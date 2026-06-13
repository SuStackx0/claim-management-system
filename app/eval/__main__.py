import argparse, asyncio, pathlib
from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.eval.runner import EvalRunner


async def main(live: bool, sleep_s: float, out_path: str,
               attempts: int, retry_cooldown_s: float):
    runner = EvalRunner.default()
    if live:
        if not settings.groq_api_key:
            raise SystemExit("live eval needs GROQ_API_KEY (provider=groq).")
        from app.llm.groq_client import GroqClient
        loader = PolicyLoader.load(settings.policy_path)
        live_orch = Orchestrator(loader=loader,
                                 llm=GroqClient(api_key=settings.groq_api_key,
                                                model=settings.groq_model))
        report = await runner.run_all_live(settings.test_cases_path, live_orch,
                                           sleep_s=sleep_s, max_attempts=attempts,
                                           retry_cooldown_s=retry_cooldown_s)
    else:
        report = await runner.run_all(settings.test_cases_path)

    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(EvalRunner.render_markdown(report, live=live))
    print(f"{report.passed}/{report.passed + report.failed} passed → {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Run the 12 assignment test cases.")
    p.add_argument("--live", action="store_true",
                   help="run through the real Groq vision pipeline using eval_docs images")
    p.add_argument("--sleep", type=float, default=15.0,
                   help="seconds between cases in live mode (rate limit)")
    p.add_argument("--out", default="docs/eval_report.md", help="output report path")
    p.add_argument("--attempts", type=int, default=3,
                   help="max attempts per case in live mode (retries transient throttling)")
    p.add_argument("--retry-cooldown", type=float, default=40.0,
                   help="seconds to wait before retrying a failed case in live mode")
    a = p.parse_args()
    asyncio.run(main(a.live, a.sleep, a.out, a.attempts, a.retry_cooldown))
