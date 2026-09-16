#!/usr/bin/env python3
import http.cookiejar
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = "18188"
BASE = f"http://127.0.0.1:{PORT}"


def client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(opener, path, method="GET", data=None, headers=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=payload, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with opener.open(req, timeout=4) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def login(phone, pin):
    opener = client()
    status, body = request(opener, "/api/login", "POST", {"phone": phone, "pin": pin})
    assert status == 200 and body["ok"]
    return opener


with tempfile.TemporaryDirectory() as tmp:
    db_path = os.path.join(tmp, "test.db")
    env = dict(os.environ, RW10_PORT=PORT, RW10_DB_PATH=db_path)
    proc = subprocess.Popen(["python3", os.path.join(ROOT, "server.py")], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                if urllib.request.urlopen(BASE + "/api/health", timeout=.5).status == 200:
                    break
            except Exception:
                time.sleep(.1)
        else:
            raise AssertionError("Server tidak siap")

        anonymous = client()
        status, health = request(anonymous, "/api/health")
        assert status == 200 and health["version"] == "0.3.0" and health["toa_mode"] == "simulation"
        assert request(anonymous, "/api/bootstrap")[0] == 401
        for asset in ("/", "/styles.css?v=0.3.0", "/app.js?v=0.3.0", "/manifest.webmanifest"):
            with urllib.request.urlopen(BASE + asset, timeout=3) as response:
                assert response.status == 200 and response.read()
        assert request(anonymous, "/missing.css")[0] == 404

        warga = login("081200000001", "0101")
        ketua = login("081200000003", "0303")
        rw = login("081200000010", "1010")
        satpam = login("081200000002", "0202")

        _, wb = request(warga, "/api/bootstrap")
        assert wb["user"]["role"] == "warga" and not wb["capabilities"]["can_respond_sos"]
        assert wb["market"] and wb["voting"] and len(wb["cameras"]) == 4
        _, sb = request(satpam, "/api/bootstrap")
        assert sb["capabilities"]["can_patrol"] and sb["invoices"] == [] and sb["letters"] == []

        idem = "smoke-idempotency-key"
        status, sos = request(warga, "/api/sos", "POST", {"category": "medis", "scope": "rw", "mode": "silent"}, {"Idempotency-Key": idem})
        assert status == 201 and sos["status"] == "cancel_window"
        _, guard_during_cancel = request(satpam, "/api/bootstrap")
        assert all(event["id"] != sos["id"] for event in guard_during_cancel["events"]), "SOS bocor sebelum cancel window selesai"
        status, duplicate = request(warga, "/api/sos", "POST", {"category": "medis", "scope": "rw", "mode": "silent"}, {"Idempotency-Key": idem})
        assert status == 201 and duplicate["id"] == sos["id"]
        assert request(warga, f"/api/sos/{sos['id']}/respond", "POST", {"action": "menuju"})[0] == 403
        assert request(warga, f"/api/sos/{sos['id']}/cancel", "POST", {})[0] == 200

        status, sos2 = request(warga, "/api/sos", "POST", {"category": "keamanan", "scope": "rw", "mode": "public"})
        assert status == 201
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE sos_events SET cancel_deadline=0 WHERE id=?", (sos2["id"],))
        request(satpam, "/api/bootstrap")
        assert request(satpam, f"/api/sos/{sos2['id']}/respond", "POST", {"action": "menuju"})[0] == 200
        assert request(satpam, f"/api/sos/{sos2['id']}/resolve", "POST", {"resolution_code": "ditangani"})[0] == 200

        status, complaint = request(warga, "/api/complaints", "POST", {"title": "Sampah menumpuk", "category": "Kebersihan", "location": "RT 01", "description": "Mohon segera dibersihkan."})
        assert status == 201
        assert request(ketua, f"/api/complaints/{complaint['id']}/transition", "POST", {"status": "Ditinjau"})[0] == 200
        assert request(ketua, f"/api/complaints/{complaint['id']}/transition", "POST", {"status": "Selesai"})[0] == 409

        invoice = wb["invoices"][0]
        assert request(warga, "/api/payment-proofs", "POST", {"invoice_id": invoice["id"], "amount": invoice["amount_due"], "reference": "TRX-TEST-001"})[0] == 201
        status, letter = request(warga, "/api/letters", "POST", {"letter_type": "Surat Pengantar Domisili", "purpose": "Administrasi pekerjaan"})
        assert status == 201
        assert request(ketua, f"/api/letters/{letter['id']}/decision", "POST", {"decision": "approve"})[1]["status"] == "rt_approved"
        issued_status, issued = request(rw, f"/api/letters/{letter['id']}/decision", "POST", {"decision": "approve"})
        assert issued_status == 200 and issued["status"] == "issued" and issued["verification_token"]

        status, guest = request(warga, "/api/guest-passes", "POST", {"guest_name": "Budi", "purpose": "Berkunjung", "duration_hours": 2})
        assert status == 201 and guest["token"]
        assert request(satpam, "/api/guest-passes/scan", "POST", {"token": guest["token"]})[0] == 200
        assert request(satpam, "/api/guest-passes/scan", "POST", {"token": guest["token"]})[0] == 409
        assert request(satpam, "/api/patrol/check-in", "POST", {"checkpoint": "Gerbang Utama"})[0] == 201

        vote_id = wb["voting"][0]["id"]
        assert request(warga, f"/api/voting/{vote_id}/vote", "POST", {"option_index": 0})[0] == 201
        assert request(warga, f"/api/voting/{vote_id}/vote", "POST", {"option_index": 1})[0] == 409
        status, pref = request(warga, "/api/preferences", "POST", {"theme": "dark", "accessibility_mode": True})
        assert status == 200 and pref["theme"] == "dark" and pref["accessibility_mode"] == 1

        print("SMOKE TEST OK: auth/RBAC, SOS, laporan, iuran, surat, Guest Pass, patroli, voting, preferensi")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
