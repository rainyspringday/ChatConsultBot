import subprocess
import sys
import os
import time
import shutil

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
    npm_executable = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_executable:
        raise FileNotFoundError(
            "npm was not found in PATH. Install Node.js and restart your terminal."
        )

    return subprocess.Popen(
        [npm_executable, "run", "dev"],
        cwd=FRONTEND_DIR,
    )


def stop_process(process: subprocess.Popen, name: str):
    if process.poll() is not None:
        return
    print(f"Stopping {name}...")
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print(f"{name} did not stop in time, killing it.")
        process.kill()


if __name__ == "__main__":
    print("Starting backend + frontend...")

    backend = None
    frontend = None

    try:
        backend = run_backend()
        frontend = run_frontend()

        while True:
            backend_exit = backend.poll()
            frontend_exit = frontend.poll()

            if backend_exit is not None:
                print(f"Backend exited with code {backend_exit}.")
                break
            if frontend_exit is not None:
                print(f"Frontend exited with code {frontend_exit}.")
                break

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, stopping services...")
    except FileNotFoundError as error:
        print(f"\nStartup failed: {error}")
        print("Backend will be stopped.")
    finally:
        if backend is not None:
            stop_process(backend, "backend")
        if frontend is not None:
            stop_process(frontend, "frontend")