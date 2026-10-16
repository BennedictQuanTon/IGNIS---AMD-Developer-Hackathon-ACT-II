"""A loopback stand-in for the AMD chat API that plays back scripted replies in order."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def chat_reply(content, finish_reason="stop", reasoning=None, usage=None) -> dict:
    message = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning"] = reasoning
    choice = {"index": 0, "message": message, "finish_reason": finish_reason}
    return {"choices": [choice], "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5}}


def reply(body, status=200, headers=None, delay=0.0, drop=False) -> dict:
    """`drop` closes the connection without answering, like a gateway reset."""
    return {"body": body, "status": status, "headers": headers or {}, "delay": delay, "drop": drop}


class ScriptedServer:
    """Serves `replies` in order and repeats the last one; records every request it receives."""

    def __init__(self, replies: list[dict]):
        self.replies = list(replies)
        self.requests = []
        scripted = self

        class Handler(BaseHTTPRequestHandler):
            def handle_any(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                scripted.requests.append({"method": self.command, "path": self.path, "headers": dict(self.headers),
                                          "body": body})
                planned = scripted.replies.pop(0) if len(scripted.replies) > 1 else scripted.replies[0]
                if planned["delay"]:
                    time.sleep(planned["delay"])
                if planned["drop"]:
                    self.close_connection = True
                    return
                payload = planned["body"]
                data = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload).encode("utf-8")
                self.send_response(planned["status"])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in planned["headers"].items():
                    self.send_header(name, value)
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            do_GET = handle_any
            do_POST = handle_any

            def log_message(self, *arguments):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exception):
        self.server.shutdown()
        self.server.server_close()
