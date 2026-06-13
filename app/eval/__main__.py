import asyncio, pathlib
from app.config import settings
from app.eval.runner import EvalRunner

async def main():
    runner = EvalRunner.default()
    report = await runner.run_all(settings.test_cases_path)
    out = pathlib.Path("docs/eval_report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(EvalRunner.render_markdown(report))
    print(f"{report.passed}/12 passed → {out}")

asyncio.run(main())
