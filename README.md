# Spectrum

**A cross-platform Pomodoro timer with the look of a modern AI client.**

Dark canvas, glass cards, a GitHub-style contribution heatmap, and a rainbow edge animation when a full focus + break cycle completes.

[![Release](https://img.shields.io/github/v/release/stardryjun/Spectrum?style=flat-square)](https://github.com/stardryjun/Spectrum/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-22d3ee?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-a78bfa?style=flat-square)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/stardryjun/Spectrum/release.yml?style=flat-square)](https://github.com/stardryjun/Spectrum/actions)

---

## Download (one-click install)

Grab the installer for your OS from the **[latest release](https://github.com/stardryjun/Spectrum/releases/latest)**. No Python required.

| Platform | File | How to install |
| --- | --- | --- |
| **macOS** (Apple Silicon & Intel) | `Spectrum-x.y.z-macos.dmg` | Open the DMG → drag **Spectrum** onto **Applications** → launch from Launchpad |
| **Windows** 10/11 (x64) | `Spectrum-x.y.z-windows.zip` | Unzip → double-click **Spectrum.exe** |
| **Android** 8+ | `Spectrum-x.y.z-android.apk` | Open the APK on the phone → Allow unknown sources → Install |
| **Linux** | `Spectrum-x.y.z-linux.tar.gz` | Extract and run the `spectrum` binary |

> Installers are **not** committed to git. Push a version tag and GitHub Actions builds them:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The Release workflow then attaches DMG / Windows zip / APK / Linux tarball to that GitHub Release.

### macOS Gatekeeper

Unsigned downloads from GitHub are blocked the first time. Right-click **Spectrum** → **Open** → **Open**. Or:

```bash
xattr -cr /Applications/Spectrum.app
```

### Android unknown sources

Settings → Security → allow install from the browser / Files app that downloaded the APK.

---

## Features

- Classic **25 + 5** and Deep Focus **50 + 10**, plus your own modes (saved in SQLite)
- Start / pause / reset — focus and break use distinct cyan / purple chrome
- A session is stored only when a **focus** block finishes on its own
- Rainbow frame plays only when a full **focus + break** cycle finishes (never on pause/reset)
- History: today / week / month / total hours, 53-week heatmap, day-grouped log
- Data lives in `~/.spectrum/spectrum.db` so reinstalls keep your history

---

## Run from source

```bash
git clone https://github.com/stardryjun/Spectrum.git
cd Spectrum
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Hot reload while hacking on the UI:

```bash
flet run main.py
```

Requires **Python 3.10+**.

---

## Project layout

```
.
├── main.py                 # app entry, theme, rainbow overlay
├── timer.py                # pomodoro state machine
├── database.py             # SQLite modes + sessions
├── theme.py                # color tokens
├── ui/home.py              # timer screen
├── ui/history.py           # stats + heatmap
├── assets/icon.png         # launcher icon (all platforms)
├── scripts/
│   ├── make_icon.py
│   ├── make_dmg.sh         # .app → drag-to-Applications DMG
│   └── build_local.sh      # local macOS DMG + APK
├── .github/workflows/release.yml
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

---

## Publish to GitHub

1. Create an empty public repo named `Spectrum` on GitHub.
2. From this folder:

```bash
git init
git add .
git commit -m "Initial release of Spectrum"
git branch -M main
git remote add origin git@github.com:YOUR_NAME/Spectrum.git
git push -u origin main
git tag v1.0.0
git push origin v1.0.0
```

3. Wait for the **Release** Action (macOS + Windows + Ubuntu runners). When it finishes, open **Releases** — the four installers are attached.

Replace `YOUR_USER` (and the badge URLs in this README) with your GitHub username. Settings → Actions → General → Workflow permissions must allow **Read and write**.

## Build installers yourself

GitHub Actions is the supported path. Cross-compilation is **not** possible: Windows EXE only builds on Windows, DMG only on macOS, APK on any OS with JDK 17.

Locally (needs unblocked access to GitHub + Flutter storage):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash scripts/build_local.sh          # macOS DMG + Android APK → release/
```

| Target | Command | Host OS | Result |
| --- | --- | --- | --- |
| macOS | `flet build macos` then `scripts/make_dmg.sh` | macOS | `.dmg` |
| Windows | `flet build windows` then `scripts/make_windows_zip.sh` | Windows | zip with `Spectrum.exe` |
| Android | `flet build apk` | macOS / Linux / Windows | `.apk` |
| Linux | `flet build linux` | Linux | binary folder |
| iOS | `flet build ipa` | macOS + Apple Developer account | `.ipa` (not in CI) |

---

## License

[MIT](LICENSE)
