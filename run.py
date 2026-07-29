"""
Single entry point: starts the server and opens your default browser to it
automatically. This is what start.bat runs.
"""
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _open_browser_when_ready():
    # Small delay so the server has bound to the port before the browser
    # tries to connect — avoids a "connection refused" flash on first load.
    time.sleep(1.2)
    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    print(f"\nStarting Sales Insights — opening {URL} in your browser...\n")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
