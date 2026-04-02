#!/usr/bin/env python3
"""OAuth2 client-credentials style token endpoint + stats for stack tests."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

# Seconds (RFC 6749 expires_in). Short values help demo refresh without waiting an hour.
_EXPIRES_IN = int(os.environ.get("OAUTH_EXPIRES_IN_SECONDS", "3600"))

POSTS = 0


class H(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        global POSTS
        if self.path == "/stats":
            body = json.dumps({"oauth_token_posts": POSTS}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        global POSTS
        if self.path != "/token":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        POSTS += 1
        body = json.dumps(
            {
                "access_token": "mock-access-token",
                "expires_in": _EXPIRES_IN,
                "token_type": "Bearer",
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", "8080"))
    print(f"oauth mock on :{port} (POST /token, GET /stats)", flush=True)
    HTTPServer(("0.0.0.0", port), H).serve_forever()
