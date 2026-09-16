#!/usr/bin/env python3
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DB_PATH = Path(os.environ.get("RW10_DB_PATH", ROOT / "data" / "rw10.db"))
HOST = os.environ.get("RW10_HOST", "0.0.0.0")
PORT = int(os.environ.get("RW10_PORT", "8000"))
COOKIE_NAME = "rw10_session"
MAX_BODY = 2_000_000
SESSION_TTL = 60 * 60 * 24 * 30
ACTIVE_ALERT_STATES = ("cancel_window", "active", "acknowledged", "responding")
STAFF_ROLES = {"ketua_rt", "pengurus_rw", "satpam_rw"}
RESPONDER_ROLES = {"ketua_rt", "pengurus_rw", "satpam_rw"}
MANAGER_ROLES = {"pengurus_rw"}


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def password_hash(pin, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 210_000)
    return f"{salt}${digest.hex()}"


def password_ok(pin, stored):
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    actual = password_hash(pin, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_column(conn, table, column, definition):
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              phone TEXT UNIQUE NOT NULL,
              name TEXT NOT NULL,
              rt TEXT NOT NULL,
              house TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT 'warga',
              pin_hash TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS sessions (
              token_hash TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sos_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id),
              category TEXT NOT NULL,
              scope TEXT NOT NULL DEFAULT 'rw',
              note TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'active',
              created_at TEXT NOT NULL,
              cancelled_at TEXT,
              resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sos_responses (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              sos_id INTEGER NOT NULL REFERENCES sos_events(id) ON DELETE CASCADE,
              user_id INTEGER NOT NULL REFERENCES users(id),
              action TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(sos_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS complaints (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id),
              title TEXT NOT NULL,
              category TEXT NOT NULL,
              location TEXT NOT NULL,
              description TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'Diterima',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS complaint_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
              actor_id INTEGER NOT NULL REFERENCES users(id),
              from_status TEXT,
              to_status TEXT NOT NULL,
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS content (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              type TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              body TEXT NOT NULL DEFAULT '',
              category TEXT NOT NULL DEFAULT '',
              event_date TEXT,
              location TEXT NOT NULL DEFAULT '',
              featured INTEGER NOT NULL DEFAULT 0,
              published INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS organizations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              short_name TEXT NOT NULL,
              description TEXT NOT NULL,
              accent TEXT NOT NULL DEFAULT 'blue',
              active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS organization_members (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              position TEXT NOT NULL,
              sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS dues_invoices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id),
              period TEXT NOT NULL,
              amount_due INTEGER NOT NULL,
              amount_paid INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'belum_lunas',
              due_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(user_id, period)
            );
            CREATE TABLE IF NOT EXISTS payment_proofs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              invoice_id INTEGER NOT NULL REFERENCES dues_invoices(id),
              user_id INTEGER NOT NULL REFERENCES users(id),
              reference TEXT NOT NULL,
              amount INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'menunggu_verifikasi',
              created_at TEXT NOT NULL,
              verified_by INTEGER REFERENCES users(id),
              verified_at TEXT
            );
            CREATE TABLE IF NOT EXISTS letters (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id),
              letter_type TEXT NOT NULL,
              purpose TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'submitted_rt',
              rt_note TEXT NOT NULL DEFAULT '',
              rw_note TEXT NOT NULL DEFAULT '',
              issued_number TEXT,
              verification_token_hash TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS guest_passes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL REFERENCES users(id),
              guest_name TEXT NOT NULL,
              purpose TEXT NOT NULL,
              valid_until INTEGER NOT NULL,
              token_hash TEXT UNIQUE NOT NULL,
              status TEXT NOT NULL DEFAULT 'active',
              checked_in_at TEXT,
              checked_out_at TEXT,
              guard_id INTEGER REFERENCES users(id),
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS patrol_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              guard_id INTEGER NOT NULL REFERENCES users(id),
              checkpoint TEXT NOT NULL,
              result TEXT NOT NULL DEFAULT 'valid',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS market_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_id INTEGER NOT NULL REFERENCES users(id),
              name TEXT NOT NULL,
              category TEXT NOT NULL,
              price_label TEXT NOT NULL,
              whatsapp TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS voting_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              options_json TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'draft',
              opens_at INTEGER NOT NULL,
              closes_at INTEGER NOT NULL,
              created_by INTEGER NOT NULL REFERENCES users(id),
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS votes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              voting_session_id INTEGER NOT NULL REFERENCES voting_sessions(id) ON DELETE CASCADE,
              house_key TEXT NOT NULL,
              user_id INTEGER NOT NULL REFERENCES users(id),
              option_index INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(voting_session_id, house_key)
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor_id INTEGER REFERENCES users(id),
              action TEXT NOT NULL,
              resource_type TEXT NOT NULL,
              resource_id TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
              key TEXT NOT NULL,
              user_id INTEGER NOT NULL REFERENCES users(id),
              endpoint TEXT NOT NULL,
              response_json TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              PRIMARY KEY(key, user_id, endpoint)
            );
            """
        )
        ensure_column(conn, "users", "theme", "TEXT NOT NULL DEFAULT 'system'")
        ensure_column(conn, "users", "accessibility_mode", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "sos_events", "mode", "TEXT NOT NULL DEFAULT 'public'")
        ensure_column(conn, "sos_events", "cancel_deadline", "INTEGER")
        ensure_column(conn, "sos_events", "ack_at", "TEXT")
        ensure_column(conn, "sos_events", "ack_by", "INTEGER REFERENCES users(id)")
        ensure_column(conn, "sos_events", "resolution_code", "TEXT")
        ensure_column(conn, "complaints", "updated_at", "TEXT")
        ensure_column(conn, "complaints", "resolved_at", "TEXT")

        conn.execute("UPDATE users SET role='pengurus_rw' WHERE role='admin'")
        conn.execute("UPDATE users SET role='satpam_rw' WHERE role='petugas'")
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            seed_users = [
                ("081200000010", "Edwin", "01", "Rumah 10", "pengurus_rw", "1010"),
                ("081200000001", "Ahmad", "01", "Rumah 12", "warga", "0101"),
                ("081200000002", "Siti", "02", "Pos Satpam RW10", "satpam_rw", "0202"),
                ("081200000003", "Ketua RT 01", "01", "RT 01", "ketua_rt", "0303"),
            ]
            conn.executemany(
                "INSERT INTO users(phone,name,rt,house,role,pin_hash) VALUES(?,?,?,?,?,?)",
                [(p, n, rt, house, role, password_hash(pin)) for p, n, rt, house, role, pin in seed_users],
            )
        elif not conn.execute("SELECT id FROM users WHERE phone='081200000003'").fetchone():
            conn.execute(
                "INSERT INTO users(phone,name,rt,house,role,pin_hash) VALUES(?,?,?,?,?,?)",
                ("081200000003", "Ketua RT 01", "01", "RT 01", "ketua_rt", password_hash("0303")),
            )

        if conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO complaints(user_id,title,category,location,description,status,created_at,updated_at) VALUES(1,?,?,?,?,?,?,?)",
                ("Lampu Jalan Mati", "Fasilitas", "RT 01", "Lampu depan gang padam.", "Diproses", now_iso(), now_iso()),
            )
        conn.execute("UPDATE complaints SET updated_at=COALESCE(updated_at,created_at)")

        if conn.execute("SELECT COUNT(*) FROM content").fetchone()[0] == 0:
            items = [
                ("announcement", "Kerja Bakti Minggu Pagi", "Bersih-bersih lingkungan RT01–RT04.", "Warga membawa alat kebersihan masing-masing.", "Lingkungan", "2026-09-20T07:00:00+07:00", "Pos RW10", 1),
                ("activity", "Ronda Malam Bersama", "Jadwal ronda gabungan dan pengecekan titik rawan.", "Koordinasi keamanan setiap RT.", "Keamanan", "2026-09-18T22:00:00+07:00", "Pos Ronda", 0),
                ("activity", "Posyandu Balita", "Pemeriksaan rutin dan pendataan balita RW10.", "Bawa buku KIA.", "Kesehatan", "2026-09-21T08:00:00+07:00", "Posyandu RW10", 0),
                ("news", "Program Digitalisasi Layanan RW10 Dimulai", "RW10+ memasuki tahap uji coba internal untuk RT01–RT04.", "Fitur darurat dan perangkat fisik masih simulasi.", "Teknologi", None, "RW10", 1),
                ("notification", "Uji Coba RW10+", "Seluruh fitur darurat masih dalam mode simulasi.", "Gunakan 110, 112, atau 119 untuk bantuan resmi.", "Sistem", None, "", 0),
            ]
            conn.executemany(
                "INSERT INTO content(type,title,summary,body,category,event_date,location,featured,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                [(*item, now_iso()) for item in items],
            )
        if conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0:
            orgs = [
                ("Pemerintahan RW10", "RW10", "Koordinasi pelayanan warga RT01 sampai RT04.", "blue"),
                ("POKJA 10", "POKJA", "Wadah kegiatan dan kolaborasi pemuda lingkungan.", "amber"),
                ("IRMAL", "IRMAL", "Kegiatan remaja masjid dan sosial keagamaan.", "emerald"),
                ("Posyandu RW10", "POSYANDU", "Pelayanan kesehatan ibu, bayi, balita, dan lansia.", "rose"),
                ("Keamanan Lingkungan", "SATPAM", "Koordinasi patroli dan respons keamanan warga.", "slate"),
            ]
            conn.executemany("INSERT INTO organizations(name,short_name,description,accent) VALUES(?,?,?,?)", orgs)
            conn.executemany(
                "INSERT INTO organization_members(organization_id,name,position,sort_order) VALUES(?,?,?,?)",
                [
                    (1, "Yusuf Saepudin", "Ketua RW10", 1),
                    (1, "Belum diisi", "Ketua RT01", 10),
                    (1, "Belum diisi", "Ketua RT02", 11),
                    (1, "Belum diisi", "Ketua RT03", 12),
                    (1, "Belum diisi", "Ketua RT04", 13),
                    (2, "Dea Erlangga", "Ketua POKJA 10", 1),
                    (3, "Ustd Saepurahman", "Pembina IRMAL/DKM", 1),
                ],
            )
        if conn.execute("SELECT COUNT(*) FROM dues_invoices").fetchone()[0] == 0:
            for user_id in [row[0] for row in conn.execute("SELECT id FROM users WHERE role='warga'")]:
                conn.execute(
                    "INSERT OR IGNORE INTO dues_invoices(user_id,period,amount_due,amount_paid,status,due_at,created_at) VALUES(?,?,?,?,?,?,?)",
                    (user_id, "2026-09", 150000, 0, "belum_lunas", "2026-09-30", now_iso()),
                )
        if conn.execute("SELECT COUNT(*) FROM market_items").fetchone()[0] == 0:
            owner = conn.execute("SELECT id FROM users WHERE role='warga' ORDER BY id LIMIT 1").fetchone()
            if owner:
                conn.executemany(
                    "INSERT INTO market_items(owner_id,name,category,price_label,whatsapp,description,created_at) VALUES(?,?,?,?,?,?,?)",
                    [
                        (owner[0], "Katering Bu Sari", "Kuliner", "Mulai Rp15.000", "6281200000001", "Nasi box dan konsumsi kegiatan warga.", now_iso()),
                        (owner[0], "Servis Elektronik Ahmad", "Jasa", "Hubungi penjual", "6281200000001", "Perbaikan kipas, pompa air, dan alat rumah tangga.", now_iso()),
                    ],
                )
        if conn.execute("SELECT COUNT(*) FROM voting_sessions").fetchone()[0] == 0:
            manager = conn.execute("SELECT id FROM users WHERE role='pengurus_rw' ORDER BY id LIMIT 1").fetchone()
            if manager:
                now = int(time.time())
                conn.execute(
                    "INSERT INTO voting_sessions(title,description,options_json,status,opens_at,closes_at,created_by,created_at) VALUES(?,?,?,'open',?,?,?,?)",
                    ("Prioritas Program Lingkungan", "Pilih program yang paling penting untuk RW10.", json.dumps(["Penerangan jalan", "Perbaikan drainase", "Penambahan CCTV"]), now - 3600, now + 604800, manager[0], now_iso()),
                )


def clean_sessions():
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (int(time.time()),))
        conn.execute("DELETE FROM idempotency_keys WHERE created_at < ?", (int(time.time()) - 86400,))


def promote_due_alerts(conn):
    conn.execute(
        "UPDATE sos_events SET status='active' WHERE status='cancel_window' AND cancel_deadline<=?",
        (int(time.time()),),
    )


def role_label(role):
    return {
        "warga": "Warga",
        "ketua_rt": "Ketua RT",
        "pengurus_rw": "Pengurus RW",
        "satpam_rw": "Satpam RW",
    }.get(role, role)


class App(BaseHTTPRequestHandler):
    server_version = "RW10Plus/0.3.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(self), microphone=(), geolocation=(self)")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; manifest-src 'self'",
        )

    def json_response(self, data, status=200, extra_headers=None):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        for key, value in extra_headers or []:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Ukuran data tidak valid") from exc
        if size <= 0 or size > MAX_BODY:
            raise ValueError("Data kosong atau terlalu besar")
        try:
            return json.loads(self.rfile.read(size))
        except json.JSONDecodeError as exc:
            raise ValueError("Format JSON tidak valid") from exc

    def session_user(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            return None
        morsel = jar.get(COOKIE_NAME)
        if not morsel:
            return None
        with db() as conn:
            row = conn.execute(
                """SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                   WHERE s.token_hash=? AND s.expires_at>? AND u.active=1""",
                (token_hash(morsel.value), int(time.time())),
            ).fetchone()
        return dict(row) if row else None

    def require_user(self):
        user = self.session_user()
        if not user:
            self.json_response({"ok": False, "error": "Silakan masuk kembali"}, 401)
        return user

    def public_user(self, user):
        data = {key: user[key] for key in ("id", "name", "phone", "rt", "house", "role", "theme", "accessibility_mode")}
        data["role_label"] = role_label(user["role"])
        return data

    def audit(self, conn, user, action, resource_type, resource_id, detail=""):
        conn.execute(
            "INSERT INTO audit_logs(actor_id,action,resource_type,resource_id,detail,created_at) VALUES(?,?,?,?,?,?)",
            (user["id"], action, resource_type, str(resource_id), detail[:500], now_iso()),
        )

    def allowed_row(self, user, owner_id=None, rt=None):
        if user["role"] in {"pengurus_rw", "satpam_rw"}:
            return True
        if user["role"] == "ketua_rt":
            return rt == user["rt"]
        return owner_id == user["id"]

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self.json_response({"ok": True, "service": "RW10+", "version": "0.3.0", "toa_mode": "simulation", "environment": "internal"})
        if path == "/api/me":
            user = self.session_user()
            return self.json_response({"ok": bool(user), "user": self.public_user(user) if user else None}, 200 if user else 401)
        if path.startswith("/api/"):
            user = self.require_user()
            if not user:
                return
            if path == "/api/bootstrap":
                return self.bootstrap(user)
            if path == "/api/events":
                try:
                    since = int(parse_qs(parsed.query).get("since", ["0"])[0] or 0)
                except ValueError:
                    return self.json_response({"ok": False, "error": "Parameter since tidak valid"}, 400)
                return self.events(user, since)
            return self.json_response({"ok": False, "error": "Endpoint tidak ditemukan"}, 404)
        return self.serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/login":
            return self.login()
        if path == "/api/logout":
            return self.logout()
        user = self.require_user()
        if not user:
            return
        if path == "/api/preferences":
            return self.update_preferences(user)
        if path == "/api/sos":
            return self.create_sos(user)
        if path.startswith("/api/sos/"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[3] == "respond":
                return self.respond_sos(user, parts[2])
            if len(parts) == 4 and parts[3] == "cancel":
                return self.cancel_sos(user, parts[2])
            if len(parts) == 4 and parts[3] == "resolve":
                return self.resolve_sos(user, parts[2])
        if path == "/api/complaints":
            return self.create_complaint(user)
        if path.startswith("/api/complaints/") and path.endswith("/transition"):
            return self.transition_complaint(user, path.split("/")[3])
        if path == "/api/payment-proofs":
            return self.create_payment_proof(user)
        if path == "/api/letters":
            return self.create_letter(user)
        if path.startswith("/api/letters/") and path.endswith("/decision"):
            return self.decide_letter(user, path.split("/")[3])
        if path == "/api/guest-passes":
            return self.create_guest_pass(user)
        if path == "/api/guest-passes/scan":
            return self.scan_guest_pass(user)
        if path == "/api/patrol/check-in":
            return self.patrol_check_in(user)
        if path.startswith("/api/voting/") and path.endswith("/vote"):
            return self.cast_vote(user, path.split("/")[3])
        return self.json_response({"ok": False, "error": "Endpoint tidak ditemukan"}, 404)

    def login(self):
        try:
            body = self.read_json()
            phone = str(body.get("phone", "")).strip()
            pin = str(body.get("pin", "")).strip()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        with db() as conn:
            user = conn.execute("SELECT * FROM users WHERE phone=? AND active=1", (phone,)).fetchone()
            if not user or not password_ok(pin, user["pin_hash"]):
                time.sleep(0.35)
                return self.json_response({"ok": False, "error": "Nomor HP atau PIN salah"}, 401)
            token = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                (token_hash(token), user["id"], int(time.time()) + SESSION_TTL),
            )
            self.audit(conn, dict(user), "LOGIN", "session", token_hash(token)[:12])
        cookie = f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}"
        return self.json_response({"ok": True, "user": self.public_user(dict(user))}, extra_headers=[("Set-Cookie", cookie)])

    def logout(self):
        user = self.session_user()
        jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        if jar.get(COOKIE_NAME):
            with db() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(jar[COOKIE_NAME].value),))
                if user:
                    self.audit(conn, user, "LOGOUT", "session", str(user["id"]))
        return self.json_response({"ok": True}, extra_headers=[("Set-Cookie", f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")])

    def bootstrap(self, user):
        cameras = [
            {"id": 1, "name": "Gerbang Utama", "rt": "01", "status": "online"},
            {"id": 2, "name": "Jalan RT 02", "rt": "02", "status": "online"},
            {"id": 3, "name": "Pos Ronda", "rt": "01", "status": "online"},
            {"id": 4, "name": "Lapangan", "rt": "03", "status": "offline"},
        ]
        with db() as conn:
            promote_due_alerts(conn)
            complaint_rows = conn.execute(
                "SELECT c.*,u.name reporter,u.rt reporter_rt FROM complaints c JOIN users u ON u.id=c.user_id ORDER BY c.id DESC LIMIT 100"
            ).fetchall()
            complaints = [dict(row) for row in complaint_rows if self.allowed_row(user, row["user_id"], row["reporter_rt"])]
            event_rows = conn.execute(
                """SELECT s.*,u.name,u.rt,u.house,a.name ack_name,
                   (SELECT COUNT(*) FROM sos_responses r WHERE r.sos_id=s.id) responders
                   FROM sos_events s JOIN users u ON u.id=s.user_id
                   LEFT JOIN users a ON a.id=s.ack_by ORDER BY s.id DESC LIMIT 100"""
            ).fetchall()
            events = []
            for row in event_rows:
                item = dict(row)
                if item["status"] == "cancel_window" and user["id"] != item["user_id"]:
                    continue
                if item["mode"] == "silent" and user["id"] != item["user_id"] and user["role"] not in {"satpam_rw", "pengurus_rw"}:
                    continue
                if user["role"] == "ketua_rt" and item["rt"] != user["rt"]:
                    continue
                events.append(item)
            invoice_rows = conn.execute(
                "SELECT d.*,u.name,u.rt,u.house FROM dues_invoices d JOIN users u ON u.id=d.user_id ORDER BY d.period DESC,d.id DESC"
            ).fetchall()
            invoices = [dict(row) for row in invoice_rows if user["role"] == "pengurus_rw" or row["user_id"] == user["id"] or (user["role"] == "ketua_rt" and row["rt"] == user["rt"])]
            letter_rows = conn.execute(
                "SELECT l.*,u.name,u.rt,u.house FROM letters l JOIN users u ON u.id=l.user_id ORDER BY l.id DESC"
            ).fetchall()
            letters = [dict(row) for row in letter_rows if user["role"] == "pengurus_rw" or row["user_id"] == user["id"] or (user["role"] == "ketua_rt" and row["rt"] == user["rt"])]
            pass_rows = conn.execute(
                "SELECT g.*,u.name owner_name,u.rt,u.house FROM guest_passes g JOIN users u ON u.id=g.user_id ORDER BY g.id DESC"
            ).fetchall()
            guest_passes = [dict(row) for row in pass_rows if self.allowed_row(user, row["user_id"], row["rt"])]
            patrol = [dict(row) for row in conn.execute(
                "SELECT p.*,u.name guard_name FROM patrol_logs p JOIN users u ON u.id=p.guard_id ORDER BY p.id DESC LIMIT 20"
            )]
            market = [dict(row) for row in conn.execute(
                "SELECT m.*,u.name owner_name,u.rt FROM market_items m JOIN users u ON u.id=m.owner_id WHERE m.active=1 ORDER BY m.id DESC"
            )]
            voting = []
            for row in conn.execute("SELECT * FROM voting_sessions WHERE status='open' ORDER BY closes_at,id DESC"):
                item = dict(row)
                item["options"] = json.loads(item.pop("options_json"))
                item["has_voted"] = bool(conn.execute("SELECT 1 FROM votes WHERE voting_session_id=? AND house_key=?", (item["id"], f"{user['rt']}:{user['house'].lower()}" )).fetchone())
                voting.append(item)
            content = [dict(row) for row in conn.execute("SELECT * FROM content WHERE published=1 ORDER BY COALESCE(event_date,created_at) DESC,id DESC")]
            organizations = [dict(row) for row in conn.execute("SELECT * FROM organizations WHERE active=1 ORDER BY id")]
            members = [dict(row) for row in conn.execute("SELECT * FROM organization_members ORDER BY organization_id,sort_order,id")]
            pending_alerts = sum(1 for event in events if event["status"] in ACTIVE_ALERT_STATES)
        return self.json_response({
            "ok": True,
            "user": self.public_user(user),
            "capabilities": {
                "can_respond_sos": user["role"] in RESPONDER_ROLES,
                "can_manage_rw": user["role"] in MANAGER_ROLES,
                "can_scan_guest": user["role"] in {"satpam_rw", "pengurus_rw"},
                "can_patrol": user["role"] == "satpam_rw",
            },
            "cameras": cameras,
            "complaints": complaints,
            "events": events,
            "invoices": invoices,
            "letters": letters,
            "guest_passes": guest_passes,
            "patrol": patrol,
            "market": market,
            "voting": voting,
            "content": content,
            "organizations": organizations,
            "members": members,
            "stats": {"active_alerts": pending_alerts, "patrol_minutes_ago": 12, "environment_status": "AMAN"},
            "toa_mode": "simulation",
        })

    def events(self, user, since):
        with db() as conn:
            promote_due_alerts(conn)
            rows = conn.execute(
                """SELECT s.*,u.name,u.rt,u.house,a.name ack_name,
                   (SELECT COUNT(*) FROM sos_responses r WHERE r.sos_id=s.id) responders
                   FROM sos_events s JOIN users u ON u.id=s.user_id
                   LEFT JOIN users a ON a.id=s.ack_by WHERE s.id>? ORDER BY s.id""",
                (since,),
            ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            if item["status"] == "cancel_window" and user["id"] != item["user_id"]:
                continue
            if item["mode"] == "silent" and user["id"] != item["user_id"] and user["role"] not in {"satpam_rw", "pengurus_rw"}:
                continue
            if user["role"] == "ketua_rt" and item["rt"] != user["rt"]:
                continue
            events.append(item)
        return self.json_response({"ok": True, "events": events})

    def update_preferences(self, user):
        try:
            body = self.read_json()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        theme = str(body.get("theme", user["theme"]))
        accessibility = 1 if body.get("accessibility_mode", user["accessibility_mode"]) else 0
        if theme not in {"system", "light", "dark"}:
            return self.json_response({"ok": False, "error": "Tema tidak valid"}, 400)
        with db() as conn:
            conn.execute("UPDATE users SET theme=?,accessibility_mode=? WHERE id=?", (theme, accessibility, user["id"]))
            self.audit(conn, user, "UPDATE_PREFERENCES", "user", user["id"], f"theme={theme},elderly={accessibility}")
        return self.json_response({"ok": True, "theme": theme, "accessibility_mode": accessibility})

    def create_sos(self, user):
        idem = self.headers.get("Idempotency-Key", "").strip()[:120]
        if idem:
            with db() as conn:
                cached = conn.execute("SELECT response_json FROM idempotency_keys WHERE key=? AND user_id=? AND endpoint='sos'", (idem, user["id"])).fetchone()
                if cached:
                    return self.json_response(json.loads(cached[0]), 201)
        try:
            body = self.read_json()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        category = str(body.get("category", "")).strip().lower()
        scope = str(body.get("scope", "rw")).strip().lower()
        mode = str(body.get("mode", "public")).strip().lower()
        note = str(body.get("note", "")).strip()[:300]
        if category not in {"keamanan", "kebakaran", "medis", "kecelakaan", "bencana"}:
            return self.json_response({"ok": False, "error": "Kategori SOS tidak valid"}, 400)
        if scope not in {"rt", "rw", "petugas"} or mode not in {"public", "silent"}:
            return self.json_response({"ok": False, "error": "Mode atau jangkauan tidak valid"}, 400)
        deadline = int(time.time()) + 10
        with db() as conn:
            placeholders = ",".join("?" for _ in ACTIVE_ALERT_STATES)
            recent = conn.execute(
                f"SELECT id FROM sos_events WHERE user_id=? AND status IN ({placeholders})",
                (user["id"], *ACTIVE_ALERT_STATES),
            ).fetchone()
            if recent:
                return self.json_response({"ok": False, "error": "Anda masih memiliki SOS aktif"}, 409)
            cur = conn.execute(
                "INSERT INTO sos_events(user_id,category,scope,note,status,created_at,mode,cancel_deadline) VALUES(?,?,?,?,?,?,?,?)",
                (user["id"], category, scope, note, "cancel_window", now_iso(), mode, deadline),
            )
            event_id = cur.lastrowid
            self.audit(conn, user, "TRIGGER", "emergency", event_id, f"{category}/{mode}/{scope}")
            response = {"ok": True, "id": event_id, "status": "cancel_window", "cancel_deadline": deadline, "toa": "simulation"}
            if idem:
                conn.execute(
                    "INSERT INTO idempotency_keys(key,user_id,endpoint,response_json,created_at) VALUES(?,?,?,?,?)",
                    (idem, user["id"], "sos", json.dumps(response), int(time.time())),
                )
        return self.json_response(response, 201)

    def cancel_sos(self, user, raw_id):
        try:
            event_id = int(raw_id)
        except ValueError:
            return self.json_response({"ok": False, "error": "ID tidak valid"}, 400)
        with db() as conn:
            promote_due_alerts(conn)
            event = conn.execute("SELECT * FROM sos_events WHERE id=?", (event_id,)).fetchone()
            if not event:
                return self.json_response({"ok": False, "error": "SOS tidak ditemukan"}, 404)
            if event["user_id"] != user["id"] and user["role"] not in MANAGER_ROLES:
                return self.json_response({"ok": False, "error": "Tidak diizinkan"}, 403)
            if event["status"] not in ACTIVE_ALERT_STATES:
                return self.json_response({"ok": False, "error": "SOS sudah ditutup"}, 409)
            if event["user_id"] == user["id"] and event["status"] != "cancel_window":
                return self.json_response({"ok": False, "error": "Batas pembatalan 10 detik sudah berakhir"}, 409)
            conn.execute("UPDATE sos_events SET status='cancelled',cancelled_at=? WHERE id=?", (now_iso(), event_id))
            self.audit(conn, user, "CANCEL", "emergency", event_id)
        return self.json_response({"ok": True, "status": "cancelled"})

    def respond_sos(self, user, raw_id):
        if user["role"] not in RESPONDER_ROLES:
            return self.json_response({"ok": False, "error": "Hanya petugas yang dapat merespons"}, 403)
        try:
            event_id = int(raw_id)
            body = self.read_json()
            action = str(body.get("action", "menuju")).strip().lower()
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Data respons tidak valid"}, 400)
        if action not in {"menuju", "hubungi", "lihat"}:
            return self.json_response({"ok": False, "error": "Respons tidak valid"}, 400)
        with db() as conn:
            promote_due_alerts(conn)
            event = conn.execute("SELECT * FROM sos_events WHERE id=?", (event_id,)).fetchone()
            if not event or event["status"] not in {"active", "acknowledged", "responding"}:
                return self.json_response({"ok": False, "error": "SOS belum dikirim atau sudah tidak aktif"}, 409)
            if user["role"] == "ketua_rt":
                reporter = conn.execute("SELECT rt FROM users WHERE id=?", (event["user_id"],)).fetchone()
                if not reporter or reporter["rt"] != user["rt"]:
                    return self.json_response({"ok": False, "error": "SOS berada di luar RT Anda"}, 403)
            conn.execute(
                "INSERT INTO sos_responses(sos_id,user_id,action,created_at) VALUES(?,?,?,?) ON CONFLICT(sos_id,user_id) DO UPDATE SET action=excluded.action,created_at=excluded.created_at",
                (event_id, user["id"], action, now_iso()),
            )
            status = "responding" if action == "menuju" else "acknowledged"
            conn.execute(
                "UPDATE sos_events SET status=?,ack_at=COALESCE(ack_at,?),ack_by=COALESCE(ack_by,?) WHERE id=?",
                (status, now_iso(), user["id"], event_id),
            )
            self.audit(conn, user, "ACKNOWLEDGE", "emergency", event_id, action)
        return self.json_response({"ok": True, "status": status})

    def resolve_sos(self, user, raw_id):
        if user["role"] not in RESPONDER_ROLES:
            return self.json_response({"ok": False, "error": "Hanya petugas yang dapat menutup SOS"}, 403)
        try:
            event_id = int(raw_id)
            body = self.read_json()
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Data tidak valid"}, 400)
        code = str(body.get("resolution_code", "aman")).strip().lower()
        if code not in {"aman", "ditangani", "false_alarm", "dirujuk"}:
            return self.json_response({"ok": False, "error": "Kode penyelesaian tidak valid"}, 400)
        with db() as conn:
            event = conn.execute("SELECT s.status,u.rt FROM sos_events s JOIN users u ON u.id=s.user_id WHERE s.id=?", (event_id,)).fetchone()
            if not event:
                return self.json_response({"ok": False, "error": "SOS tidak ditemukan"}, 404)
            if event["status"] not in {"active", "acknowledged", "responding"}:
                return self.json_response({"ok": False, "error": "SOS tidak dapat ditutup"}, 409)
            if user["role"] == "ketua_rt" and event["rt"] != user["rt"]:
                return self.json_response({"ok": False, "error": "SOS berada di luar RT Anda"}, 403)
            conn.execute("UPDATE sos_events SET status='resolved',resolved_at=?,resolution_code=? WHERE id=?", (now_iso(), code, event_id))
            self.audit(conn, user, "RESOLVE", "emergency", event_id, code)
        return self.json_response({"ok": True, "status": "resolved"})

    def create_complaint(self, user):
        try:
            body = self.read_json()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        title = str(body.get("title", "")).strip()[:100]
        category = str(body.get("category", "Umum")).strip()[:50]
        location = str(body.get("location", f"RT {user['rt']}")).strip()[:100]
        description = str(body.get("description", "")).strip()[:1000]
        if len(title) < 4 or len(description) < 6:
            return self.json_response({"ok": False, "error": "Judul atau keterangan terlalu pendek"}, 400)
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO complaints(user_id,title,category,location,description,status,created_at,updated_at) VALUES(?,?,?,?,?,'Diterima',?,?)",
                (user["id"], title, category, location, description, now_iso(), now_iso()),
            )
            complaint_id = cur.lastrowid
            conn.execute(
                "INSERT INTO complaint_events(complaint_id,actor_id,to_status,note,created_at) VALUES(?,?,?,?,?)",
                (complaint_id, user["id"], "Diterima", "Laporan dibuat", now_iso()),
            )
            self.audit(conn, user, "CREATE", "complaint", complaint_id)
        return self.json_response({"ok": True, "id": complaint_id, "status": "Diterima"}, 201)

    def transition_complaint(self, user, raw_id):
        if user["role"] not in STAFF_ROLES:
            return self.json_response({"ok": False, "error": "Tidak diizinkan"}, 403)
        try:
            complaint_id = int(raw_id)
            body = self.read_json()
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Data tidak valid"}, 400)
        target = str(body.get("status", "")).strip()
        note = str(body.get("note", "")).strip()[:500]
        allowed = {
            "Diterima": {"Ditinjau"},
            "Ditinjau": {"Diproses", "Ditolak"},
            "Diproses": {"Menunggu Pihak Luar", "Selesai"},
            "Menunggu Pihak Luar": {"Diproses", "Selesai"},
            "Selesai": {"Ditutup"},
        }
        with db() as conn:
            row = conn.execute("SELECT c.*,u.rt reporter_rt FROM complaints c JOIN users u ON u.id=c.user_id WHERE c.id=?", (complaint_id,)).fetchone()
            if not row:
                return self.json_response({"ok": False, "error": "Laporan tidak ditemukan"}, 404)
            if user["role"] == "ketua_rt" and row["reporter_rt"] != user["rt"]:
                return self.json_response({"ok": False, "error": "Laporan berada di luar RT Anda"}, 403)
            if target not in allowed.get(row["status"], set()):
                return self.json_response({"ok": False, "error": f"Transisi {row['status']} → {target} tidak diizinkan"}, 409)
            resolved = now_iso() if target in {"Selesai", "Ditutup"} else None
            conn.execute("UPDATE complaints SET status=?,updated_at=?,resolved_at=COALESCE(?,resolved_at) WHERE id=?", (target, now_iso(), resolved, complaint_id))
            conn.execute(
                "INSERT INTO complaint_events(complaint_id,actor_id,from_status,to_status,note,created_at) VALUES(?,?,?,?,?,?)",
                (complaint_id, user["id"], row["status"], target, note, now_iso()),
            )
            self.audit(conn, user, "TRANSITION", "complaint", complaint_id, f"{row['status']}->{target}")
        return self.json_response({"ok": True, "status": target})

    def create_payment_proof(self, user):
        try:
            body = self.read_json()
            invoice_id = int(body.get("invoice_id"))
            amount = int(body.get("amount"))
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Invoice atau nominal tidak valid"}, 400)
        reference = str(body.get("reference", "")).strip()[:120]
        if amount <= 0 or len(reference) < 3:
            return self.json_response({"ok": False, "error": "Nominal atau referensi belum lengkap"}, 400)
        with db() as conn:
            invoice = conn.execute("SELECT * FROM dues_invoices WHERE id=?", (invoice_id,)).fetchone()
            if not invoice:
                return self.json_response({"ok": False, "error": "Tagihan tidak ditemukan"}, 404)
            if invoice["user_id"] != user["id"] and user["role"] not in MANAGER_ROLES:
                return self.json_response({"ok": False, "error": "Tidak diizinkan"}, 403)
            cur = conn.execute(
                "INSERT INTO payment_proofs(invoice_id,user_id,reference,amount,created_at) VALUES(?,?,?,?,?)",
                (invoice_id, user["id"], reference, amount, now_iso()),
            )
            self.audit(conn, user, "SUBMIT_PROOF", "payment_proof", cur.lastrowid, f"invoice={invoice_id}")
        return self.json_response({"ok": True, "id": cur.lastrowid, "status": "menunggu_verifikasi"}, 201)

    def create_letter(self, user):
        try:
            body = self.read_json()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        letter_type = str(body.get("letter_type", "")).strip()[:80]
        purpose = str(body.get("purpose", "")).strip()[:500]
        if len(letter_type) < 3 or len(purpose) < 5:
            return self.json_response({"ok": False, "error": "Jenis dan keperluan surat wajib diisi"}, 400)
        stamp = now_iso()
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO letters(user_id,letter_type,purpose,status,created_at,updated_at) VALUES(?,?,?,'submitted_rt',?,?)",
                (user["id"], letter_type, purpose, stamp, stamp),
            )
            self.audit(conn, user, "SUBMIT", "letter", cur.lastrowid, letter_type)
        return self.json_response({"ok": True, "id": cur.lastrowid, "status": "submitted_rt"}, 201)

    def decide_letter(self, user, raw_id):
        try:
            letter_id = int(raw_id)
            body = self.read_json()
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Data tidak valid"}, 400)
        decision = str(body.get("decision", "approve")).strip().lower()
        note = str(body.get("note", "")).strip()[:500]
        if decision not in {"approve", "reject", "revision"}:
            return self.json_response({"ok": False, "error": "Keputusan tidak valid"}, 400)
        with db() as conn:
            row = conn.execute("SELECT l.*,u.rt FROM letters l JOIN users u ON u.id=l.user_id WHERE l.id=?", (letter_id,)).fetchone()
            if not row:
                return self.json_response({"ok": False, "error": "Surat tidak ditemukan"}, 404)
            status = row["status"]
            if status == "submitted_rt":
                if user["role"] not in {"ketua_rt", "pengurus_rw"}:
                    return self.json_response({"ok": False, "error": "Menunggu persetujuan Ketua RT"}, 403)
                if user["role"] == "ketua_rt" and row["rt"] != user["rt"]:
                    return self.json_response({"ok": False, "error": "Surat berada di luar RT Anda"}, 403)
                next_status = "rt_approved" if decision == "approve" else ("revision" if decision == "revision" else "rejected")
                conn.execute("UPDATE letters SET status=?,rt_note=?,updated_at=? WHERE id=?", (next_status, note, now_iso(), letter_id))
            elif status == "rt_approved":
                if user["role"] not in MANAGER_ROLES:
                    return self.json_response({"ok": False, "error": "Menunggu persetujuan Pengurus RW"}, 403)
                next_status = "issued" if decision == "approve" else ("revision" if decision == "revision" else "rejected")
                number = None
                verify_hash = None
                verify_token = None
                if next_status == "issued":
                    verify_token = secrets.token_urlsafe(24)
                    verify_hash = token_hash(verify_token)
                    number = f"{letter_id:04d}/RW10/IX/2026"
                conn.execute(
                    "UPDATE letters SET status=?,rw_note=?,issued_number=?,verification_token_hash=?,updated_at=? WHERE id=?",
                    (next_status, note, number, verify_hash, now_iso(), letter_id),
                )
            else:
                return self.json_response({"ok": False, "error": "Surat tidak dapat diproses pada status ini"}, 409)
            self.audit(conn, user, "DECISION", "letter", letter_id, f"{status}->{next_status}")
        response = {"ok": True, "status": next_status}
        if next_status == "issued":
            response.update({"issued_number": number, "verification_token": verify_token})
        return self.json_response(response)

    def create_guest_pass(self, user):
        try:
            body = self.read_json()
            duration_hours = max(1, min(72, int(body.get("duration_hours", 8))))
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Durasi tidak valid"}, 400)
        guest_name = str(body.get("guest_name", "")).strip()[:80]
        purpose = str(body.get("purpose", "")).strip()[:120]
        if len(guest_name) < 2 or len(purpose) < 3:
            return self.json_response({"ok": False, "error": "Nama tamu dan tujuan wajib diisi"}, 400)
        token = secrets.token_urlsafe(18)
        valid_until = int(time.time()) + duration_hours * 3600
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO guest_passes(user_id,guest_name,purpose,valid_until,token_hash,created_at) VALUES(?,?,?,?,?,?)",
                (user["id"], guest_name, purpose, valid_until, token_hash(token), now_iso()),
            )
            self.audit(conn, user, "CREATE", "guest_pass", cur.lastrowid, f"hours={duration_hours}")
        return self.json_response({"ok": True, "id": cur.lastrowid, "token": token, "valid_until": valid_until}, 201)

    def scan_guest_pass(self, user):
        if user["role"] not in {"satpam_rw", "pengurus_rw"}:
            return self.json_response({"ok": False, "error": "Hanya Satpam/Pengurus yang dapat memindai"}, 403)
        try:
            body = self.read_json()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        token = str(body.get("token", "")).strip()
        if len(token) < 10:
            return self.json_response({"ok": False, "error": "Kode Guest Pass tidak valid"}, 400)
        with db() as conn:
            row = conn.execute(
                "SELECT g.*,u.name owner_name,u.house,u.rt FROM guest_passes g JOIN users u ON u.id=g.user_id WHERE g.token_hash=?",
                (token_hash(token),),
            ).fetchone()
            if not row:
                return self.json_response({"ok": False, "error": "Guest Pass tidak ditemukan"}, 404)
            if row["status"] != "active":
                return self.json_response({"ok": False, "error": "Guest Pass sudah digunakan atau dicabut"}, 409)
            if row["valid_until"] < int(time.time()):
                conn.execute("UPDATE guest_passes SET status='expired' WHERE id=?", (row["id"],))
                return self.json_response({"ok": False, "error": "Guest Pass sudah kedaluwarsa"}, 410)
            updated = conn.execute("UPDATE guest_passes SET status='checked_in',checked_in_at=?,guard_id=? WHERE id=? AND status='active'", (now_iso(), user["id"], row["id"]))
            if updated.rowcount != 1:
                return self.json_response({"ok": False, "error": "Guest Pass baru saja digunakan"}, 409)
            self.audit(conn, user, "CHECK_IN", "guest_pass", row["id"])
        return self.json_response({"ok": True, "status": "checked_in", "guest_name": row["guest_name"], "purpose": row["purpose"], "destination": f"{row['house']} • RT {row['rt']}", "owner_name": row["owner_name"]})

    def patrol_check_in(self, user):
        if user["role"] != "satpam_rw":
            return self.json_response({"ok": False, "error": "Hanya Satpam yang dapat check-in patroli"}, 403)
        try:
            body = self.read_json()
        except ValueError as exc:
            return self.json_response({"ok": False, "error": str(exc)}, 400)
        checkpoint = str(body.get("checkpoint", "")).strip()[:80]
        if checkpoint not in {"Gerbang Utama", "Pos Utara", "Lapangan", "Pos RW10", "Jalan RT 04"}:
            return self.json_response({"ok": False, "error": "Checkpoint tidak dikenal"}, 400)
        with db() as conn:
            cur = conn.execute("INSERT INTO patrol_logs(guard_id,checkpoint,created_at) VALUES(?,?,?)", (user["id"], checkpoint, now_iso()))
            self.audit(conn, user, "CHECK_IN", "patrol", cur.lastrowid, checkpoint)
        return self.json_response({"ok": True, "id": cur.lastrowid, "checkpoint": checkpoint}, 201)

    def cast_vote(self, user, raw_id):
        try:
            session_id = int(raw_id)
            body = self.read_json()
            option_index = int(body.get("option_index"))
        except (ValueError, TypeError):
            return self.json_response({"ok": False, "error": "Pilihan voting tidak valid"}, 400)
        now = int(time.time())
        house_key = f"{user['rt']}:{user['house'].lower()}"
        with db() as conn:
            session = conn.execute("SELECT * FROM voting_sessions WHERE id=?", (session_id,)).fetchone()
            if not session:
                return self.json_response({"ok": False, "error": "Voting tidak ditemukan"}, 404)
            options = json.loads(session["options_json"])
            if session["status"] != "open" or not (session["opens_at"] <= now <= session["closes_at"]):
                return self.json_response({"ok": False, "error": "Voting belum dibuka atau sudah ditutup"}, 409)
            if option_index < 0 or option_index >= len(options):
                return self.json_response({"ok": False, "error": "Pilihan tidak tersedia"}, 400)
            try:
                cur = conn.execute(
                    "INSERT INTO votes(voting_session_id,house_key,user_id,option_index,created_at) VALUES(?,?,?,?,?)",
                    (session_id, house_key, user["id"], option_index, now_iso()),
                )
            except sqlite3.IntegrityError:
                return self.json_response({"ok": False, "error": "Rumah ini sudah menggunakan hak suara"}, 409)
            self.audit(conn, user, "CAST", "vote", cur.lastrowid, f"session={session_id}")
        return self.json_response({"ok": True, "status": "recorded"}, 201)

    def serve_static(self, path):
        if path in {"", "/"}:
            path = "/index.html"
        candidate = (STATIC / path.lstrip("/")).resolve()
        safe = STATIC.resolve() in candidate.parents
        if not safe or not candidate.is_file():
            if safe and Path(path).suffix == "":
                candidate = STATIC / "index.html"
            else:
                return self.json_response({"ok": False, "error": "Berkas tidak ditemukan"}, 404)
        content = candidate.read_bytes()
        kind = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.security_headers()
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-cache" if candidate.name in {"index.html", "sw.js"} else "public, max-age=86400")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    init_db()
    clean_sessions()
    print(f"RW10+ v0.3.0 listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), App).serve_forever()
