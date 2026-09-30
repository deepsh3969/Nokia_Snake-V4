# 🐍 Nokia Snake — Gesture AI

A modern reimagining of the classic Nokia Snake game, controlled in real time with your **hand gestures** through a webcam — available in two editions:

| | Desktop edition | Browser edition |
|---|---|---|
| **Stack** | Python · Pygame · OpenCV · MediaPipe | HTML · CSS · JavaScript · Canvas · MediaPipe Tasks Vision |
| **Runs in** | Your desktop (local window) | Any modern browser (deployed on Vercel) |
| **Hand tracking** | MediaPipe Python | MediaPipe Tasks Vision (WASM, in-browser) |
| **Webcam** | `cv2.VideoCapture` | `navigator.mediaDevices.getUserMedia()` |
| **No Python needed?** | — | ✅ Fully client-side |

> **Browser edition live:** https://nokia-snake-gesture-ai.vercel.app
> The game itself loads at that URL — play immediately with the keyboard, then enable the camera for gesture control.

---

## 1. Desktop Python version

**Requires:** Python 3.11, a webcam.

```bash
git clone https://github.com/deepsh3969/Nokia_Snake-V4.git
cd Nokia-Snake-V4

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

python -m pip install -r requirements.txt

python main.py
```

- Camera capture and hand tracking run on a **background thread** — the 60 FPS game loop never waits for the webcam.
- If the camera or MediaPipe fails to start, the game switches to **keyboard control automatically** and shows a clear status in the HUD.

## 2. Browser / Vercel version

Lives in [`web/`](web/). Pure static site — **no Python, no Pygame, no OpenCV**:

- `web/index.html` — page structure
- `web/style.css` — light, Nokia-inspired responsive UI
- `web/script.js` — Canvas snake game + webcam gesture engine (MediaPipe Tasks Vision loaded on demand from CDN)

### Run the web version locally

```bash
python -m http.server 8000 --directory web
```

Open **http://localhost:8000** — the Snake game loads directly.

> Webcam access works on `localhost` (secure context) and on HTTPS in production. Vercel serves HTTPS automatically.

## 3. Keyboard controls (both editions)

| Key | Action |
|---|---|
| `↑` `↓` `←` `→` | Steer |
| `W` `A` `S` `D` | Steer |
| `SPACE` | Pause / resume |
| `ENTER` | Start / restart |

180° reversals (e.g. moving right → immediately left) are rejected, and quick double-turns are queued safely.

## 4. Gesture controls (camera)

Click **ENABLE CAMERA**, allow webcam permission, then:

| Gesture | Action |
|---|---|
| 👆 Swipe up / down / left / right | Steer the snake |
| 🖐 Open palm (hold ~0.2 s) | Pause / resume |
| 🤏 Pinch (hold) | Turbo — temporarily doubles the speed |

- The camera view is **mirrored** (selfie style); gesture directions follow your mirrored movement, so swiping your hand right moves the snake right.
- **Debounce:** one hand movement triggers exactly one turn (cooldown ≈ 450 ms), and reversal of the current direction is blocked.
- Landmarks are drawn live on an overlay canvas above the video.

## 5. Camera permissions

- **Desktop:** allow camera access for your OS / terminal. Windows: *Settings → Privacy → Camera*.
- **Browser:** the site must be served over **HTTPS** (Vercel provides this) or `localhost`. Click **ENABLE CAMERA** and accept the permission prompt.
- If permission is denied or MediaPipe cannot load, the page shows
  **"Camera unavailable — Keyboard controls enabled"**
  and the game keeps working with the keyboard. Nothing crashes.

## 6. Local web testing

```bash
# serve the site
python -m http.server 8000 --directory web
# serve the repo root (needed for the automated test page)
python -m http.server 8001 --directory .
```

Automated browser tests (headless Chrome, fake webcam):

```bash
node tests/run_cdp.mjs
```

This verifies page/CSS/JS loading, keyboard input, movement, 180° rejection, pause/resume, collision, restart, localStorage high score, camera startup, MediaPipe hand-landmarker initialisation, camera-denial fallback, and that the console stays error-free. The pure-logic suite in `tests/web_selftest.html` covers the swipe detector, pinch/palm pose helpers and the full game rules.

## 7. Vercel deployment

Two supported setups — both serve the game at `/` with **no 404s**:

**A. Root directory = `web`** (recommended for Git-integrated projects)

- Framework Preset: `Other`
- Build Command: *(empty)*
- Output Directory: `.`
- Root Directory: `web`

`web/vercel.json` is already present.

**B. Root directory = repository root**

A root-level `vercel.json` rewrites `/`, `/style.css` and `/script.js` into `web/`, so even a root deployment serves the game.

CLI deployment (what this repo uses):

```bash
cd web
vercel --prod
```

## 8. GitHub deployment

```bash
git status
git remote -v                       # verify origin first
git add .
git commit -m "Create browser-based Nokia Snake Gesture AI"
git push origin main
```

## 9. Project structure

```
Nokia-Snake-V4/
├── main.py                 # desktop entry point
├── requirements.txt
├── README.md
├── core/                   # snake logic, food, collisions, particles, highscore
├── ui/                     # Pygame HUD, panels, menu
├── vision/                 # OpenCV capture + MediaPipe hand tracking (threaded)
├── assets/
├── web/
│   ├── index.html          # browser edition page
│   ├── style.css           # responsive light UI
│   ├── script.js           # Canvas game + gesture engine
│   └── vercel.json         # static config (root-directory = web)
├── tests/
│   ├── web_selftest.html   # pure-logic test page
│   └── run_cdp.mjs         # headless-Chrome end-to-end runner
├── vercel.json             # root-deployment rewrites -> web/
└── .gitignore
```

---

## Troubleshooting

- **Camera unavailable (desktop):** close other apps using the webcam, check the privacy shutter / `Fn` camera key, and Windows camera permissions. The game continues with the keyboard.
- **Camera unavailable (browser):** confirm the URL is HTTPS or `localhost`, check the browser's camera permission (lock icon in the address bar), and close other apps holding the webcam.
- **Hand tracking inactive:** ensure your hand is well lit and fully inside the camera panel; landmark overlay appears when a hand is found.

## License

MIT — free to use, modify and share.
