# Release checklist

Use this checklist before creating a GitHub Release.

## 1) Quality gate

- [ ] Run local checks: `ruff check .`, `ruff format --check .`, `mypy src`, `pytest`
- [ ] Confirm CI is green on `main`
- [ ] Review open issues/PRs for release blockers

## 2) Versioning

- [ ] Bump `version` in `pyproject.toml`
- [ ] Update changelog notes (`RELEASE_vX.Y.Z.md`)
- [ ] Verify CLI examples still work

## 3) Docs and artifacts

- [ ] Update README if flags/commands changed
- [ ] Update or add screenshots in `docs/screenshots/`
- [ ] Ensure security note stays present (never commit `.env`)

## 4) Tag and publish

- [ ] Commit release changes
- [ ] Create annotated tag: `git tag -a vX.Y.Z -m "ISS-Horizon vX.Y.Z"`
- [ ] Push branch + tags: `git push origin main --tags`
- [ ] Create GitHub Release from tag `vX.Y.Z`
- [ ] Paste notes from `.github/RELEASE_TEMPLATE.md`

## 5) Post-release verification

- [ ] Confirm release appears in GitHub Releases
- [ ] Confirm README release badge shows new tag
- [ ] Smoke test install flow (`pipx install iss-horizon` or local editable install)
- [ ] Announce/update project channels
