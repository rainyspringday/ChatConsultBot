import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")  # adjust if needed
BACKEND_DIR = BASE_DIR


def run_backend():
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=BACKEND_DIR,
    )


def run_frontend():
    return subprocess.Popen(
        "npm run dev",
        cwd=FRONTEND_DIR,
        shell=True,
        executable="/bin/bash"
    )


if __name__ == "__main__":
    print("Starting backend + frontend...")

    backend = run_backend()
    frontend = run_frontend()

    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend.terminate()
        frontend.terminate()