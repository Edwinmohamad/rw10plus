# RW10+ v8 — dark mode repair + Public Content CMS

## Added
- Contrast repair for dark mode on the public homepage and RT pages (`website/theme-fix.css`).
- CMS at `http://SERVER:8080/admin.html` to add/edit/remove/publish news, events, organization entries, aggregate stats, gallery images and UMKM.
- Manual JPG, PNG, or WebP upload (5 MB limit), files stored in `./cms-data/media` and database `./cms-data/cms.sqlite3`.
- Public homepage reads *published* CMS content only; until official content exists, relevant sections show empty states. CMS API failures keep previous sample content visible so availability problems are apparent.
- Admin table: number, selection checkbox, filter/search, edit, delete selected, publication toggle, and photo upload.

## Install
1. Back up the complete project, `data/`, `.env`, and any existing CMS data.
2. Extract the new project source without replacing your live `data/` directory.
3. Add `CMS_ADMIN_PASSWORD` (strong unique >=12 characters) to your existing `.env` file. See `.env.cms.example`. Without it Docker Compose intentionally refuses to start CMS.
4. `mkdir -p cms-data && docker compose up -d --build`
5. Open `/admin.html`, log in, upload photos, and create entries. Tick 'Publikasikan konten' to show entries on the website.
6. If deploying behind HTTPS, set `CMS_COOKIE_SECURE=true` and ensure the reverse proxy uses HTTPS.

## Scope and safeguards
- CMS is **public content only**. Do not upload residents' NIK, KK, addresses, or student ID documents here. There is no private resident database module in this release.
- This CMS currently has **one administrator password**, not individual RT-scoped administrative accounts. Do not share that credential with RT administrators. Full RT-scoped editing needs a subsequent integrated login/RBAC implementation.
- Published 'stats' items only support aggregate numeric values. Use titles containing `penduduk`, `kk`, or `umkm` for homepage statistic mapping.
- Existing RW10 internal app at 8188 and RT isolation code unchanged. Existing CCTV remains a simulation and WiFi student integration is not added.
- Change password after rollout; protect admin endpoints with HTTPS and ideally VPN or IP allowlisting. Back up `cms-data/` regularly.
- Assets uploaded in CMS are public when linked. Do not upload sensitive files.
- This patch has static and API checks, not a visual browser end-to-end certification.
