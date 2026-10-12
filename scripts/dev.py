"""Run both development servers and stop them together on exit."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    processes: list[subprocess.Popen] = []

    def stop(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        for command, directory in [
            (
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "hippobox.server:app",
                    "--reload",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    os.getenv("BACKEND_PORT", "8000"),
                ],
                "src/backend",
            ),
            (
                [
                    "npm",
                    "run",
                    "dev:vite",
                    "--",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    os.getenv("FRONTEND_PORT", "5173"),
                    "--strictPort",
                ],
                "src/frontend",
            ),
        ]:
            processes.append(subprocess.Popen(command, cwd=ROOT / directory, start_new_session=True))
        while all(process.poll() is None for process in processes):
            time.sleep(0.2)
        return next(process.returncode for process in processes if process.returncode is not None)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
