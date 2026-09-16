#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
css = (ROOT / "static" / "styles.css").read_text(encoding="utf-8")

all_ids = re.findall(r'\bid="([^"]+)"', html)
assert len(all_ids) == len(set(all_ids)), "ID HTML duplikat"
ids = set(all_ids)
views = set(re.findall(r'id="view-([^"]+)"', html))
targets = set(re.findall(r'data-view="([^"]+)"', html))
required = {"home", "services", "sos", "complaints", "dues", "letters", "guest", "operations", "cctv", "activities", "news", "organization", "market", "voting", "contacts", "notifications", "profile"}
assert required <= views, f"Halaman belum lengkap: {sorted(required - views)}"
assert targets <= views, f"Navigasi tanpa halaman: {sorted(targets - views)}"

selectors = set(re.findall(r"\$\('#([A-Za-z][\w:-]*)'\)", js))
assert selectors <= ids, f"Selector JavaScript tanpa elemen: {sorted(selectors - ids)}"
for marker in ("holdTimer", "cancel_deadline", "accessibility_mode", "letter-decision", "guest-passes/scan", "patrol/check-in"):
    assert marker in js, f"Logika UI hilang: {marker}"
for marker in ('href="/styles.css?v=0.3.0"', 'src="/app.js?v=0.3.0"', 'id="elderly-toggle"', 'data-theme'):
    assert marker in html or marker in css, f"Kontrak tampilan hilang: {marker}"
assert css.count("{") == css.count("}"), "Kurung CSS tidak seimbang"
assert "html.elderly" in css and 'html[data-theme="dark"]' in css

print(f"UI CONTRACT OK: {len(views)} halaman, {len(targets)} target, Light/Dark OLED + Mode Lansia")
