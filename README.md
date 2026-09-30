# 🐍 Nokia Snake — Gesture AI

A modern reimagining of the classic Nokia Snake game, controlled in real time with your **hand gestures** through a webcam. Built with Python, Pygame, OpenCV and MediaPipe.

> **Note:** This is a desktop Python application. The actual Pygame/OpenCV/MediaPipe game runs locally because Vercel does not execute the Python desktop application or provide direct webcam access to it. The repository also contains a static landing page (`web/`) that is deployed separately.

---

## ✨ Features

- **Gesture Control** — steer the snake with swipes, no keyboard required
- **Real-Time Hand Tracking** — 21 hand landmarks detected live with MediaPipe
- **Live Camera Feed** — mirrored selfie-style camera panel inside the game window
- **Turbo Mode** — pinch to temporarily boost the snake's speed
- **Classic Nokia Gameplay** — grid board, wall/self collision, food, levels
- **High Score System** — persistent high score saved to disk
- **Particle Effects** — burst animation when you eat food
- **Graceful Degradation** — camera or MediaPipe failures never break the game; keyboard always works
- **Performance Optimized** — camera capture + hand tracking run on a background thread, independent of the 60 FPS game loop

---

## 🎮 Gesture Controls

| Gesture | Action |
|---|---|
| Swipe **←** (move hand left) | Snake moves **LEFT** |
| Swipe **→** (move hand right) | Snake moves **RIGHT** |
| Swipe **↑** (move hand up) | Snake moves **UP** |
| Swipe **↓** (move hand down) | Snake moves **DOWN** |
| **Pinch** (thumb + index) | **Turbo** — faster while held |
| **Closed fist** | **Pause / resume** |
| **Open palm** | **Restart** (only when game over) |

Notes:

- The camera feed is **mirrored** (selfie view), and gesture interpretation stays intuitive — moving your hand to your right always moves the snake right.
- Illegal 180° turns are rejected (e.g. moving RIGHT, a LEFT swipe is ignored).
- Swipes use a cooldown/debounce so one gesture never triggers multiple turns.
- Turbo only applies while the pinch is held.

---

## ⌨️ Keyboard Controls

| Key | Action |
|---|---|
| `W A S D` / `Arrow keys` | Move |
| `Space` | Pause / resume |
| `R` | Restart |
| `Esc` | Quit |

Keyboard controls are always available as a fallback, even when the camera or hand tracking is unavailable.

---

## 🏗 Architecture

```
main.py                 Application entry point: window, main loop,
                        event handling, gesture → game input routing

core/
  game.py               Snake logic: movement, collision, food, levels,
                        speed/turbo, overlays, rendering
  highscore.py          Persistent high score (highscore.dat)
  particles.py          Particle explosion effects

ui/
  hud.py                Full HUD: header, camera panel, status panel,
                        gesture guide, footer
  components.py         Reusable rounded panel / progress bar widgets
  menu.py               Menu/title rendering

vision/
  hand_tracker.py       Webcam capture + MediaPipe hand tracking on a
                        background thread, swipe/pinch/fist/palm
                        detection with debounce

web/                    Static landing page (deployed on Vercel)
```

**Threading model:** the game loop runs at 60 FPS and never blocks. Camera capture, frame decoding and MediaPipe inference run in a worker thread that publishes the latest gesture result through a thread-safe reader (`HandTracker.get_result()`).

---

## 🛠 Technologies

| Technology | Role |
|---|---|
| **Python 3.11** | Runtime |
| **Pygame** | Game window, rendering, input |
| **OpenCV** | Webcam capture, image processing |
| **MediaPipe** | Real-time hand landmark detection |
| **NumPy** | Numerical operations on frames |

---

## 📦 Installation

Requirements: **Python 3.11** and a webcam.

```bash
git clone https://github.com/deepsh3969/Nokia_Snake-V4.git
cd Nokia_Snake-V4

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

python -m pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
python main.py
```

The window opens with the game board on the left and the live camera / gesture panel on the right. Show your hand to the camera to start controlling the snake — or use the keyboard.

---

## 📷 Camera Troubleshooting

| Symptom | What to try |
|---|---|
| Panel shows **"Camera unavailable"** | Close other apps using the camera (Zoom, Teams, OBS, Camera app) and restart the game |
| Panel shows **"No signal"** | Check the **physical privacy shutter** or the laptop's camera function key (on Lenovo: `Fn` + camera key), then restart the game |
| Wrong camera is picked | The app auto-probes camera indexes `0`, `1`, `2` — plug/unplug external webcams and relaunch |
| Black image in the Windows Camera app | The issue is at the OS/hardware level, not in this project — update the camera driver in Device Manager |
| Slow, choppy feed | Close GPU-heavy applications; the app processes frames at 640×480 and tracks at up to 25 Hz |

If the camera cannot be used at all, the game still runs fully with keyboard controls.

---

## 🖐 MediaPipe Troubleshooting

| Symptom | What to try |
|---|---|
| **"Hand tracking unavailable"** | Reinstall: `python -m pip install --force-reinstall mediapipe==0.10.21` |
| Import error on `mediapipe` | Confirm Python 3.11: `python --version` (MediaPipe wheels must match your Python version) |
| Tracking is jittery | Improve lighting, keep your hand 30–60 cm from the camera, use a plain background |
| False swipes | Increase distance from the camera; swipe deliberately — a 0.45 s cooldown is applied |

Keyboard controls remain active whenever hand tracking is unavailable.

---

## 📂 Project Structure

```
Nokia_Snake-V4/
│
├── main.py
├── README.md
├── requirements.txt
├── .gitignore
├── vercel.json
│
├── assets/
│   └── sounds/
│
├── core/
│   ├── game.py
│   ├── highscore.py
│   ├── particles.py
│   └── __init__.py
│
├── ui/
│   ├── components.py
│   ├── hud.py
│   ├── menu.py
│   └── __init__.py
│
├── vision/
│   ├── hand_tracker.py
│   └── __init__.py
│
└── web/                  # Static landing page (Vercel)
    ├── index.html
    ├── style.css
    └── script.js
```

---

## ⚡ Performance Notes

- Camera capture and MediaPipe inference run on a **dedicated background thread** — the 60 FPS game loop never waits on the webcam.
- Frames are captured at **640×480** and downscaled before being handed to Pygame.
- Hand tracking runs at a capped **~25 Hz**, which is more than sufficient for gesture input.
- Only one hand is tracked (`max_num_hands=1`) with the lightweight model (`model_complexity=0`).
- The camera panel reports its real FPS next to the game FPS in the header.

---

## 🔮 Future Improvements

- Multiple simultaneous hand gestures
- Configurable sensitivity / cooldown settings from an in-game options menu
- Sound effects and music (`assets/sounds/`)
- Online leaderboard
- Mobile/web port of the game itself (separate from this desktop build)
- Alternate control schemes (head tracking, face direction)

---

## 📸 Screenshots

> Screenshots will be added after a run on a machine with a working webcam.

- **Gameplay screenshot** — *coming soon*
- **Camera/gesture screenshot** — *coming soon*
- **Game-over screenshot** — *coming soon*

---

## 🌐 Deployment

Two independent parts:

1. **Desktop game** — runs locally with `python main.py`. It is *not* deployed to Vercel (Vercel cannot run Pygame or access a webcam).
2. **Landing page** (`web/`) — static HTML/CSS/JS, deployed on Vercel with `web/` as the root directory.

---

## 📄 License

MIT License — free to use, modify and distribute.

---

## 👤 Author

**deepsh3969** — [github.com/deepsh3969](https://github.com/deepsh3969)

Built with Python + Computer Vision.
