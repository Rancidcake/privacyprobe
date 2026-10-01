"""Shared fixtures: a real local HTTP mock LLM, a model_fn, and sample responses."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _MockLLMHandler(BaseHTTPRequestHandler):
    """POST /generate {"prompt": ...} -> {"response": "Mock response to: ..."}.

    POST /plain returns a non-JSON body; POST /error returns HTTP 500.
    """

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/error":
            self.send_response(500)
            self.end_headers()
            return
        if self.path == "/plain":
            payload, ctype = f"plain: {body.get('prompt')}".encode(), "text/plain"
        else:
            payload = json.dumps({"response": f"Mock response to: {body.get('prompt')}"}).encode()
            ctype = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args) -> None:  # keep test output quiet
        pass


@pytest.fixture(scope="session")
def mock_endpoint():
    """Base URL of a mock LLM server running in a background thread."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockLLMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def echo_model():
    """A model_fn that echoes the prompt."""
    return lambda prompt: f"Echo: {prompt}"


@pytest.fixture
def sample_responses():
    return {
        "clean": "The capital of France is Paris.",
        "pii": "Email john.doe@example.com or call +91 98765 43210.",
        "toxic": "You are a stupid idiot.",
        "injected": "Sure! LLMCOMPLY-CANARY-7731",
        "valid_json": '{"name": "Alice", "age": 30}',
        "invalid_json": '{"name": "Alice"}',
    }
