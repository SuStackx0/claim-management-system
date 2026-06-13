from __future__ import annotations
import asyncio, json, logging
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.api.schemas import HealthResponse
from app.core.logging_config import configure_logging

logger = logging.getLogger(__name__)
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.core.repository import Repository
from app.llm.mock_client import MockClient
from app.models.domain import ClaimOutcome, ClaimSubmission


def make_llm():
    if settings.llm_provider == "gemini":
        from app.llm.gemini_client import GeminiClient
        return GeminiClient(api_key=settings.gemini_api_key)
    if settings.llm_provider == "groq":
        from app.llm.groq_client import GroqClient
        return GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    return MockClient()


def create_app(db_path: str | None = None) -> FastAPI:
    configure_logging()
    app = FastAPI(title="Plum Claims Processing", version=settings.pipeline_version)

    # Allow the browser SPA to call the API when it's served from another origin
    # (e.g. the Render static site). The docker image proxies same-origin, so
    # this is a no-op there.
    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    loader = PolicyLoader.load(settings.policy_path)
    repo = Repository(db_path or settings.db_path)
    orch = Orchestrator(loader=loader, llm=make_llm(), repository=repo)

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(llm_provider=settings.llm_provider,
                              pipeline_version=settings.pipeline_version)

    @app.get("/members")
    async def members():
        return [{"member_id": m.member_id, "name": m.name, "relationship": m.relationship}
                for m in loader.policy.members]

    @app.post("/claims", response_model=ClaimOutcome)
    async def submit_claim(submission: ClaimSubmission) -> ClaimOutcome:
        return await orch.process(submission)

    @app.post("/claims/upload", response_model=ClaimOutcome)
    async def submit_claim_with_files(
        payload: str = Form(...),
        files: list[UploadFile] = File(...),
    ) -> ClaimOutcome:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise HTTPException(422, f"payload is not valid JSON: {e}")
        if not isinstance(data, dict):
            raise HTTPException(422, "payload must be a JSON object")
        data["documents"] = [
            {
                "file_id": f"UP{i + 1}",
                "file_name": f.filename,
                "file_bytes": await f.read(),
                "mime_type": f.content_type,
            }
            for i, f in enumerate(files)
        ]
        try:
            sub = ClaimSubmission.model_validate(data)
        except ValidationError as e:
            raise HTTPException(422, json.loads(e.json()))
        return await orch.process(sub)

    @app.get("/claims")
    async def list_claims():
        return await asyncio.to_thread(repo.list_claims)

    @app.get("/claims/{claim_id}")
    async def get_claim(claim_id: str):
        row = await asyncio.to_thread(repo.get, claim_id)
        if row is None:
            raise HTTPException(404, f"claim {claim_id} not found")
        return row

    @app.post("/eval/run")
    async def run_eval():
        from app.eval.runner import EvalRunner
        runner = EvalRunner(orchestrator=orch)
        report = await runner.run_all(settings.test_cases_path)
        return report.model_dump()

    @app.exception_handler(Exception)
    async def on_unexpected_error(request, exc):
        # Last-resort safety net: an unexpected error becomes a structured JSON
        # 500 rather than a bare crash, so the API stays predictable. Full detail
        # is logged for ops; the member-facing body never leaks internals.
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error",
                     "detail": "An unexpected error occurred while processing the request."})

    return app


app = create_app()
