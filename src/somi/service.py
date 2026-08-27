"""Service lifecycle manager - start/stop a local llama-server for the
desktop LLM backend.

This is the muscle behind the future GUI's on/off switch and model manager.
It manages one local llama-server subprocess. Renite services (the Titan's
llama-server and somi-tts) are systemd units on another machine and are out of scope here.

Usage:
    from somi import service
    service.start()         # launch llama-server (no-op if already up)
    service.stop()          # terminate the managed process
    service.is_running()    # -> bool

CLI: python -m somi.service [start|stop|restart|status]
"""

import os
import signal
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from somi import settings

PIDFILE = Path.home() / ".config" / "somi" / "llama-server.pid"


def _host_port() -> tuple[str, int]:
    url = urlparse(settings.get("llm", "base_url"))
    return url.hostname or "127.0.0..1", url.port or 8080


def is_running() -> bool:
    """True if the local LLM endpoint responds."""
    host, port = _host_port()
    try:
        httpx.get(f"http://{host}:{port}/v1/models", timeout=1.0)
        return True
    except Exception:
        return False


def start() -> None:
    """Launch llama-server in the background, unless already up."""
    if is_running():
        return

    model_path = settings.get("service", "model_path")
    if not model_path:
            raise RuntimeError(
                 "service.model_path is empty. Set it to the GGUF to run, or "
                 "use LM Studio / a manually-started server instead."
            )

    host, port = _host_port()
    cmd = [
         settings.get("service", "llama-server_bin"),
         "-m", model_path,
         "--host", host,
         "--port", str(port),
         "-c", settings.get("service", "context"),
    ]

    proc = subprocess.Popen(
         cmd,
         stdout=subprocess.DEVNULL,
         stderr=subprocess.DEVNULL,
         start_new_session=True,        # detach so it survives this process
    )
    PIDFILE.write_text(str(proc.pid))

    deadline = time.time() + 60
    while time.time() < deadline:
         if is_running():
              return
         time.sleep(1)
    raise RuntimeError("llama-server did not become ready within 60s")

def stop() -> None:
     """Terminate the managed llama-server, if any."""
     if PIDFILE.exists():
          try:
               pid = int(PIDFILE.read_text().strip())
               os.kill(pid, signal.SIGTERM)
          except (ProcessLookupError, ValueError):
               pass
          PIDFILE.unlink(missing_ok=True)


def restart() -> None:
     stop()
     start()


if __name__ == "__main__":
     import sys
     action = sys.argv[1] if len(sys.argv) > 1 else "status"
     if action == "start":
          start(); print("started")
     elif action == "stop":
          stop(); print("stopped")
     elif action == "restart":
          restart(); print("restarted")
     else:
         print("running" if is_running() else "not running")