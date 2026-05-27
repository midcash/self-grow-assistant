"""Self-Grow launcher — starts the server and opens a native window."""
import os
import sys
import threading
import time
import urllib.request

# Must be set before importing app, because main.py checks it at module level
os.environ["SELFGROW_ENV"] = "prod"

import uvicorn
import webview

from backend.main import app

HOST = "127.0.0.1"
PORT = 8000


def start_server():
    """Start FastAPI server in background thread."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


def wait_for_server(timeout=15):
    """Poll until the server is ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}/api/health")
            return True
        except Exception:
            time.sleep(0.3)
    return False


if __name__ == "__main__":
    # Start the server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Wait for the server to be ready
    if not wait_for_server():
        print("Server failed to start.", file=sys.stderr)
        sys.exit(1)

    # Open native window (blocks until window is closed)
    webview.create_window(
        title="Self-Grow — 自我成长",
        url=f"http://{HOST}:{PORT}",
        width=500,
        height=800,
        min_size=(400, 500),
    )
    webview.start()
