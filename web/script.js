/* ==========================================================
   NOKIA SNAKE — GESTURE AI  ·  landing page scripts
   ========================================================== */

(function () {
  "use strict";

  /* ---------------- mobile nav ---------------- */

  var toggle = document.getElementById("navToggle");
  var links = document.getElementById("navLinks");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });

    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("open");
      }
    });
  }

  /* ---------------- hero snake animation ---------------- */

  var grid = document.getElementById("heroGrid");

  if (grid) {
    var COLS = 12;
    var ROWS = 10;
    var cells = [];

    for (var i = 0; i < COLS * ROWS; i++) {
      var cell = document.createElement("i");
      grid.appendChild(cell);
      cells.push(cell);
    }

    var snake = [
      { x: 3, y: 5 },
      { x: 2, y: 5 },
      { x: 1, y: 5 }
    ];

    var dir = { x: 1, y: 0 };
    var food = { x: 8, y: 3 };

    var DIRS = [
      { x: 1, y: 0 },
      { x: -1, y: 0 },
      { x: 0, y: 1 },
      { x: 0, y: -1}
    ];

    function index(x, y) {
      return y * COLS + x;
    }

    function draw() {
      for (var i = 0; i < cells.length; i++) {
        cells[i].className = "";
      }
      for (var s = 0; s < snake.length; s++) {
        var c = cells[index(snake[s].x, snake[s].y)];
        if (c) c.className = "snake";
      }
      var f = cells[index(food.x, food.y)];
      if (f) f.className = "food";
    }

    function step() {
      // random gentle turns, never reverse
      if (Math.random() < 0.3) {
        var options = DIRS.filter(function (d) {
          return !(d.x === -dir.x && d.y === -dir.y);
        });
        dir = options[Math.floor(Math.random() * options.length)];
      }

      var head = {
        x: (snake[0].x + dir.x + COLS) % COLS,
        y: (snake[0].y + dir.y + ROWS) % ROWS
      };

      snake.unshift(head);

      if (head.x === food.x && head.y === food.y) {
        food = {
          x: Math.floor(Math.random() * COLS),
          y: Math.floor(Math.random() * ROWS)
        };
      } else {
        snake.pop();
      }

      draw();
    }

    draw();
    setInterval(step, 340);
  }

  /* ---------------- scroll reveal ---------------- */

  var revealTargets = document.querySelectorAll(
    ".card, .gcard, .tech__item, .pipeline li, .code"
  );

  if ("IntersectionObserver" in window) {
    revealTargets.forEach(function (el) {
      el.style.opacity = "0";
      el.style.transform = "translateY(14px)";
      el.style.transition = "opacity .5s ease, transform .5s ease";
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.style.opacity = "1";
            entry.target.style.transform = "none";
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    revealTargets.forEach(function (el) {
      observer.observe(el);
    });
  }
})();
