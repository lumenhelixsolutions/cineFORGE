# Public Beta Release Runbook (M7)

## Preconditions

- [ ] `pytest tests/unit -q` green locally
- [ ] `cd ui && npm run build` succeeds
- [ ] Version bumped in `src-tauri/tauri.conf.json`, `pyproject.toml`, `ui/package.json`
- [ ] `CHANGELOG.md` updated
- [ ] Working tree committed and pushed to `origin/master`

## Tag and release

```powershell
cd D:\projects\cineforge
git add -A
git commit -m "chore(release): prepare v0.2.0 public beta"
git push origin master
git tag v0.2.0
git push origin v0.2.0
```

GitHub Actions `release.yml` triggers on `v*` tags and uploads **draft prerelease** assets (MSI, DMG, AppImage).

1. Open https://github.com/lumenhelixlab/cineFORGE/releases
2. Edit the draft release — paste body from `docs/RELEASE_NOTES_v0.2.0.md`
3. Uncheck "pre-release" when ready for wide beta, or leave checked for early testers
4. Publish

## Landing page (GitHub Pages)

Workflow: `.github/workflows/pages.yml` deploys `landing/` on push to `master`.

- Custom domain: `cineforge.app` (see `landing/CNAME`)
- Configure DNS: CNAME `cineforge.app` → `lumenhelixlab.github.io` or Pages URL
- Enable Pages in repo Settings → Pages → Source: GitHub Actions

## Signing (Milestone 11 — not blocking unsigned beta)

| Secret | Platform |
|--------|----------|
| `WINDOWS_CERTIFICATE` + `WINDOWS_CERTIFICATE_PASSWORD` | Authenticode MSI |
| `APPLE_CERTIFICATE` + `APPLE_CERTIFICATE_PASSWORD` + `APPLE_ID` + `APPLE_PASSWORD` + `APPLE_TEAM_ID` | macOS notarization |

When secrets are present, `release.yml` passes them to `tauri-apps/tauri-action`. Until then, `signingIdentity: "-"` in `tauri.conf.json` produces unsigned bundles.

## Post-release verification

- [ ] Download MSI/DMG/AppImage from Releases
- [ ] Install on clean VM (expect publisher warning if unsigned)
- [ ] Create project → ingest lookBOOK JSON → render one cloud shot with Veo or Kling
- [ ] Landing page loads at https://cineforge.app (after DNS + Pages deploy)