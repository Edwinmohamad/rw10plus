# RW10+ v6 — Public Widgets Patch + Full Source

## Scope delivered
- All v5 source retained (internal app, RT-isolation backend, compose, photos, INKAMNET logo).
- New public widgets: 4 RT selector (keyboard-operable), verified-statistics placeholder and animated count of 4 RT, public organizational overview, photo lightbox, native modal close, responsive UI.
- NO invented personal data or fake statistics: residents, households and business figures remain unpublished until official data is connected.
- Existing RT04 photo and INKAMNET/Edwin credits are retained.

## Not delivered / not production-ready
- Resident/household CRUD, import/export and bulk data actions; admin configurable widgets; content management backend; CCTV go2rtc integration; live WiFi/MikroTik integration.
- Real RT-level statistics and official organizational names.
- Visual verification in real Chrome on desktop/mobile and production integration testing are still necessary.

## Deploy
1. Back up `data/` and the existing source and `.env` files.
2. On a staging server, extract source, preserve existing production settings, compare changes.
3. Run `python3 tests/ui_contract_test.py && python3 tests/smoke_test.py && python3 tests/rt_isolation_test.py` (if present).
4. Run `docker compose up -d --build` and inspect ports 8080/8188.
5. Update `website/config.js` with the correct HTTPS URL of the internal portal.
6. Review keyboard navigation, photo lightbox and RT selector on desktop/mobile.

**Important:** This is a verified incremental update, not completion of all proposed platform modules. In particular, do not import real citizen IDs until data security, roles and backup processes are implemented and tested.
