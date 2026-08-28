# Contributing

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Pull requests

1. Fork and branch from `main`
2. Keep changes focused
3. Do not commit `.venv/`, `build/`, or `release/`
4. Open a PR with a short description of what changed and why

## Releases

Maintainers cut a version by tagging:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions builds the DMG / Windows zip / APK / Linux tarball and attaches them to the GitHub Release.
