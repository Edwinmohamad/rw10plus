# RW10+ v9.2 — RUNNING HOTFIX

This hotfix intentionally makes the CMS boot without GitHub Secrets or a local `.env`.

Temporary CMS login password:

```text
RW10Admin2026!
```

The password is intentionally a bootstrap default to get CI/deployment running. Change it after the first successful deployment.

## Fixed
- `compose.yaml` no longer uses `${CMS_ADMIN_PASSWORD:? ...}` or any required-variable interpolation.
- Deploy workflow exports a bootstrap CMS password before validation/deploy.
- `sudo` preserves the CMS variables into `install.sh`.
- `install.sh` also has local bootstrap fallbacks.
- CMS itself has the same fallback when started outside Compose.
- `cms-data` is created and owned by UID/GID 10001 so the non-root CMS container can write SQLite/media.

## First deployment
Push the patch and re-run **Deploy RW10+ to CT102**. No GitHub Secret is required for this first bootstrap deployment.
