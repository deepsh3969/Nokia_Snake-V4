/* Automated browser test for Nokia Snake web version.
   Drives headless Chrome (fake webcam) over the DevTools protocol.
   Usage: node tests/run_cdp.mjs
   Env: BASE (default http://localhost:8000), CHROME, PORT */
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";

const CHROME =
  process.env.CHROME ||
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = Number(process.env.PORT || 9444);
const BASE = process.env.BASE || "http://localhost:8000";
const GAME_URL = BASE + "/";
const SELFTEST_URL =
  (process.env.BASE2 || "http://localhost:8001") + "/tests/web_selftest.html";
const OUT_DIR = new URL("./artifacts/", import.meta.url).pathname.replace(/^\/(\w):/, "$1:");

const results = [];
function pass(name, extra = "") {
  results.push("PASS " + name + (extra ? " :: " + extra : ""));
}
function fail(name, extra = "") {
  results.push("FAIL " + name + (extra ? " :: " + extra : ""));
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------------- CDP client ---------------- */
class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.handlers = new Map();
    ws.addEventListener("message", (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id !== undefined && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id);
        this.pending.delete(m.id);
        if (m.error) reject(new Error(m.error.message));
        else resolve(m.result);
      } else if (m.method) {
        (this.handlers.get(m.method) || []).forEach((f) => f(m.params));
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
  on(method, fn) {
    if (!this.handlers.has(method)) this.handlers.set(method, []);
    this.handlers.get(method).push(fn);
  }
  async evaluate(expression) {
    const r = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (r.exceptionDetails) {
      throw new Error(
        "eval exception: " +
          (r.exceptionDetails.exception?.description ||
            r.exceptionDetails.text)
      );
    }
    return r.result.value;
  }
}

/* ---------------- helpers ---------------- */
async function waitFor(cdp, expr, timeoutMs, label) {
  const t0 = Date.now();
  let last;
  while (Date.now() - t0 < timeoutMs) {
    try {
      last = await cdp.evaluate(expr);
      if (last) return last;
    } catch (e) { /* keep polling */ }
    await sleep(300);
  }
  throw new Error("timeout waiting for " + label + " (last=" + JSON.stringify(last) + ")");
}

async function key(cdp, keyName, code, vk) {
  for (const type of ["keyDown", "keyUp"]) {
    await cdp.send("Input.dispatchKeyEvent", {
      type,
      key: keyName,
      code,
      windowsVirtualKeyCode: vk,
      nativeVirtualKeyCode: vk,
      ...(keyName === " " ? { text: " " } : keyName === "Enter" ? { text: "\r" } : {}),
    });
  }
}

async function main() {
  /* ---- 0. local HTTP status checks ---- */
  for (const path of ["/", "/style.css", "/script.js"]) {
    try {
      const r = await fetch(BASE + path);
      const body = await r.text();
      if (r.status === 200 && body.length > 100)
        pass("HTTP 200 " + path, r.headers.get("content-type") + " " + body.length + "B");
      else fail("HTTP 200 " + path, "status=" + r.status + " len=" + body.length);
    } catch (e) {
      fail("HTTP 200 " + path, e.message);
    }
  }

  /* ---- 1. launch chrome ---- */
  const profile = process.env.TEMP + "\\nsv4-cdp-profile";
  const chrome = spawn(
    CHROME,
    [
      "--headless=new",
      "--disable-gpu",
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${profile}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--autoplay-policy=no-user-gesture-required",
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      "--window-size=1440,1100",
      "--hide-scrollbars",
      "about:blank",
    ],
    { stdio: "ignore" }
  );

  let ws;
  try {
    let list;
    for (let i = 0; i < 40; i++) {
      try {
        const r = await fetch(`http://127.0.0.1:${PORT}/json`);
        list = await r.json();
        if (list.length) break;
      } catch (e) { /* retry */ }
      await sleep(250);
    }
    const page = (list || []).find((t) => t.type === "page");
    if (!page) throw new Error("no page target");

    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => {
      ws.addEventListener("open", res, { once: true });
      ws.addEventListener("error", rej, { once: true });
    });
    const cdp = new CDP(ws);

    const consoleErrors = [];
    cdp.on("Runtime.exceptionThrown", (p) =>
      consoleErrors.push(p.exceptionDetails?.exception?.description || "exception")
    );
    cdp.on("Log.entryAdded", (p) => {
      if (p.entry.level === "error") consoleErrors.push(p.entry.text + " " + (p.entry.url || ""));
    });
    cdp.on("Runtime.consoleAPICalled", (p) => {
      if (p.type === "error")
        consoleErrors.push(p.args.map((a) => a.value || a.description).join(" "));
    });

    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Log.enable");

    /* ---- 2. load game page ---- */
    const loadPromise = new Promise((res) => cdp.on("Page.loadEventFired", res));
    await cdp.send("Page.navigate", { url: GAME_URL });
    await Promise.race([loadPromise, sleep(15000)]);
    await sleep(600);

    const assetsOk = await cdp.evaluate(`(() => {
      const css = document.styleSheets.length > 0;
      let rules = 0;
      try { rules = document.styleSheets[0].cssRules.length; } catch(e) {}
      const bodyFont = getComputedStyle(document.body).fontFamily || "";
      const canvas = document.getElementById('gameCanvas');
      return {
        css, rules, bodyFont: bodyFont.slice(0, 30),
        hasCanvas: !!canvas,
        hasNSG: typeof window.NSG === 'object',
        title: document.title
      };
    })()`);
    assetsOk.css && assetsOk.rules > 10 && assetsOk.hasCanvas && assetsOk.hasNSG
      ? pass("page loads: CSS + JS + canvas", JSON.stringify(assetsOk))
      : fail("page loads: CSS + JS + canvas", JSON.stringify(assetsOk));

    /* ---- 3. keyboard: start ---- */
    const st0 = await cdp.evaluate("window.__ns.game.state");
    st0 === "READY" ? pass("initial state READY") : fail("initial state READY", st0);

    await key(cdp, "Enter", "Enter", 13);
    await sleep(400);
    const st1 = await cdp.evaluate("window.__ns.game.state");
    st1 === "PLAYING" ? pass("ENTER starts game") : fail("ENTER starts game", st1);

    /* ---- 4. snake actually moves ---- */
    const headBefore = await cdp.evaluate("JSON.stringify(window.__ns.game.snake[0])");
    await sleep(900);
    const moved = await cdp.evaluate(
      `JSON.stringify(window.__ns.game.snake[0]) !== ${JSON.stringify(headBefore)}`
    );
    moved ? pass("snake moves with game loop", headBefore + " -> moved") : fail("snake moves", headBefore);

    /* ---- 5. direction via ArrowDown ---- */
    await key(cdp, "ArrowDown", "ArrowDown", 40);
    await sleep(500);
    const dir = await cdp.evaluate("window.__ns.game.dir.name");
    dir === "DOWN" ? pass("ArrowDown steers snake DOWN") : fail("ArrowDown steers", dir);

    /* ---- 6. illegal 180 rejected live ---- */
    const rev = await cdp.evaluate("window.__ns.game.setDirection('UP')");
    rev === false ? pass("live 180° reversal rejected") : fail("live 180° rejected", String(rev));

    /* ---- 7. pause / resume ---- */
    await key(cdp, " ", "Space", 32);
    await sleep(250);
    const paused = await cdp.evaluate("window.__ns.game.state");
    await key(cdp, " ", "Space", 32);
    await sleep(250);
    const resumed = await cdp.evaluate("window.__ns.game.state");
    paused === "PAUSED" && resumed === "PLAYING"
      ? pass("SPACE pauses and resumes")
      : fail("SPACE pauses and resumes", paused + "/" + resumed);

    /* ---- 8. wall collision -> game over + overlay ---- */
    const overState = await cdp.evaluate(`(() => {
      const g = window.__ns.game;
      g.snake[0] = { x: 23, y: 12 };
      g.dir = window.NSG.DIRS.RIGHT;
      g._step();
      return g.state;
    })()`);
    await sleep(300);
    const overlay = await cdp.evaluate(`(() => ({
      hidden: document.getElementById('gameOverlay').dataset.hidden,
      btn: document.getElementById('overlayBtn').textContent,
      status: document.getElementById('gameStatus').textContent
    }))()`);
    overState === "GAME OVER" && overlay.hidden === "false" && overlay.btn === "PLAY AGAIN"
      ? pass("wall collision -> GAME OVER + overlay", JSON.stringify(overlay))
      : fail("wall collision -> GAME OVER + overlay", overState + " " + JSON.stringify(overlay));

    /* ---- 9. ENTER restarts ---- */
    await key(cdp, "Enter", "Enter", 13);
    await sleep(350);
    const after = await cdp.evaluate(
      "JSON.stringify({s: window.__ns.game.state, score: window.__ns.game.score, len: window.__ns.game.snake.length})"
    );
    const parsed = JSON.parse(after);
    parsed.s === "PLAYING" && parsed.score === 0 && parsed.len === 3
      ? pass("ENTER restarts clean", after)
      : fail("ENTER restarts clean", after);

    /* ---- 10. high score in localStorage ---- */
    const hi = await cdp.evaluate(`(() => {
      window.__ns.game.score = 50;
      window.__ns.game._gameOver();
      return {
        stored: parseInt(localStorage.getItem('nokiaSnakeHighScore') || '0', 10),
        shown: document.getElementById('highValue').textContent
      };
    })()`);
    hi.stored >= 50
      ? pass("high score persisted", JSON.stringify(hi))
      : fail("high score persisted", JSON.stringify(hi));

    // restart again to keep playing state tidy
    await key(cdp, "Enter", "Enter", 13);
    await sleep(250);

    /* ---- 11. camera + MediaPipe with fake webcam ---- */
    await cdp.evaluate("document.getElementById('enableCamBtn2').click()");
    let camInfo = {};
    try {
      await waitFor(
        cdp,
        "window.__ns.gesture && window.__ns.gesture.landmarker ? true : false",
        45000,
        "MediaPipe hand landmarker ready"
      );
      await waitFor(
        cdp,
        "document.getElementById('camVideo').readyState >= 2 ? true : false",
        10000,
        "video frames flowing"
      );
      await waitFor(
        cdp,
        "window.__ns.gesture.camFps > 0 ? true : false",
        8000,
        "detection loop running (camFps > 0)"
      );
      camInfo = await cdp.evaluate(`(() => ({
        badge: document.getElementById('camBadge').textContent,
        track: document.getElementById('trackStatus').textContent,
        gesture: document.getElementById('gestureStatus').textContent,
        camFps: window.__ns.gesture.camFps,
        running: window.__ns.gesture.running,
        landmarker: !!window.__ns.gesture.landmarker,
        videoW: document.getElementById('camVideo').videoWidth
      }))()`);
      camInfo.badge === "CONNECTED" && camInfo.running && camInfo.landmarker &&
      camInfo.camFps > 0 && camInfo.track === "INACTIVE"
        ? pass("camera + MediaPipe active", JSON.stringify(camInfo))
        : fail("camera + MediaPipe active", JSON.stringify(camInfo));
    } catch (e) {
      fail("camera + MediaPipe active", e.message);
    }

    /* ---- 12. screenshots ---- */
    mkdirSync(OUT_DIR, { recursive: true });
    const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
    writeFileSync(OUT_DIR + "game.png", Buffer.from(shot.data, "base64"));
    pass("screenshot saved", "game.png");

    /* ---- 13. console must be error-free ---- */
    const realErrors = consoleErrors.filter((e) => !/favicon/i.test(e));
    realErrors.length === 0
      ? pass("no console errors")
      : fail("no console errors", realErrors.join(" | "));

    /* ---- 14. self-test page ---- */
    await cdp.send("Page.navigate", { url: SELFTEST_URL });
    await sleep(1200);
    let selfResults = [];
    try {
      await waitFor(cdp, "window.__done === true ? true : false", 20000, "selftest completion");
      selfResults = await cdp.evaluate("window.__results");
    } catch (e) {
      fail("selftest page completes", e.message);
      try { selfResults = await cdp.evaluate("window.__results || []"); } catch (e2) { selfResults = []; }
    }
    selfResults.forEach((r) => results.push(r));
    const selfFails = selfResults.filter((r) => r.startsWith("FAIL")).length;
    const selfPasses = selfResults.filter((r) => r.startsWith("PASS")).length;
    (selfFails === 0 && selfPasses >= 15
      ? pass
      : fail)("selftest suite", selfPasses + " passed, " + selfFails + " failed");
  } finally {
    try { if (ws) ws.close(); } catch (e) {}
    try { chrome.kill(); } catch (e) {}
  }

  /* ---- report ---- */
  results.forEach((r) => console.log(r));
  const fails = results.filter((r) => r.startsWith("FAIL"));
  console.log("\n==== " + (results.length - fails.length) + "/" + results.length + " PASSED ====");
  process.exit(fails.length ? 1 : 0);
}

main().catch((e) => {
  console.error("RUNNER ERROR:", e);
  console.log(results.join("\n"));
  process.exit(2);
});
