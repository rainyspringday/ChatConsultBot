import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
BACKEND_DIR = BASE_DIR
NGROK_TUNNELS_CONFIG_PATH = os.path.join(BASE_DIR, ".ngrok-run.yml")
NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173


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
    workers = max(1, int(os.getenv("UVICORN_WORKERS", "4")))
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
    ]

    if workers > 1:
        cmd.extend(["--workers", str(workers)])
        print(
            f"[backend] Starting backend on http://127.0.0.1:{BACKEND_PORT} "
            f"({workers} workers)"
        )
    else:
        cmd.append("--reload")
        print(f"[backend] Starting backend on http://127.0.0.1:{BACKEND_PORT} (reload enabled)")

    return subprocess.Popen(cmd, cwd=BACKEND_DIR)


def run_frontend(api_base_url=None, ngrok_mode=False):
    print("[frontend] Starting frontend (Vite)...")

    env = os.environ.copy()
    if ngrok_mode:
        # Same-origin requests through Vite proxy (works with one public ngrok URL).
        env["VITE_API_BASE_URL"] = ""
        print("[frontend] VITE_API_BASE_URL=(empty — API proxied through Vite)")
    elif api_base_url:
        env["VITE_API_BASE_URL"] = api_base_url
        print(f"[frontend] VITE_API_BASE_URL={api_base_url}")

    npm_executable = shutil.which("npm") or shutil.which("npm.cmd")

    if not npm_executable:
        print("[frontend] npm not found in PATH, trying NVM...")
        nvm_prefix = load_nvm_env()

        if nvm_prefix:
            command = f'{nvm_prefix} npm run dev'
            return subprocess.Popen(
                ["bash", "-c", command],
                cwd=FRONTEND_DIR,
                env=env,
            )

        raise FileNotFoundError(
            "npm was not found in PATH and NVM could not be loaded."
        )

    return subprocess.Popen(
        [npm_executable, "run", "dev"],
        cwd=FRONTEND_DIR,
        env=env,
    )


def find_ngrok_auth_configs():
    """
    Return ngrok config files that contain the authtoken (user's saved token).
    When run_dev passes only .ngrok-run.yml, ngrok ignores ~/.config/ngrok/ngrok.yml
    and authentication fails with ERR_NGROK_4018.
    """
    candidates = [
        os.getenv("NGROK_CONFIG"),
        os.path.expanduser("~/.config/ngrok/ngrok.yml"),
        os.path.expanduser("~/.ngrok2/ngrok.yml"),
    ]
    return [path for path in candidates if path and os.path.isfile(path)]


def write_ngrok_tunnels_config(authtoken=None, dual=False):
    """Tunnel definitions only; auth comes from merged user config or authtoken arg."""
    lines = ['version: "2"', "tunnels:"]
    if authtoken:
        lines = [f'authtoken: {authtoken.strip()}', *lines]

    if dual:
        lines.extend(
            [
                "  backend:",
                f"    addr: {BACKEND_PORT}",
                "    proto: http",
                "  frontend:",
                f"    addr: {FRONTEND_PORT}",
                "    proto: http",
            ]
        )
    else:
        lines.extend(
            [
                "  frontend:",
                f"    addr: {FRONTEND_PORT}",
                "    proto: http",
            ]
        )

    with open(NGROK_TUNNELS_CONFIG_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def wait_for_ngrok_tunnels(timeout=30, dual=False):
    deadline = time.time() + timeout
    expected = {"backend", "frontend"} if dual else {"frontend"}
    found = {}

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(NGROK_API_URL, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.5)
            continue

        for tunnel in payload.get("tunnels", []):
            name = tunnel.get("name")
            public_url = tunnel.get("public_url", "")
            if name in expected and public_url.startswith("https://"):
                found[name] = public_url

        if expected.issubset(found.keys()):
            if dual:
                return found["backend"], found["frontend"]
            return None, found["frontend"]

        time.sleep(0.5)

    raise TimeoutError(
        "Timed out waiting for ngrok tunnels. "
        "Ensure ngrok is installed and authenticated (`ngrok config add-authtoken <token>`)."
    )


def run_ngrok(dual=False):
    ngrok_executable = shutil.which("ngrok")
    if not ngrok_executable:
        raise FileNotFoundError(
            "ngrok was not found in PATH. Install it from https://ngrok.com/download "
            "or set USE_NGROK=0 to run locally only."
        )

    auth_configs = find_ngrok_auth_configs()
    env_token = os.getenv("NGROK_AUTHTOKEN", "").strip()

    if auth_configs:
        write_ngrok_tunnels_config(dual=dual)
        ngrok_cmd = [ngrok_executable, "start", "--all"]
        for config_path in auth_configs:
            ngrok_cmd.extend(["--config", config_path])
        ngrok_cmd.extend(["--config", NGROK_TUNNELS_CONFIG_PATH])
        print("[ngrok] Using authtoken from:", ", ".join(auth_configs))
    elif env_token:
        write_ngrok_tunnels_config(authtoken=env_token, dual=dual)
        ngrok_cmd = [
            ngrok_executable,
            "start",
            "--all",
            "--config",
            NGROK_TUNNELS_CONFIG_PATH,
        ]
        print("[ngrok] Using authtoken from NGROK_AUTHTOKEN environment variable")
    else:
        raise FileNotFoundError(
            "No ngrok authtoken found. Run:\n"
            "  ngrok config add-authtoken <your-token>\n"
            "or set NGROK_AUTHTOKEN in your .env file."
        )

    mode_label = "backend + frontend" if dual else "frontend only (API proxied via Vite)"
    print(f"[ngrok] Starting tunnel ({mode_label})...")
    process = subprocess.Popen(ngrok_cmd, cwd=BASE_DIR)

    time.sleep(1.5)
    backend_url, frontend_url = wait_for_ngrok_tunnels(dual=dual)

    if dual:
        print(f"[ngrok] Backend public URL:  {backend_url}  (API only — do not open in browser)")
        print(f"[ngrok] Frontend public URL: {frontend_url}")
    else:
        print(f"[ngrok] Public demo URL: {frontend_url}")

    print("\n" + "=" * 72)
    print("  OPEN THIS URL IN YOUR BROWSER:")
    print(f"  {frontend_url}")
    print("=" * 72 + "\n")

    return process, backend_url, frontend_url


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


def parse_args():
    parser = argparse.ArgumentParser(description="Run backend, frontend, and optional ngrok tunnels.")
    parser.add_argument(
        "--ngrok",
        action="store_true",
        help="Expose app via ngrok (one public frontend URL; API proxied locally).",
    )
    parser.add_argument(
        "--ngrok-dual",
        action="store_true",
        help="Expose backend and frontend as separate ngrok URLs (advanced).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    use_ngrok = args.ngrok or args.ngrok_dual or os.getenv("USE_NGROK", "0") == "1"
    ngrok_dual = args.ngrok_dual or os.getenv("NGROK_DUAL", "0") == "1"

    print("Starting backend + frontend...")
    if use_ngrok:
        print("ngrok tunneling enabled.\n")
    else:
        print("Local only (pass --ngrok or set USE_NGROK=1 to tunnel).\n")

    backend = None
    frontend = None
    ngrok = None
    backend_public_url = None

    try:
        backend = run_backend()
        time.sleep(1)

        if use_ngrok:
            ngrok, backend_public_url, frontend_public_url = run_ngrok(dual=ngrok_dual)
            if ngrok_dual:
                frontend = run_frontend(api_base_url=backend_public_url)
            else:
                frontend = run_frontend(ngrok_mode=True)
            print(f"\n[ready] Open locally:  http://127.0.0.1:{FRONTEND_PORT}")
            print(f"[ready] Open publicly: {frontend_public_url}\n")
        else:
            frontend = run_frontend()
            print(f"\n[ready] Open locally: http://127.0.0.1:{FRONTEND_PORT}\n")

        while True:
            if backend.poll() is not None:
                print(f"[backend] Exited with code {backend.returncode}")
                break

            if frontend.poll() is not None:
                print(f"[frontend] Exited with code {frontend.returncode}")
                break

            if ngrok is not None and ngrok.poll() is not None:
                print(f"[ngrok] Exited with code {ngrok.returncode}")
                break

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, stopping services...")

    except FileNotFoundError as error:
        print(f"\nStartup failed: {error}")
        print("Services will be stopped.")

    finally:
        stop_process(frontend, "frontend")
        stop_process(backend, "backend")
        stop_process(ngrok, "ngrok")
        print("All services stopped.")
