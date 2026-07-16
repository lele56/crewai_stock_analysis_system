# run_tests.py
"""快速运行项目测试套件"""

from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).parent


def run_tests(args=None):
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(PROJECT_ROOT / "tests"),
        "-v",
        "--tb=short",
    ]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def run_fast():
    return run_tests(["-x", "--durations=10"])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fast":
        sys.exit(run_fast())
    else:
        sys.exit(run_tests(sys.argv[1:]))
