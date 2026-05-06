import subprocess
import sys
import os
import time
import shutil
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
BACKEND_DIR = BASE_DIR


def load_nvm_env():
    """
    Ensures NVM is loaded so npm is available inside subprocesses.
    Returns a shell prefix string that loads NVM and activates Node.
    """
    nvm_dir = os.path.expanduser("~/.nvm")
    nvm_sh = os.path.join(nvm_dir, "nvm.sh")

    if os.path.exists(nvm_sh):
        return f'. "{nvm_sh}"; nvm use 20; '

    return ""


def run_backend():
    print("[backend] Starting backend on http://127.0.0.1:8000")

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
    print("[frontend] Starting frontend (Vite)...")

    # Try system npm first
    npm_executable = shutil.which("npm") or shutil.which("npm.cmd")

    # If system npm not found, try NVM
    if not npm_executable:
        print("[frontend] npm not found in PATH, trying NVM...")
        nvm_prefix = load_nvm_env()

        if nvm_prefix:
            # Run npm via bash with NVM loaded
            command = f'{nvm_prefix} npm run dev'
            return subprocess.Popen(
                ["bash", "-c", command],
                cwd=FRONTEND_DIR,
            )

        raise FileNotFoundError(
            "npm was not found in PATH and NVM could not be loaded."
        )

    # System npm works
    return subprocess.Popen(
        [npm_executable, "run", "dev"],
        cwd=FRONTEND_DIR,
    )


def stop_process(process: subprocess.Popen, name: str):
    if process is None or process.poll() is not None:
        return

    print(f"[{name}] Stopping...")

    try:
        process.terminate()
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        print(f"[{name}] Did not stop in time, killing...")
        process.kill()


if __name__ == "__main__":
    print("Starting backend + frontend...\n")

    backend = None
    frontend = None

    try:
        backend = run_backend()
        frontend = run_frontend()

        while True:
            if backend.poll() is not None:
                print(f"[backend] Exited with code {backend.returncode}")
                break

            if frontend.poll() is not None:
                print(f"[frontend] Exited with code {frontend.returncode}")
                break

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, stopping services...")

    except FileNotFoundError as error:
        print(f"\nStartup failed: {error}")
        print("Backend will be stopped.")

    finally:
        stop_process(backend, "backend")
        stop_process(frontend, "frontend")
        print("All services stopped.")
