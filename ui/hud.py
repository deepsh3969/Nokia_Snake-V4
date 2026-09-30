import pygame

from ui.components import Panel


# -------------------------------------------------------
# Font / text surface caches
# (fonts are expensive to create; rendering the same
#  strings every frame is expensive too)
# -------------------------------------------------------

_font_cache = {}
_text_cache = {}

_SYM_KEY = "symbol"


def _font(size):
    f = _font_cache.get(size)
    if f is None:
        f = pygame.font.Font(None, size)
        _font_cache[size] = f
    return f


def _render(key, font, text, color):
    ck = (key, text, color)
    surf = _text_cache.get(ck)
    if surf is None:
        surf = font.render(text, True, color)
        if len(_text_cache) > 4096:
            _text_cache.clear()
        _text_cache[ck] = surf
    return surf


DIRECTION_ARROWS = {
    "UP": "↑",
    "DOWN": "↓",
    "LEFT": "←",
    "RIGHT": "→"
}


class HUD:

    def __init__(self):

        self.title_font = pygame.font.Font(None, 36)
        self.section_font = pygame.font.Font(None, 23)
        self.font = pygame.font.Font(None, 20)
        self.small = pygame.font.Font(None, 17)
        self.value_font = pygame.font.Font(None, 30)

        # Symbol font (arrows / bullets render correctly here)

        self.symbol_font = pygame.font.SysFont(
            "segoeui,dejavusans,arial",
            15
        )

        # Right column layout

        self.camera_rect = (595, 78, 480, 340)
        self.status_rect = (595, 426, 480, 116)
        self.guide_rect = (595, 550, 480, 196)

        # Bottom strip (left column only)

        self.footer_rect = (25, 660, 550, 90)

    # =====================================================
    # TEXT
    # =====================================================

    def draw_text(
        self,
        screen,
        text,
        x,
        y,
        size=20,
        bright=False,
        color=None
    ):

        if color is None:

            color = (
                (215, 255, 60)
                if bright
                else (225, 240, 190)
            )

        font = _font(size)

        surface = _render(size, font, text, color)

        screen.blit(surface, (x, y))

        return surface

    def draw_right(self, screen, text, right, y, size=20, color=None):

        color = color or (225, 240, 190)

        font = _font(size)

        surface = _render(size, font, text, color)

        screen.blit(surface, (right - surface.get_width(), y))

    def draw_mixed(
        self,
        screen,
        x,
        y,
        segments,
        size=19,
        color=(225, 240, 190),
        gap=4
    ):

        cursor = x

        for text, is_symbol in segments:

            if is_symbol:

                font = self.symbol_font

                dy = y - 4

            else:

                font = _font(size)

                dy = y

            surface = _render(
                _SYM_KEY if is_symbol else size,
                font,
                text,
                color
            )

            screen.blit(surface, (cursor, dy))

            cursor += surface.get_width() + gap

        return cursor

    def measure_mixed(self, segments, size=19, gap=4):

        total = 0

        for text, is_symbol in segments:

            font = (
                self.symbol_font
                if is_symbol
                else _font(size)
            )

            total += font.size(text)[0] + gap

        return total - gap if segments else 0

    # =====================================================
    # COMPLETE HUD
    # =====================================================

    def draw(self, screen, game, gesture, game_fps=0):

        self.draw_header(screen, game, gesture, game_fps)

        game.draw(screen)

        self.draw_camera(screen, gesture)

        self.draw_status(screen, game, gesture, game_fps)

        self.draw_guide(screen)

        self.draw_footer(screen, game)

    # =====================================================
    # HEADER
    # =====================================================

    def draw_header(self, screen, game, gesture, game_fps):

        self.draw_text(
            screen,
            "NOKIA SNAKE AI",
            25,
            20,
            36,
            True
        )

        self.draw_text(
            screen,
            "GESTURE EDITION",
            27,
            54,
            17,
            False,
            (120, 150, 70)
        )

        status = gesture.get("status")

        tracking = gesture.get("tracking", False)

        if status == "CAMERA_UNAVAILABLE":

            dot = "X"
            label = "CAMERA OFF"
            color = (220, 90, 60)

        elif status == "TRACKING_UNAVAILABLE":

            dot = "!"
            label = "TRACKING UNAVAILABLE"
            color = (230, 180, 60)

        elif tracking:

            dot = "●"
            label = "HAND TRACKED"
            color = (215, 255, 60)

        else:

            dot = "○"
            label = "NO HAND"
            color = (150, 175, 90)

        segments = [(dot, True), (label, False)]

        width = self.measure_mixed(segments, 20)

        self.draw_mixed(
            screen,
            1075 - width,
            24,
            segments,
            20,
            color
        )

        self.draw_right(
            screen,
            f"GAME {game_fps:3.0f} FPS   CAM {gesture.get('fps', 0):3.0f} FPS",
            1075,
            52,
            17,
            (120, 150, 70)
        )

    # =====================================================
    # CAMERA PANEL
    # =====================================================

    def draw_camera(self, screen, gesture):

        x, y, w, h = self.camera_rect

        status = gesture.get("status")

        frame = gesture.get("preview_rgb")

        border = (
            (155, 188, 15)
            if status == "OK"
            else (200, 120, 50)
        )

        Panel((x, y, w, h)).draw(
            screen,
            border=border,
            background=(6, 11, 4)
        )

        inner = (x + 3, y + 3, w - 6, h - 6)

        if frame is not None and status == "OK":

            try:

                surface = pygame.surfarray.make_surface(
                    frame.swapaxes(0, 1)
                )

                surface = pygame.transform.smoothscale(
                    surface,
                    (inner[2], inner[3])
                )

                screen.blit(surface, (inner[0], inner[1]))

            except Exception:

                frame = None

        if frame is None or status != "OK":

            message = gesture.get(
                "message",
                "Camera unavailable"
            )

            if status == "STARTING":

                message = "Starting camera..."

            elif status == "OK":

                message = "Loading camera..."

            line_a = self.section_font.render(
                message,
                True,
                (230, 180, 60) if status != "STARTING" else (215, 255, 60)
            )

            line_b = self.small.render(
                "Keyboard controls still work",
                True,
                (150, 175, 90)
            )

            screen.blit(
                line_a,
                (
                    x + (w - line_a.get_width()) // 2,
                    y + h // 2 - 30
                )
            )

            screen.blit(
                line_b,
                (
                    x + (w - line_b.get_width()) // 2,
                    y + h // 2 + 6
                )
            )

        # Live badge

        if status == "OK":

            dot = "●"
            badge = "LIVE"
            badge_color = (215, 255, 60)

        elif status == "STARTING":

            dot = "○"
            badge = "STARTING"
            badge_color = (230, 180, 60)

        else:

            dot = "○"
            badge = "NO SIGNAL"
            badge_color = (220, 90, 60)

        badge_bg = pygame.Surface((140, 26), pygame.SRCALPHA)

        badge_bg.fill((4, 8, 3, 200))

        screen.blit(badge_bg, (x + 12, y + 12))

        self.draw_mixed(
            screen,
            x + 22,
            y + 16,
            [(dot, True), (badge, False)],
            18,
            badge_color
        )

        # Panel title

        self.draw_right(
            screen,
            "CAMERA / GESTURE",
            x + w - 14,
            y + 17,
            18,
            (120, 150, 70)
        )

    # =====================================================
    # STATUS PANEL
    # =====================================================

    def draw_status(self, screen, game, gesture, game_fps):

        x, y, w, h = self.status_rect

        Panel((x, y, w, h)).draw(screen)

        self.draw_text(
            screen,
            "STATUS",
            x + 16,
            y + 12,
            20,
            True
        )

        # Current gesture

        swipe = gesture.get("swipe")

        if swipe:

            current = f"SWIPE {swipe}"

        elif gesture.get("pinch"):

            current = "PINCH (TURBO)"

        elif gesture.get("tracking"):

            current = f"{gesture.get('fingers', 0)} FINGERS"

        elif gesture.get("status") != "OK":

            current = gesture.get("message", "UNAVAILABLE")

        else:

            current = "NONE"

        self.draw_text(
            screen,
            "Current Gesture:",
            x + 16,
            y + 40,
            19,
            False,
            (150, 175, 90)
        )

        self.draw_text(
            screen,
            current,
            x + 168,
            y + 40,
            19,
            True
        )

        # Direction

        direction = game.direction

        self.draw_text(
            screen,
            "Direction:",
            x + 16,
            y + 64,
            19,
            False,
            (150, 175, 90)
        )

        arrow = DIRECTION_ARROWS.get(direction, "")

        self.draw_mixed(
            screen,
            x + 168,
            y + 64,
            [(arrow, True), (direction, False)],
            19,
            (215, 255, 60)
        )

        # Game status

        if game.game_over:

            state = "GAME OVER"

            state_color = (220, 90, 60)

        elif game.paused:

            state = "PAUSED"

            state_color = (230, 180, 60)

        elif game.turbo:

            state = "PLAYING (TURBO)"

            state_color = (215, 255, 60)

        else:

            state = "PLAYING"

            state_color = (215, 255, 60)

        self.draw_text(
            screen,
            "Status:",
            x + 16,
            y + 88,
            19,
            False,
            (150, 175, 90)
        )

        self.draw_text(
            screen,
            state,
            x + 168,
            y + 88,
            19,
            True,
            state_color
        )

        # Turbo bar

        if game.turbo:

            self.draw_right(
                screen,
                "TURBO ACTIVE",
                x + w - 16,
                y + 88,
                18,
                (215, 255, 60)
            )

    # =====================================================
    # GESTURE GUIDE
    # =====================================================

    def draw_guide(self, screen):

        x, y, w, h = self.guide_rect

        Panel((x, y, w, h)).draw(screen)

        self.draw_text(
            screen,
            "GESTURE GUIDE",
            x + 16,
            y + 12,
            20,
            True
        )

        entries = [
            ("←", "Swipe LEFT", "Move left"),
            ("→", "Swipe RIGHT", "Move right"),
            ("↑", "Swipe UP", "Move up"),
            ("↓", "Swipe DOWN", "Move down"),
            ("~", "PINCH", "Turbo (hold)"),
            ("", "CLOSED FIST", "Pause / resume"),
            ("", "OPEN PALM", "Restart (game over)")
        ]

        for i, (symbol, name, action) in enumerate(entries):

            yy = y + 40 + i * 21

            if symbol:

                self.draw_mixed(
                    screen,
                    x + 20,
                    yy,
                    [(symbol, True)],
                    17,
                    (215, 255, 60)
                )

            self.draw_text(
                screen,
                name,
                x + 48,
                yy,
                17,
                False,
                (225, 240, 190)
            )

            self.draw_text(
                screen,
                action,
                x + 180,
                yy,
                17,
                False,
                (120, 150, 70)
            )

    # =====================================================
    # FOOTER
    # =====================================================

    def draw_footer(self, screen, game):

        x, y, w, h = self.footer_rect

        Panel((x, y, w, h)).draw(screen)

        columns = [
            ("SCORE", game.score, x + 16),
            ("HIGH SCORE", game.high_score, x + 150),
            ("LEVEL", game.level, x + 330)
        ]

        for label, value, cx in columns:

            self.draw_text(
                screen,
                label,
                cx,
                y + 12,
                16,
                False,
                (150, 175, 90)
            )

            self.draw_text(
                screen,
                str(value),
                cx,
                y + 32,
                28,
                True
            )

        self.draw_text(
            screen,
            "WASD / ARROWS: MOVE   SPACE: PAUSE   R: RESTART   ESC: QUIT",
            x + 16,
            y + 68,
            16,
            False,
            (120, 150, 70)
        )
