"""
Run one or more assignment test cases through the REAL Groq vision pipeline
(document images -> classify -> extract -> adjudicate) and print a detailed,
per-step log. Paces calls with a sleep between cases to stay under Groq's
free-tier rate limit.

Usage:
  python scripts/run_live_eval.py TC004                 # one case
  python scripts/run_live_eval.py TC004 TC009 TC010     # several
  python scripts/run_live_eval.py ALL --sleep 10        # all 12, 10s apart
"""
from __future__ import annotations

import argparse
import asyncio

from app.config import settings
from app.core.orchestrator import Orchestrator
from app.core.policy_loader import PolicyLoader
from app.eval.runner import EvalRunner, find_case, load_cases


def _make_client(provider: str):
    if provider == "gemini":
        from app.llm.gemini_client import GeminiClient
        return GeminiClient(api_key=settings.gemini_api_key)
    from app.llm.groq_client import GroqClient
    return GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)


def _step_line(s: dict) -> str:
    bits = [f"    {s['step']:16} {s['status']:8} {s['duration_ms']:>6}ms"]
    extras = []
    for c in s.get("checks", []):
        d = c.get("detail", {}) or {}
        if d.get("source"):
            extras.append(f"{d.get('file_id')}:{d.get('doc_type')}={d['source']}")
        elif d.get("detected_type"):
            extras.append(f"{d.get('file_id')}:{d['detected_type']}@{d.get('confidence')}")
    if extras:
        bits.append("  | " + ", ".join(extras))
    if s.get("error"):
        bits.append(f"  ERROR={s['error'].get('code')}")
    return "".join(bits)


def _print_result(case: dict, result) -> None:
    for s in result.trace.get("steps", []):
        print(_step_line(s))
    verdict = "PASS ✅" if result.passed else "FAIL ❌"
    print(f"  expected={result.expected_decision} produced={result.produced_decision} "
          f"amount={result.approved_amount} conf={result.confidence}  -> {verdict}")
    if result.member_message:
        print(f"  member_message: {result.member_message[:200]}")
    if result.failures:
        for f in result.failures:
            print(f"  ✗ {f}")


async def run_one(case: dict, orch: Orchestrator, runner: EvalRunner,
                  attempts: int, cooldown: float):
    print(f"\n{'='*78}\n{case['case_id']} — {case['case_name']}")
    print(f"  images: {', '.join(EvalRunner.live_images_for(case)) or '(none)'}")
    result = await runner.run_case_live(case, orch)
    n = 1
    while not result.passed and n < attempts:
        print(f"  …attempt {n} failed, cooling down {cooldown}s then retrying…")
        await asyncio.sleep(cooldown)
        result = await runner.run_case_live(case, orch)
        n += 1
    _print_result(case, result)
    return result


async def main(case_ids: list[str], sleep_s: float, attempts: int,
               cooldown: float, out_path: str | None, provider: str) -> None:
    loader = PolicyLoader.load(settings.policy_path)
    llm = _make_client(provider)
    print(f"provider: {provider}")
    orch = Orchestrator(loader=loader, llm=llm)
    runner = EvalRunner.default()

    if case_ids == ["ALL"]:
        case_ids = [c["case_id"] for c in load_cases()]

    results = []
    for i, cid in enumerate(case_ids):
        case = find_case(cid)
        if case is None:
            print(f"unknown case {cid}")
            continue
        results.append(await run_one(case, orch, runner, attempts, cooldown))
        if i < len(case_ids) - 1 and sleep_s:
            print(f"\n  …sleeping {sleep_s}s (rate limit)…")
            await asyncio.sleep(sleep_s)

    passed = sum(r.passed for r in results)
    print(f"\n{'='*78}\nSUMMARY: {passed}/{len(results)} passed")
    for r in results:
        print(f"  {r.case_id}: {'PASS' if r.passed else 'FAIL'}")

    if out_path and len(results) == 12:
        import pathlib
        from app.eval.runner import EvalReport
        report = EvalReport(cases=results, passed=passed, failed=12 - passed)
        pathlib.Path(out_path).write_text(EvalRunner.render_markdown(report, live=True))
        print(f"\nwrote report → {out_path}")
    elif out_path:
        print(f"\n(skipped report write: need all 12 cases, ran {len(results)})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cases", nargs="+", help="case ids (e.g. TC004) or ALL")
    p.add_argument("--sleep", type=float, default=8.0, help="seconds between cases")
    p.add_argument("--attempts", type=int, default=1, help="max attempts per case")
    p.add_argument("--cooldown", type=float, default=30.0, help="seconds before a retry")
    p.add_argument("--out", default=None, help="write eval report here (requires running all 12)")
    p.add_argument("--provider", default="groq", choices=["groq", "gemini"],
                   help="which vision LLM to use")
    a = p.parse_args()
    asyncio.run(main(a.cases, a.sleep, a.attempts, a.cooldown, a.out, a.provider))
