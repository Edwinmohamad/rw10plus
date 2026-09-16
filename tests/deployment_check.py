#!/usr/bin/env python3
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8188"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as response:
        return response.status, response.headers.get_content_type(), response.read()


status, kind, body = get("/api/health")
health = json.loads(body)
assert status == 200 and kind == "application/json" and health["version"] == "0.3.0"
for path, marker in (("/styles.css?v=0.3.0", b"html.elderly"), ("/app.js?v=0.3.0", b"cancel_deadline"), ("/", b'id="view-operations"')):
    status, _, body = get(path)
    assert status == 200 and marker in body
try:
    get("/aset-yang-tidak-ada.css")
    raise AssertionError("Aset hilang seharusnya 404")
except urllib.error.HTTPError as exc:
    assert exc.code == 404
print("DEPLOYMENT CHECK OK: v0.3.0, UI, alur SOS, dan 404 aset")
