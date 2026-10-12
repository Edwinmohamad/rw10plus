# RW10+ v9.2 RUNNING

Hotfix target: make first CMS deployment succeed without a pre-existing `.env` or GitHub Secret.

Temporary CMS password:

    RW10Admin2026!

Changes:
- compose.yaml uses a literal bootstrap CMS password; no required env interpolation.
- deploy workflow provides the same bootstrap environment.
- install.sh preserves/exports bootstrap values and creates writable cms-data.
- CMS Docker image uses fixed UID/GID 10001.
- CMS server also has a standalone bootstrap password fallback.
- Android API 26/27 navigation-bar lint split remains present.

Validation performed in build workspace:
- Python compile: PASS
- Workflow YAML parse: PASS
- Compose YAML static parse: PASS
- CMS startup/login without .env: PASS
- UI contract: PASS
- RT isolation: PASS
- Backend smoke test: PASS
- Android styles API 26/27 structural check: PASS

Docker itself is not installed in the build workspace, so the exact `docker compose config` command could not be executed here. The interpolation that caused GitHub Actions to fail has been removed entirely from active files.
