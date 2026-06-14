from __future__ import annotations
import asyncio, json, logging, uuid
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.api.schemas import HealthResponse
from app.core.logging_config import configure_logging, request_id_var

logger = logging.getLogger(__name__)
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.core.repository import Repository
from app.llm.mock_client import MockClient
from app.models.domain import ClaimOutcome, ClaimSubmission


def make_llm():
    # Live providers reach over the network, so they sit behind a circuit breaker
    # that fails fast when the provider is down (see CircuitBreakerLLM). The mock
    # provider is in-process and deterministic — wrapping it would add nothing, so
    # it's returned bare and the breaker stays entirely off the test/eval path.
    if settings.llm_provider == "gemini":
        from app.llm.gemini_client import GeminiClient
        return _with_breaker(GeminiClient(api_key=settings.gemini_api_key), "gemini")
    if settings.llm_provider == "groq":
        from app.llm.groq_client import GroqClient
        return _with_breaker(
            GroqClient(api_key=settings.groq_api_key, model=settings.groq_model), "groq")
    return MockClient()


def _with_breaker(client, name: str):
    from app.llm.circuit_breaker import CircuitBreakerLLM
    return CircuitBreakerLLM(
        client,
        fail_max=settings.llm_circuit_fail_max,
        cooldown_s=settings.llm_circuit_cooldown_s,
        name=name,
    )


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

    @app.middleware("http")
    async def correlation_id(request, call_next):
        # Honor a caller-supplied X-Request-ID (lets a gateway/SPA thread one id
        # through), else mint one. Bind it to the contextvar so every log line
        # this request emits is stamped with it, and stash it on request.state
        # so the error handler can still read it after the contextvar is reset.
        rid = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
        request.state.request_id = rid
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

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

    @app.get("/eval/cases")
    async def eval_cases():
        from app.eval.runner import case_summaries
        return case_summaries(settings.test_cases_path)

    @app.post("/eval/run/{case_id}")
    async def run_eval_case(case_id: str):
        """Run a single case through the real vision pipeline: the generated
        document images are read by Groq's multimodal model (classification,
        extraction, name-matching) instead of injecting structured content."""
        from app.eval.runner import EVAL_DOCS_DIR, EvalRunner, find_case
        case = find_case(case_id, settings.test_cases_path)
        if case is None:
            raise HTTPException(404, f"unknown test case {case_id!r}")
        if not settings.groq_api_key:
            raise HTTPException(
                503, "live eval needs a vision LLM: set GROQ_API_KEY (provider=groq).")
        # Fail loudly if the document images are missing — otherwise the live
        # path silently falls back to injected content and looks like vision but
        # isn't (the classic "0ms extraction" symptom in a stale container).
        if case["input"].get("documents") and not EvalRunner.live_images_for(case):
            raise HTTPException(
                503, f"No eval document images for {case_id} in {EVAL_DOCS_DIR}. "
                "Run `python scripts/generate_eval_docs.py`, then rebuild the API "
                "image (app/Dockerfile copies eval_docs/).")
        from app.llm.groq_client import GroqClient
        live_llm = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
        live_orch = Orchestrator(loader=loader, llm=live_llm)  # no repo: eval is not a real claim
        runner = EvalRunner(orchestrator=orch)
        result = await runner.run_case_live(case, live_orch)
        return result.model_dump()

    @app.exception_handler(Exception)
    async def on_unexpected_error(request, exc):
        # Last-resort safety net: an unexpected error becomes a structured JSON
        # 500 rather than a bare crash, so the API stays predictable. Full detail
        # is logged for ops; the member-facing body never leaks internals. The
        # request id is echoed in both the log and the body so a user-reported
        # failure can be traced to its exact log line. (Read from request.state,
        # not the contextvar, which the middleware has already reset by now.)
        rid = getattr(request.state, "request_id", "-")
        logger.exception("unhandled error on %s %s [%s]",
                         request.method, request.url.path, rid)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error",
                     "request_id": rid,
                     "detail": "An unexpected error occurred while processing the request."})

    return app


app = create_app()
