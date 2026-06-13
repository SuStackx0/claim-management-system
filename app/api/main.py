from __future__ import annotations
import asyncio, json, logging
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.api.schemas import HealthResponse

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
    return MockClient()


def create_app(db_path: str | None = None) -> FastAPI:
    app = FastAPI(title="Plum Claims Processing", version=settings.pipeline_version)
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
