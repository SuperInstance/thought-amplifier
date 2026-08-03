#!/usr/bin/env python3
"""
viewer/server.py — WebSocket Viewer for Thought Stream

Pure Python stdlib HTTP + WebSocket server that serves the thought
stream UI and streams journal data in real-time via WebSocket.

Adapted from slackwater-cognition/viewer/server.py — simplified and
generalized for the thought amplifier.

Run standalone:
    python viewer/server.py

Or via amplifier.py:
    python amplifier.py --viewer
"""

from __future__ import annotations

import base64
import glob
import hashlib
import json
import os
import select
import socket
import struct
import threading
import time
import re
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# ─── Paths ──────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
VIEWER_DIR = Path(__file__).resolve().parent
JOURNAL_DIR = REPO_ROOT / "journals"

PORT = int(os.environ.get("VIEWER_PORT", "8770"))


# ─── Journal Reading ────────────────────────────────────────────

def _session_files() -> list[Path]:
    """Return sorted list of session JSONL files."""
    if not JOURNAL_DIR.exists():
        return []
    return sorted(JOURNAL_DIR.glob("session_*.jsonl"))


def read_entries(limit: int = 200, entry_type: str | None = None) -> list[dict[str, Any]]:
    """Read entries from all session files, most recent first."""
    files = _session_files()
    if not files:
        return []
    entries: list[dict[str, Any]] = []
    for f in reversed(files):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            if entry_type is None or entry.get("type") == entry_type:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except OSError:
            continue
        if len(entries) >= limit:
            break
    return entries[:limit]


def read_thoughts(limit: int = 100) -> list[dict[str, Any]]:
    return read_entries(limit=limit, entry_type="thought")


def read_directives(limit: int = 50) -> list[dict[str, Any]]:
    return read_entries(limit=limit, entry_type="directive")


def read_system_events(limit: int = 20) -> list[dict[str, Any]]:
    return read_entries(limit=limit, entry_type="system")


# ─── File Watcher ───────────────────────────────────────────────

class FileWatcher:
    """Watches journal files for changes and notifies WebSocket clients."""

    def __init__(self) -> None:
        self.clients: list[WebSocketClient] = []
        self._lock = threading.Lock()
        self._known_sizes: dict[str, int] = {}
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def add_client(self, client: "WebSocketClient") -> None:
        with self._lock:
            self.clients.append(client)

    def remove_client(self, client: "WebSocketClient") -> None:
        with self._lock:
            if client in self.clients:
                self.clients.remove(client)

    def _watch_loop(self) -> None:
        """Poll files for changes every 0.5s."""
        while self._running:
            try:
                self._check_files()
            except Exception:
                pass
            time.sleep(0.5)

    def _check_files(self) -> None:
        files = _session_files()
        for f in files:
            key = str(f)
            try:
                size = f.stat().st_size
            except OSError:
                continue
            prev = self._known_sizes.get(key)
            if prev is None:
                self._known_sizes[key] = size
                # Send last few entries on first discovery
                self._send_recent_from_file(f, count=5)
            elif size > prev:
                self._known_sizes[key] = size
                self._send_new_lines(f, prev)

    def _send_recent_from_file(self, path: Path, count: int = 5) -> None:
        try:
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-count:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_type = data.get("type", "thought")
                    self._broadcast({"type": msg_type, "data": data})
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass

    def _send_new_lines(self, path: Path, prev_size: int) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.seek(prev_size)
                new_content = f.read()
            for line in new_content.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_type = data.get("type", "thought")
                    self._broadcast({"type": msg_type, "data": data})
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass

    def _broadcast(self, message: dict[str, Any]) -> None:
        text = json.dumps(message, ensure_ascii=False)
        with self._lock:
            dead: list[WebSocketClient] = []
            for client in self.clients:
                try:
                    client.send_text(text)
                except Exception:
                    dead.append(client)
            for d in dead:
                self.clients.remove(d)


# ─── WebSocket Implementation ───────────────────────────────────

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketClient:
    """A connected WebSocket client."""

    def __init__(self, sock: socket.socket, watcher: FileWatcher) -> None:
        self.sock = sock
        self.watcher = watcher
        self.alive = True

    def send_text(self, message: str) -> None:
        if not self.alive:
            return
        data = message.encode("utf-8")
        header = bytearray()
        header.append(0x81)  # FIN + text frame
        length = len(data)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(127)
            header.extend(struct.pack(">Q", length))
        self.sock.sendall(bytes(header) + data)

    def recv_text(self) -> str | None:
        try:
            header = self._recv_exact(2)
            if not header:
                return None
            opcode = header[0] & 0x0F
            masked = (header[1] & 0x80) != 0
            length = header[1] & 0x7F
            if length == 126:
                ext = self._recv_exact(2)
                if not ext:
                    return None
                length = struct.unpack(">H", ext)[0]
            elif length == 127:
                ext = self._recv_exact(8)
                if not ext:
                    return None
                length = struct.unpack(">Q", ext)[0]
            if masked:
                mask = self._recv_exact(4)
                if not mask:
                    return None
            payload = self._recv_exact(length) if length > 0 else b""
            if masked and payload:
                payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))

            if opcode == 0x8:  # Close
                self.alive = False
                return None
            elif opcode == 0x9:  # Ping
                self._send_pong(payload)
                return self.recv_text()
            return payload.decode("utf-8", errors="replace")
        except (ConnectionError, OSError):
            self.alive = False
            return None

    def _recv_exact(self, n: int) -> bytes | None:
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = self.sock.recv(n - len(buf))
                if not chunk:
                    return None
                buf.extend(chunk)
            except (ConnectionError, OSError):
                return None
        return bytes(buf)

    def _send_pong(self, payload: bytes) -> None:
        header = bytearray()
        header.append(0x8A)
        header.append(len(payload))
        try:
            self.sock.sendall(bytes(header) + payload)
        except (ConnectionError, OSError):
            self.alive = False

    def close(self) -> None:
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass


def handle_websocket(sock: socket.socket, watcher: FileWatcher) -> None:
    """Handle a WebSocket connection after upgrade."""
    client = WebSocketClient(sock, watcher)
    watcher.add_client(client)

    # Send initial data
    try:
        recent = read_thoughts(20)
        for t in reversed(recent):
            client.send_text(json.dumps({"type": "thought", "data": t}, ensure_ascii=False))

        directives = read_directives(10)
        for d in directives:
            client.send_text(json.dumps({"type": "directive", "data": d}, ensure_ascii=False))

        events = read_system_events(5)
        for e in events:
            client.send_text(json.dumps({"type": "system", "data": e}, ensure_ascii=False))
    except Exception:
        pass

    try:
        while client.alive:
            msg = client.recv_text()
            if msg is None:
                break
            try:
                data = json.loads(msg)
                if data.get("type") == "ping":
                    client.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, KeyError):
                pass
    finally:
        watcher.remove_client(client)
        client.close()


# ─── HTTP Handler ───────────────────────────────────────────────

watcher: FileWatcher  # set in main


class ViewerHandler(BaseHTTPRequestHandler):
    """Serves the web UI and REST API."""

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress default logging

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/stream":
            self._handle_ws_upgrade()
            return

        if path == "/" or path == "/index.html":
            self._serve_file(VIEWER_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/api/thoughts":
            self._serve_json(read_thoughts(200))
        elif path == "/api/directives":
            self._serve_json(read_directives(50))
        elif path == "/api/system":
            self._serve_json(read_system_events(20))
        elif path == "/api/state":
            thoughts = read_thoughts(1)
            state = {
                "latest_thought": thoughts[0] if thoughts else None,
                "thought_count": len(read_thoughts(1000)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._serve_json(state)
        else:
            self.send_error(404, f"Not found: {path}")

    def _handle_ws_upgrade(self) -> None:
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_error(400, "Missing WebSocket key")
            return

        accept = base64.b64encode(
            hashlib.sha1((key + WS_MAGIC).encode()).digest()
        ).decode()

        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()

        handle_websocket(self.connection, watcher)

    def _serve_file(self, path: Path, content_type: str) -> None:
        try:
            content = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f"File not found: {path.name}")

    def _serve_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


# ─── Main ───────────────────────────────────────────────────────

class DualServer(HTTPServer):
    """HTTP server with socket reuse."""
    def __init__(self, addr: tuple[str, int], handler: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(addr, handler)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


def main() -> None:
    global watcher
    watcher = FileWatcher()
    watcher.start()

    server = DualServer(("0.0.0.0", PORT), ViewerHandler)

    print("╔══════════════════════════════════════════════╗")
    print("║   Thought Amplifier — Stream Viewer           ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  URL:   http://localhost:{PORT}")
    print(f"  WS:    ws://localhost:{PORT}/stream")
    print(f"  API:   http://localhost:{PORT}/api/thoughts")
    print(f"  Logs:  {JOURNAL_DIR}")
    print()
    print("  Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        watcher.stop()
        server.shutdown()
        print("Stopped.")


if __name__ == "__main__":
    main()
