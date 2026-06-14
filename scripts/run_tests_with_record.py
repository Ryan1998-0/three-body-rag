from datetime import datetime
from pathlib import Path
import os
import subprocess
import sys


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    record_dir = repo_root / "test-records"
    record_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record_path = record_dir / f"test-record-{timestamp}.md"
    command = [sys.executable, "-m", "unittest", "tests.test_rag_pipeline"]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
    )

    record = [
        f"# Test Record {timestamp}",
        "",
        f"- Command: `{' '.join(command)}`",
        f"- Exit code: `{completed.returncode}`",
        "",
        "## stdout",
        "",
        "```text",
        completed.stdout.rstrip(),
        "```",
        "",
        "## stderr",
        "",
        "```text",
        completed.stderr.rstrip(),
        "```",
        "",
    ]
    record_path.write_text("\n".join(record), encoding="utf-8")
    print(f"Saved test record: {record_path}")
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
