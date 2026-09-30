/* =====================================================
   Nokia Snake — Gesture AI · browser edition
   Pure client-side: HTML Canvas game + webcam gestures
   via MediaPipe Tasks Vision (loaded on demand from CDN)
   ===================================================== */
(function () {
  "use strict";

  /* -------------------------------------------------
     Constants
  ------------------------------------------------- */

  var MP_VERSION = "0.10.14";
  var MP_MODULE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@" + MP_VERSION + "/vision_bundle.mjs";
  var MP_WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@" + MP_VERSION + "/wasm";
  var MP_MODEL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

  var HI_KEY = "nokiaSnakeHighScore";

  var DIRS = {
    UP: { x: 0, y: -1, name: "UP", arrow: "↑" },
    DOWN: { x: 0, y: 1, name: "DOWN", arrow: "↓" },
    LEFT: { x: -1, y: 0, name: "LEFT", arrow: "←" },
    RIGHT: { x: 1, y: 0, name: "RIGHT", arrow: "→" }
  };

  var HAND_CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [5, 9], [9, 10], [10, 11], [11, 12],
    [9, 13], [13, 14], [14, 15], [15, 16],
    [13, 17], [17, 18], [18, 19], [19, 20],
    [0, 17]
  ];

  function $(id) { return document.getElementById(id); }

  function dist(a, b) {
    var dx = a.x - b.x, dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  /* =================================================
     PURE GESTURE LOGIC (unit-testable)
     ================================================= */

  /**
   * Buffers palm-centre positions and fires a swipe when enough
   * movement happens inside the time window. Mirrored coordinates
   * are expected (hand right => x grows => "RIGHT").
   */
  function SwipeDetector(opts) {
    opts = opts || {};
    this.threshold = opts.threshold || 0.16;
    this.cooldownMs = opts.cooldownMs || 450;
    this.windowMs = opts.windowMs || 400;
    this.minSpanMs = opts.minSpanMs || 90;
    this.buffer = [];
    this.lastFired = -Infinity;
  }

  SwipeDetector.prototype.feed = function (x, y, t) {
    var now = (typeof t === "number") ? t : performance.now();

    if (now - this.lastFired < this.cooldownMs) {
      // keep buffer pinned to current position so pre-cooldown
      // motion cannot instantly fire again after cooldown
      this.buffer = [{ x: x, y: y, t: now }];
      return null;
    }

    this.buffer.push({ x: x, y: y, t: now });
    while (this.buffer.length && now - this.buffer[0].t > this.windowMs) {
      this.buffer.shift();
    }

    if (this.buffer.length < 3) return null;

    var old = this.buffer[0];
    var last = this.buffer[this.buffer.length - 1];
    var span = last.t - old.t;
    if (span < this.minSpanMs) return null;

    var dx = last.x - old.x;
    var dy = last.y - old.y;
    var adx = Math.abs(dx), ady = Math.abs(dy);

    if (adx < this.threshold && ady < this.threshold) return null;

    var dir = null;
    if (adx >= ady * 1.25 && adx >= this.threshold) dir = dx > 0 ? "RIGHT" : "LEFT";
    else if (ady >= adx * 1.25 && ady >= this.threshold) dir = dy > 0 ? "DOWN" : "UP";
    else { this.buffer = [{ x: x, y: y, t: now }]; return null; } // ambiguous diagonal

    this.lastFired = now;
    this.buffer = [];
    return dir;
  };

  SwipeDetector.prototype.reset = function () {
    this.buffer = [];
    this.lastFired = -Infinity;
  };

  /** Pure landmark helpers. lm = 21 hand landmarks {x,y,z}. */
  var handPose = {
    isPinch: function (lm) {
      if (!lm || lm.length < 21) return false;
      var handSize = dist(lm[0], lm[9]) || 1e-6;
      return dist(lm[4], lm[8]) < 0.45 * handSize;
    },

    _fingerExtended: function (lm, tip, pip) {
      return dist(lm[0], lm[tip]) > dist(lm[0], lm[pip]) * 1.05;
    },

    isOpenPalm: function (lm) {
      if (!lm || lm.length < 21) return false;
      if (handPose.isPinch(lm)) return false;
      var fingers = [[8, 6], [12, 10], [16, 14], [20, 18]];
      for (var i = 0; i < fingers.length; i++) {
        if (!handPose._fingerExtended(lm, fingers[i][0], fingers[i][1])) return false;
      }
      // thumb: tip farther from pinky MCP than the IP joint
      return dist(lm[4], lm[17]) > dist(lm[3], lm[17]);
    }
  };

  /* =================================================
     SNAKE GAME (Canvas)
     ================================================= */

  function SnakeGame(canvas, callbacks) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.cb = callbacks || {};

    this.cols = 24;
    this.rows = 24;
    this.cell = canvas.width / this.cols;

    this.baseInterval = 140;   // ms per step at level 1
    this.minInterval = 70;
    this.levelUpEvery = 5;     // foods per level
    this.pointsPerFood = 10;

    this.state = "READY";
    this.turbo = false;
    this.high = this._loadHigh();
    this.fps = 60;

    this._acc = 0;
    this._lastT = 0;
    this._raf = 0;
    this._fpsFrames = 0;
    this._fpsT = 0;

    this._resetBoard();
    this._bindInput();
    this._loop = this._loop.bind(this);
    this._raf = requestAnimationFrame(this._loop);

    this._emitState();
    this._emitScore();
  }

  SnakeGame.prototype._loadHigh = function () {
    try {
      var v = parseInt(localStorage.getItem(HI_KEY) || "0", 10);
      return isFinite(v) && v > 0 ? v : 0;
    } catch (e) { return 0; }
  };

  SnakeGame.prototype._saveHigh = function () {
    try { localStorage.setItem(HI_KEY, String(this.high)); } catch (e) { /* private mode */ }
  };

  SnakeGame.prototype._resetBoard = function () {
    var midY = Math.floor(this.rows / 2);
    this.snake = [
      { x: 8, y: midY },
      { x: 7, y: midY },
      { x: 6, y: midY }
    ];
    this.dir = DIRS.RIGHT;
    this.queue = [];
    this.foods = 0;
    this.score = 0;
    this.level = 1;
    this.food = null;
    this._spawnFood();
    this._acc = 0;
    this.turbo = false;
  };

  SnakeGame.prototype._spawnFood = function () {
    var free = [];
    for (var y = 0; y < this.rows; y++) {
      for (var x = 0; x < this.cols; x++) {
        var onSnake = false;
        for (var i = 0; i < this.snake.length; i++) {
          if (this.snake[i].x === x && this.snake[i].y === y) { onSnake = true; break; }
        }
        if (!onSnake) free.push({ x: x, y: y });
      }
    }
    if (!free.length) { this._win(); return; }
    this.food = free[Math.floor(Math.random() * free.length)];
  };

  /* ---------- input ---------- */

  SnakeGame.prototype._bindInput = function () {
    var self = this;
    this._onKey = function (e) {
      var k = (e.key || "").toLowerCase();
      var map = {
        arrowup: "UP", w: "UP",
        arrowdown: "DOWN", s: "DOWN",
        arrowleft: "LEFT", a: "LEFT",
        arrowright: "RIGHT", d: "RIGHT"
      };
      if (map[k]) {
        e.preventDefault();
        self.setDirection(map[k]);
        return;
      }
      if (e.code === "Space" || k === " ") {
        e.preventDefault();
        self.togglePause();
        return;
      }
      if (k === "enter") {
        e.preventDefault();
        self.startOrRestart();
      }
    };
    window.addEventListener("keydown", this._onKey);
  };

  SnakeGame.prototype.startOrRestart = function () {
    if (this.state === "READY") this.start();
    else if (this.state === "GAME OVER") this.restart();
    else if (this.state === "PAUSED") this.togglePause();
  };

  SnakeGame.prototype.start = function () {
    if (this.state === "READY") {
      this.state = "PLAYING";
      this._acc = 0;
      this._emitState();
    }
  };

  SnakeGame.prototype.togglePause = function () {
    if (this.state === "PLAYING") { this.state = "PAUSED"; this._emitState(); }
    else if (this.state === "PAUSED") { this.state = "PLAYING"; this._acc = 0; this._emitState(); }
  };

  SnakeGame.prototype.restart = function () {
    this._resetBoard();
    this.state = "PLAYING";
    this._emitState();
    this._emitScore();
  };

  SnakeGame.prototype.setTurbo = function (on) {
    this.turbo = !!on;
  };

  /** Queue-safe direction change: rejects 180° reversals. */
  SnakeGame.prototype.setDirection = function (nameOrDir) {
    var d = typeof nameOrDir === "string" ? DIRS[nameOrDir] : nameOrDir;
    if (!d) return false;

    var ref = this.queue.length ? this.queue[this.queue.length - 1] : this.dir;
    if (d.x === -ref.x && d.y === -ref.y) return false;   // 180°
    if (d.x === ref.x && d.y === ref.y) return false;     // same
    if (this.queue.length >= 2) return false;             // buffer full

    this.queue.push(d);
    if (this.cb.onDirection) this.cb.onDirection(d);
    return true;
  };

  /* ---------- simulation ---------- */

  SnakeGame.prototype._interval = function () {
    var interval = Math.max(this.minInterval, this.baseInterval - (this.level - 1) * 12);
    if (this.turbo) interval *= 0.58;
    return interval;
  };

  SnakeGame.prototype._step = function () {
    if (this.queue.length) this.dir = this.queue.shift();

    var head = {
      x: this.snake[0].x + this.dir.x,
      y: this.snake[0].y + this.dir.y
    };

    // walls
    if (head.x < 0 || head.x >= this.cols || head.y < 0 || head.y >= this.rows) {
      this._gameOver();
      return;
    }

    // self (ignore the tail cell — it moves away unless growing)
    var willGrow = this.food && head.x === this.food.x && head.y === this.food.y;
    var checkLen = willGrow ? this.snake.length : this.snake.length - 1;
    for (var i = 0; i < checkLen; i++) {
      if (this.snake[i].x === head.x && this.snake[i].y === head.y) {
        this._gameOver();
        return;
      }
    }

    this.snake.unshift(head);

    if (willGrow) {
      this.foods += 1;
      this.score += this.pointsPerFood;
      if (this.foods % this.levelUpEvery === 0) this.level += 1;
      if (this.score > this.high) { this.high = this.score; this._saveHigh(); }
      this._spawnFood();
      this._emitScore();
    } else {
      this.snake.pop();
    }
  };

  SnakeGame.prototype._gameOver = function () {
    this.state = "GAME OVER";
    this.turbo = false;
    this.queue = [];
    if (this.score >= this.high) { this.high = this.score; this._saveHigh(); }
    this._emitState();
    this._emitScore();
    if (this.cb.onGameOver) this.cb.onGameOver(this.score, this.high);
  };

  SnakeGame.prototype._win = function () {
    this._gameOver(); // board filled — treat as win/game over
  };

  SnakeGame.prototype._emitState = function () {
    if (this.cb.onState) this.cb.onState(this.state);
  };

  SnakeGame.prototype._emitScore = function () {
    if (this.cb.onScore) this.cb.onScore(this.score, this.high, this.level);
  };

  /* ---------- loop & render ---------- */

  SnakeGame.prototype._loop = function (t) {
    this._raf = requestAnimationFrame(this._loop);

    var dt = this._lastT ? Math.min(t - this._lastT, 250) : 16;
    this._lastT = t;

    this._fpsFrames++;
    if (t - this._fpsT >= 500) {
      this.fps = Math.round(this._fpsFrames * 1000 / (t - this._fpsT));
      this._fpsFrames = 0;
      this._fpsT = t;
      if (this.cb.onFps) this.cb.onFps(this.fps);
    }

    if (this.state === "PLAYING") {
      this._acc += dt;
      var iv = this._interval();
      var guard = 0;
      while (this._acc >= iv && this.state === "PLAYING" && guard < 4) {
        this._acc -= iv;
        this._step();
        guard++;
      }
    }

    this.draw();
  };

  SnakeGame.prototype.draw = function () {
    var ctx = this.ctx;
    var c = this.cell;
    var W = this.canvas.width, H = this.canvas.height;

    // LCD background
    ctx.fillStyle = "#9cb869";
    ctx.fillRect(0, 0, W, H);

    // subtle dot grid
    ctx.fillStyle = "rgba(30, 43, 18, 0.10)";
    for (var y = 0; y < this.rows; y++) {
      for (var x = 0; x < this.cols; x++) {
        ctx.fillRect(x * c + c / 2 - 1, y * c + c / 2 - 1, 2, 2);
      }
    }

    // food (pulsing)
    if (this.food) {
      var pulse = 1 + 0.12 * Math.sin(performance.now() / 150);
      var fx = this.food.x * c + c / 2;
      var fy = this.food.y * c + c / 2;
      ctx.fillStyle = "#b3372c";
      ctx.beginPath();
      ctx.arc(fx, fy, (c * 0.34) * pulse, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "rgba(179, 55, 44, 0.5)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(fx, fy, (c * 0.46) * pulse, 0, Math.PI * 2);
      ctx.stroke();
    }

    // snake
    for (var i = this.snake.length - 1; i >= 0; i--) {
      var seg = this.snake[i];
      var pad = i === 0 ? 2 : 3;
      var sx = seg.x * c + pad;
      var sy = seg.y * c + pad;
      var size = c - pad * 2;
      var r = i === 0 ? 6 : 4;

      ctx.fillStyle = i === 0 ? "#16260d" : (i % 2 ? "#223616" : "#2c4420");
      this._roundRect(ctx, sx, sy, size, size, r);
      ctx.fill();

      if (i === 0) {
        // eyes toward direction
        ctx.fillStyle = "#c7e08d";
        var cx = sx + size / 2, cy = sy + size / 2;
        var ox = this.dir.y !== 0 ? 3.5 : 0;
        var oy = this.dir.x !== 0 ? 3.5 : 0;
        var ex = this.dir.x * 2.6, ey = this.dir.y * 2.6;
        ctx.fillRect(cx + ex - 1.5 - ox, cy + ey - 1.5 - oy, 3, 3);
        ctx.fillRect(cx + ex - 1.5 + ox, cy + ey - 1.5 + oy, 3, 3);
      }
    }

    // paused dim
    if (this.state === "PAUSED") {
      ctx.fillStyle = "rgba(30, 43, 18, 0.35)";
      ctx.fillRect(0, 0, W, H);
    }
  };

  SnakeGame.prototype._roundRect = function (ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  };

  /* =================================================
     GESTURE CONTROLLER (camera + MediaPipe)
     ================================================= */

  function GestureController(opts) {
    this.video = opts.video;
    this.canvas = opts.canvas;
    this.ctx = this.canvas.getContext("2d");
    this.game = opts.game;
    this.ui = opts.ui || {};

    this.stream = null;
    this.landmarker = null;
    this.running = false;
    this.rafId = 0;
    this.lastVideoTime = -1;
    this.ts = 0;
    this.swipes = new SwipeDetector();

    this.palmSince = null;
    this.palmArmed = true;
    this.palmCooldownUntil = 0;
    this.lastGesture = "NONE";
    this.trackingActive = false;
    this.camFrames = 0;
    this.camFps = 0;
    this._fpsT = 0;
    this._gestureUntil = 0;
  }

  GestureController.prototype.isEnabled = function () {
    return !!this.stream;
  };

  GestureController.prototype.enable = async function () {
    if (this._connecting) return;
    this._connecting = true;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this._connecting = false;
      this._notice("Camera unavailable — Keyboard controls enabled", "error");
      return;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false
      });
    } catch (err) {
      this._connecting = false;
      this._notice("Camera unavailable — Keyboard controls enabled", "error");
      return;
    }

    this.video.srcObject = this.stream;
    try {
      await this.video.play();
    } catch (e) { /* autoplay guard — muted video will still play */ }

    if (this.ui.onCamera) this.ui.onCamera(true);
    if (this.ui.onStatus) this.ui.onStatus("track", "LOADING", "warn");

    // ---- MediaPipe (dynamic ESM import; failure must not break game) ----
    try {
      var vision = await import(MP_MODULE);
      var fileset = await vision.FilesetResolver.forVisionTasks(MP_WASM);
      var options = {
        baseOptions: { modelAssetPath: MP_MODEL, delegate: "GPU" },
        runningMode: "VIDEO",
        numHands: 1,
        minHandDetectionConfidence: 0.5,
        minHandPresenceConfidence: 0.5,
        minTrackingConfidence: 0.5
      };
      try {
        this.landmarker = await vision.HandLandmarker.createFromOptions(fileset, options);
      } catch (gpuErr) {
        options.baseOptions.delegate = "CPU";
        this.landmarker = await vision.HandLandmarker.createFromOptions(fileset, options);
      }
    } catch (err) {
      this.landmarker = null;
      this._connecting = false;
      if (this.ui.onStatus) this.ui.onStatus("track", "INACTIVE", "off");
      this._notice("Hand tracking unavailable — camera on, keyboard controls enabled", "error");
      return;
    }

    this._connecting = false;
    this.running = true;
    this._notice("Camera connected — show your hand to control the snake", "success");
    this._sizeCanvas();
    this._loop();
  };

  GestureController.prototype.disable = function () {
    this.running = false;
    if (this.rafId) cancelAnimationFrame(this.rafId);
    this.rafId = 0;
    if (this.stream) {
      this.stream.getTracks().forEach(function (t) { t.stop(); });
      this.stream = null;
    }
    this.video.srcObject = null;
    this.game.setTurbo(false);
    this._clearOverlay();
    if (this.ui.onCamera) this.ui.onCamera(false);
    if (this.ui.onStatus) this.ui.onStatus("track", "INACTIVE", "off");
    if (this.ui.onGesture) this.ui.onGesture("NONE");
    this.lastGesture = "NONE";
    this.trackingActive = false;
  };

  GestureController.prototype._sizeCanvas = function () {
    var w = this.video.videoWidth || 640;
    var h = this.video.videoHeight || 480;
    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }
  };

  GestureController.prototype._clearOverlay = function () {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  };

  GestureController.prototype._loop = function () {
    if (!this.running) return;
    this.rafId = requestAnimationFrame(this._loop.bind(this));

    try {
      if (this.video.readyState < 2 || !this.landmarker) return;
      if (this.video.currentTime === this.lastVideoTime) return;
      this.lastVideoTime = this.video.currentTime;

      this.ts = Math.max(performance.now(), this.ts + 1);
      var res = this.landmarker.detectForVideo(this.video, this.ts);

      this.camFrames++;
      var now = performance.now();
      if (now - this._fpsT >= 1000) {
        this.camFps = this.camFrames;
        this.camFrames = 0;
        this._fpsT = now;
        if (this.ui.onStatus) this.ui.onStatus("camFps", String(this.camFps));
      }

      var hands = res && res.landmarks && res.landmarks.length ? res.landmarks : null;

      if (!hands) {
        this._noHand(now);
      } else {
        this.trackingActive = true;
        if (this.ui.onStatus) this.ui.onStatus("track", "ACTIVE", "on");
        this._drawHand(hands[0]);
        this._interpret(hands[0], now);
      }
    } catch (err) {
      // never crash the page: stop tracking, keep keyboard alive
      this.running = false;
      this.game.setTurbo(false);
      if (this.ui.onStatus) this.ui.onStatus("track", "INACTIVE", "off");
      this._notice("Hand tracking stopped — Keyboard controls enabled", "error");
    }
  };

  GestureController.prototype._noHand = function (now) {
    if (this.trackingActive) this.trackingActive = false;
    if (this.ui.onStatus) this.ui.onStatus("track", "INACTIVE", "off");
    this._clearOverlay();
    this.game.setTurbo(false);
    this.palmSince = null;
    this.palmArmed = true;
    this.swipes.reset();
    if (now > this._gestureUntil) {
      this._setGesture("NONE", 0);
    }
  };

  GestureController.prototype._interpret = function (lm, now) {
    var game = this.game;

    // ---- pinch => turbo (held) ----
    if (handPose.isPinch(lm)) {
      game.setTurbo(true);
      this._setGesture("PINCH · TURBO", 400);
      this.palmSince = null;
      return;
    }
    game.setTurbo(false);

    // ---- open palm => pause toggle (armed / cooldown) ----
    if (handPose.isOpenPalm(lm)) {
      this.swipes.reset(); // palm is not a swipe
      if (this.palmSince === null) this.palmSince = now;
      var held = now - this.palmSince;
      if (this.palmArmed && held >= 200 && now >= this.palmCooldownUntil) {
        game.togglePause();
        this.palmArmed = false;
        this.palmCooldownUntil = now + 900;
        this._setGesture("OPEN PALM", 800);
      } else if (!this.palmArmed) {
        this._setGesture("OPEN PALM", 400);
      }
      return;
    }
    // palm released -> re-arm
    this.palmSince = null;
    this.palmArmed = true;

    // ---- swipes (mirrored coordinates => intuitive directions) ----
    var palm = lm[9];
    var dir = this.swipes.feed(1 - palm.x, palm.y, now);
    if (dir) {
      var accepted = game.state === "PLAYING" ? game.setDirection(dir) : false;
      this._setGesture(dir, 700);
      if (this.ui.onDirection) this.ui.onDirection(DIRS[dir], accepted || game.state !== "PLAYING");
      return;
    }

    if (now > this._gestureUntil) this._setGesture("NONE", 0);
  };

  GestureController.prototype._setGesture = function (label, ms) {
    this.lastGesture = label;
    if (ms > 0) this._gestureUntil = performance.now() + ms;
    if (this.ui.onGesture) this.ui.onGesture(label);
  };

  GestureController.prototype._drawHand = function (lm) {
    var cv = this.canvas, ctx = this.ctx;
    ctx.clearRect(0, 0, cv.width, cv.height);

    // mirror x so drawing lines up with the mirrored <video>
    var pts = lm.map(function (p) { return { x: (1 - p.x) * cv.width, y: p.y * cv.height }; });

    ctx.strokeStyle = "rgba(47, 122, 52, 0.95)";
    ctx.lineWidth = Math.max(2, cv.width / 260);
    ctx.lineCap = "round";
    for (var i = 0; i < HAND_CONNECTIONS.length; i++) {
      var a = pts[HAND_CONNECTIONS[i][0]];
      var b = pts[HAND_CONNECTIONS[i][1]];
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    ctx.fillStyle = "#e8f5e4";
    for (var j = 0; j < pts.length; j++) {
      ctx.beginPath();
      ctx.arc(pts[j].x, pts[j].y, Math.max(2.5, cv.width / 170), 0, Math.PI * 2);
      ctx.fill();
    }
    // palm centre highlight
    ctx.fillStyle = "#2f7a34";
    ctx.beginPath();
    ctx.arc(pts[9].x, pts[9].y, Math.max(4, cv.width / 120), 0, Math.PI * 2);
    ctx.fill();
  };

  GestureController.prototype._notice = function (msg, kind) {
    if (this.ui.onNotice) this.ui.onNotice(msg, kind);
  };

  /* =================================================
     UI WIRING
     ================================================= */

  var noticeTimer = 0;

  function showNotice(msg, kind) {
    var el = $("notice");
    el.textContent = msg;
    el.setAttribute("data-kind", kind || "info");
    el.hidden = false;
    el.style.animation = "none";
    void el.offsetWidth; // restart animation
    el.style.animation = "";
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(function () { el.hidden = true; }, 7000);
  }

  function init() {
    if (!$("gameCanvas")) return; // loaded on a page without the game UI
    var overlay = $("gameOverlay");

    var game = new SnakeGame($("gameCanvas"), {
      onState: function (state) {
        var statusEl = $("gameStatus");
        statusEl.textContent = state;
        statusEl.setAttribute("data-state", state);

        var pauseBtn = $("pauseBtn");
        pauseBtn.textContent = state === "PAUSED" ? "RESUME" : "PAUSE";

        var playing = state === "PLAYING";
        overlay.dataset.hidden = playing ? "true" : "false";

        if (!playing) {
          var kicker = $("overlayKicker");
          var title = $("overlayTitle");
          var sub = $("overlaySub");
          var scoreEl = $("overlayScore");
          var btn = $("overlayBtn");

          if (state === "READY") {
            kicker.textContent = "NOKIA SNAKE";
            title.textContent = "Ready?";
            sub.innerHTML = 'Press <kbd>ENTER</kbd> or hit Start to play.<br>Use <kbd>↑ ↓ ← →</kbd> or <kbd>W A S D</kbd> to steer.';
            scoreEl.hidden = true;
            btn.textContent = "START GAME";
          } else if (state === "PAUSED") {
            kicker.textContent = "PAUSED";
            title.textContent = "Take a breath";
            sub.innerHTML = 'Press <kbd>SPACE</kbd> or Open Palm to resume.';
            scoreEl.hidden = true;
            btn.textContent = "RESUME";
          } else if (state === "GAME OVER") {
            kicker.textContent = "GAME OVER";
            title.textContent = "You crashed!";
            sub.innerHTML = 'Press <kbd>ENTER</kbd> to play again.';
            scoreEl.hidden = false;
            scoreEl.textContent = "Score " + game.score + " · High " + game.high;
            btn.textContent = "PLAY AGAIN";
          }
        }
      },
      onScore: function (score, high, level) {
        $("scoreValue").textContent = String(score);
        $("highValue").textContent = String(high);
        $("levelValue").textContent = String(level);
      },
      onDirection: function (d) {
        $("dirBadge").textContent = "MOVE " + d.arrow;
      },
      onFps: function (fps) {
        $("fpsPill").textContent = fps + " FPS";
      }
    });

    overlay.dataset.hidden = "false";

    var gesture = new GestureController({
      video: $("camVideo"),
      canvas: $("landmarkCanvas"),
      game: game,
      ui: {
        onCamera: function (on) {
          $("camPlaceholder").hidden = on;
          var badge = $("camBadge");
          badge.textContent = on ? "CONNECTED" : "OFFLINE";
          badge.className = "badge " + (on ? "badge--on" : "badge--off");
          ["enableCamBtn", "enableCamBtn2"].forEach(function (id) {
            var b = $(id);
            b.disabled = on;
            b.textContent = on ? "CAMERA ON" : "ENABLE CAMERA";
          });
        },
        onStatus: function (key, value, tone) {
          if (key === "track") {
            var el = $("trackStatus");
            el.textContent = value;
            el.className = "val " + (tone === "on" ? "val--on" : tone === "off" ? "val--off" : "");
          } else if (key === "camFps") {
            $("camFps").textContent = value;
          }
        },
        onGesture: function (label) {
          $("gestureStatus").textContent = label;
        },
        onDirection: function (d) {
          $("dirBadge").textContent = "MOVE " + d.arrow;
        },
        onNotice: showNotice
      }
    });

    /* ---------- buttons ---------- */
    $("startBtn").addEventListener("click", function () { game.startOrRestart(); });
    $("pauseBtn").addEventListener("click", function () { game.togglePause(); });
    $("restartBtn").addEventListener("click", function () { game.restart(); });

    function camClick() { gesture.enable(); }
    $("enableCamBtn").addEventListener("click", camClick);
    $("enableCamBtn2").addEventListener("click", camClick);

    $("overlayBtn").addEventListener("click", function () { game.startOrRestart(); });

    /* ---------- page lifecycle ---------- */
    window.addEventListener("pagehide", function () { gesture.disable(); });

    // expose for automated tests
    window.__ns = {
      game: game,
      gesture: gesture,
      SwipeDetector: SwipeDetector,
      handPose: handPose,
      DIRS: DIRS
    };
  }

  // expose pure logic + classes (used by automated tests)
  window.NSG = {
    version: "1.0.0",
    SnakeGame: SnakeGame,
    GestureController: GestureController,
    SwipeDetector: SwipeDetector,
    handPose: handPose,
    DIRS: DIRS
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
