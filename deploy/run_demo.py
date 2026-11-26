"""Run the hosted demo with a dedicated database and mock providers."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def configure_demo() -> None:
    database = (Path(tempfile.gettempdir()) / "rai-demo.sqlite3").as_posix()
    os.environ.update(
        DATABASE_URL=f"sqlite+pysqlite:///{database}",
        APP_ENV="public_demo",
        AI_MODE="mock",
        PAYMENT_PROVIDER="mock",
        MOCK_PROVIDER_FORCE_ERROR="false",
        LLM_API_KEY="",
        RAZORPAY_KEY_ID="",
        RAZORPAY_KEY_SECRET="",
    )


def main() -> int:
    configure_demo()
    from app.db.base import Base
    from app.db.session import engine
    from app.demo.bootstrap import seed_if_empty

    Base.metadata.create_all(engine)
    seed_if_empty()

    processes: list[subprocess.Popen] = []
    stopping = False

    def request_stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        processes.append(subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"
        ]))
        processes.append(subprocess.Popen(
            ["node", "/app/web/server.js"],
            env={**os.environ, "HOSTNAME": "0.0.0.0", "PORT": os.getenv("PORT", "10000")},
            cwd="/app/web",
        ))
        while not stopping:
            if any(process.poll() is not None for process in processes):
                return 1
            time.sleep(0.5)
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    sys.exit(main())
