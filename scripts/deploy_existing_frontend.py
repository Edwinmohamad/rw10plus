#!/usr/bin/env python3
"""Update the public UI in the existing web/app stack without Compose takeover."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

WEB = "rw10plus-web-1"
APP = "rw10plus-app-1"
BASE = "http://127.0.0.1:8080"
BEGIN = "    # BEGIN RW10 EDITORIAL FRONTEND"
END = "    # END RW10 EDITORIAL FRONTEND"


def run(*args):
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True,
                              timeout=90).stdout
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Command timed out: " + " ".join(args)) from exc


def container(name):
    return json.loads(run("docker", "inspect", name))[0]


def mount(info, destination):
    candidates = [m for m in info.get("Mounts", [])
                  if m.get("Destination") == destination and m.get("Type") == "bind"]
    if len(candidates) != 1:
        raise RuntimeError("Expected one bind mount: " + destination)
    return Path(candidates[0]["Source"]).resolve()


def configuration(original, release):
    # Only the observed single-server layout is supported; fail closed on other layouts.
    if len(re.findall(r"(?m)^\s*server\s*\{", original)) != 1:
        raise RuntimeError("Expected a single Nginx server block")
    if "root /srv/frontend;" not in original or "proxy_pass http://app:8000;" not in original:
        raise RuntimeError("Existing Nginx root/upstream differs from the supported layout")
    block = (BEGIN + "\n    location = / {\n"
             f"        try_files /_rw10_ui/{release}/index.html =404;\n"
             "    }\n" + END)
    if BEGIN in original or END in original:
        if original.count(BEGIN) != 1 or original.count(END) != 1:
            raise RuntimeError("Invalid previous deployment markers")
        return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                      lambda _: block, original, flags=re.S)
    if re.search(r"location\s*=\s*/\s*\{", original):
        raise RuntimeError("An existing exact homepage route requires manual review")
    return re.sub(r"(server\s*\{)", lambda m: m[0] + "\n" + block, original, count=1)


def prepare_site(source, destination, release):
    shutil.copytree(source, destination)
    prefix = f"/_rw10_ui/{release}/"
    for path in destination.rglob("*"):
        if not path.is_file() or path.suffix not in {".html", ".css", ".js"}:
            continue
        text = path.read_text()
        text = text.replace("http://192.168.100.50:8188", "/login")
        # Keep this bundle out of /assets/, which belongs to the live Uvicorn app.
        text = text.replace("./assets/", prefix + "assets/")
        text = re.sub(r"(?P<q>[\"'`])\./(?P<p>[A-Za-z0-9_-]+\.(?:html|css|js))",
                      lambda m: m["q"] + prefix + m["p"], text)
        if path.suffix == ".html":
            text = re.sub(r'\s+on[a-z]+="[^"]*"', "", text, flags=re.I)
            text = text.replace("https://upload.wikimedia.org/wikipedia/commons/3/3b/Lambang_Kabupaten_Bogor.svg",
                                prefix + "assets/kabupaten-bogor-fallback.svg")
            # CSP permits self scripts but not inline scripts; externalize the RT theme initializer.
            counter = [0]
            def externalize(match):
                counter[0] += 1
                filename = f"{path.stem}-inline-{counter[0]}.js"
                (path.parent / filename).write_text(match[1])
                return f'<script src="{prefix}{filename}"></script>'
            text = re.sub(r"<script>(.*?)</script>", externalize, text, flags=re.S)
        path.write_text(text)
    (destination / "config.js").write_text(
        "window.RW10_INTERNAL_URL = window.location.origin + '/login';\n")
    # An unrelated standalone CMS must not be assumed to contain this app's data.
    # The existing content-api URL is retained; its availability is reported separately.
    (destination / "nginx.conf").unlink(missing_ok=True)


def response(path):
    try:
        # Local readiness checks must never go through a runner's HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(BASE + path, timeout=15) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "")


NETWORK_ERRORS = (urllib.error.URLError, TimeoutError, ConnectionError)


def login_ready(attempts):
    for attempt in range(attempts):
        try:
            status = response("/login")[0]
            print("Login readiness HTTP:", status, flush=True)
            if status == 200:
                return True
        except NETWORK_ERRORS as exc:
            print("Login readiness:", type(exc).__name__, flush=True)
        if attempt + 1 < attempts:
            time.sleep(3)
    return False


def ensure_backend_ready():
    if login_ready(2):
        return
    info = container(APP)
    state = info.get("State", {})
    health = state.get("Health", {}).get("Status", "unknown")
    print("Existing backend health:", health, flush=True)
    if not state.get("Running") or health != "unhealthy":
        raise RuntimeError("Login is unavailable; backend is not eligible for automatic recovery")
    print("Restarting the unhealthy existing backend once; retaining its container and volumes.", flush=True)
    run("docker", "restart", "--time", "30", APP)
    if not login_ready(8):
        raise RuntimeError("Login remains unavailable after backend recovery; frontend not changed")


def diagnostics(repo):
    usage = shutil.disk_usage(repo)
    print("Host load (1/5/15 minutes):", os.getloadavg(), flush=True)
    print("Host disk free MiB:", usage.free // 1048576, flush=True)
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:", "SwapFree:")):
            print(line, flush=True)


def verify(release, before):
    status, body, _ = response("/")
    if status != 200 or f"/_rw10_ui/{release}/editorial-v6.css".encode() not in body:
        raise RuntimeError("Updated homepage is not served on port 8080")
    for name in ("editorial-v6.css", "assets/gapura-gg-kape.webp", "app.js", "config.js"):
        if response(f"/_rw10_ui/{release}/" + name)[0] != 200:
            raise RuntimeError("Missing new UI asset: " + name)
    for path, expected in before.items():
        actual = response(path)
        if actual[0] != expected[0]:
            raise RuntimeError("Existing route status changed: " + path)
        if path.startswith("/assets/") and actual[1] != expected[1]:
            raise RuntimeError("Existing app asset changed: " + path)
    if response("/login")[0] != 200:
        raise RuntimeError("Existing login is unavailable")


def activate(conf, updated, original, check):
    # In-place writes are required: replacing a bind-mounted file's inode leaves
    # the running container reading the old config.
    try:
        conf.write_text(updated)
        run("docker", "exec", WEB, "nginx", "-t")
        run("docker", "exec", WEB, "nginx", "-s", "reload")
        check()
    except BaseException:
        conf.write_text(original)
        run("docker", "exec", WEB, "nginx", "-t")
        run("docker", "exec", WEB, "nginx", "-s", "reload")
        raise


def main():
    if os.geteuid() != 0:
        raise RuntimeError("Run this deployment as root")
    repo = Path(__file__).resolve().parents[1]
    print("Starting existing-stack frontend deployment", flush=True)
    diagnostics(repo)
    source = repo / "website"
    if not (source / "editorial-v6.css").is_file():
        raise RuntimeError("The editorial website source is missing")
    web, app = container(WEB), container(APP)
    for info in (web, app):
        if not info["State"]["Running"]:
            raise RuntimeError("Both existing web/app containers must be running")
        labels = info.get("Config", {}).get("Labels", {})
        if labels.get("com.docker.compose.project.working_dir") != str(repo):
            raise RuntimeError("Container working directory differs from this checkout")
    frontend = mount(web, "/srv/frontend")
    conf = mount(web, "/etc/nginx/conf.d/default.conf")
    if frontend != repo / "frontend" or conf != repo / "nginx/default.conf":
        raise RuntimeError("Bind-mount paths differ from the inspected installation")
    with open("/run/lock/rw10plus-frontend-deploy.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ensure_backend_ready()
        original = conf.read_text()
        release = time.strftime("%Y%m%d-%H%M%S") + "-" + str(os.getpid())
        updated = configuration(original, release)
        before = {}
        for path in ("/login", "/api/health", "/assets/product.js", "/assets/product.css"):
            print("Checking existing route:", path, flush=True)
            try:
                before[path] = response(path)
            except NETWORK_ERRORS as exc:
                raise RuntimeError("Existing route unavailable before deployment: " + path) from exc
        if before["/login"][0] != 200:
            raise RuntimeError("Login failed before deployment; no files changed")
        backup = Path(tempfile.mkdtemp(prefix="rw10-ui-", dir="/var/backups"))
        (backup / "default.conf").write_text(original)
        (backup / "container-ids.json").write_text(json.dumps({"web": web["Id"], "app": app["Id"]}))
        with tarfile.open(backup / "frontend.tar.gz", "w:gz") as archive:
            for path in frontend.iterdir():
                if path.name != "_rw10_ui":
                    archive.add(path, arcname=path.name)
        # Parent is public web content; only bundled public files are copied here.
        releases = frontend / "_rw10_ui"
        releases.mkdir(exist_ok=True, mode=0o755)
        destination = releases / release
        prepare_site(source, destination, release)
        for path in [destination, *destination.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        print("Backup:", backup, flush=True)
        print("Updating the existing Nginx homepage; API/login/data remain on the existing app.", flush=True)
        def checks():
            last = None
            for _ in range(5):
                try:
                    verify(release, before)
                    return
                except (RuntimeError, *NETWORK_ERRORS) as exc:
                    last = exc
                    time.sleep(1)
            raise last
        activate(conf, updated, original, checks)
        try:
            cms = response("/content-api/api/public?kind=news&rt=ALL")
        except NETWORK_ERRORS:
            cms = (0, b"", "")
        if cms[0] != 200 or "application/json" not in cms[2]:
            print("NOTE: Public CMS is not integrated with the existing app; example content remains labelled.")
        print("OK: existing port 8080 serves the new homepage. Login and existing app assets verified.")
        print("Rollback: restore", backup / "default.conf", "in-place and run docker exec", WEB, "nginx -s reload")


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise InterruptedError("Deployment interrupted")
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)
    try:
        main()
    except Exception as exc:
        print("DEPLOY FAILED:", str(exc), file=sys.stderr)
        sys.exit(1)
