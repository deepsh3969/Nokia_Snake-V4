import random
import pygame

from core.particles import ParticleSystem


class SnakeGame:

    def __init__(
        self,
        high_score=0
    ):

        # =================================================
        # BOARD
        # =================================================

        self.cell = 25

        self.cols = 22
        self.rows = 22

        self.board_x = 25
        self.board_y = 100

        self.board_width = (
            self.cols * self.cell
        )

        self.board_height = (
            self.rows * self.cell
        )

        # =================================================
        # COLORS
        # =================================================

        self.BLACK = (4, 8, 3)

        self.DARK = (10, 18, 7)

        self.GRID = (24, 38, 12)

        self.GREEN = (155, 188, 15)

        self.BRIGHT = (215, 255, 60)

        self.WHITE = (230, 240, 190)

        self.RED = (220, 60, 45)

        # =================================================
        # STATE
        # =================================================

        self.score = 0

        self.high_score = high_score

        self.level = 1

        self.game_over = False

        self.paused = False

        self.turbo = False

        self.move_timer = 0

        self.particles = ParticleSystem()

        self.restart()

    # =====================================================
    # RESTART
    # =====================================================

    def restart(self):

        center_x = self.cols // 2
        center_y = self.rows // 2

        self.snake = [

            (center_x, center_y),

            (center_x - 1, center_y),

            (center_x - 2, center_y),

            (center_x - 3, center_y)
        ]

        self.direction = "RIGHT"

        self.next_direction = "RIGHT"

        self.score = 0

        self.level = 1

        self.game_over = False

        self.paused = False

        self.turbo = False

        self.move_timer = 0

        self.food = self.spawn_food()

        self.particles.clear()

    # =====================================================
    # FOOD
    # =====================================================

    def spawn_food(self):

        while True:

            position = (

                random.randrange(
                    self.cols
                ),

                random.randrange(
                    self.rows
                )
            )

            if position not in self.snake:

                return position

    # =====================================================
    # DIRECTION
    # =====================================================

    def set_direction(
        self,
        direction
    ):

        opposites = {

            "UP": "DOWN",

            "DOWN": "UP",

            "LEFT": "RIGHT",

            "RIGHT": "LEFT"
        }

        if direction not in opposites:

            return

        if direction == opposites[
            self.direction
        ]:

            return

        self.next_direction = direction

    # =====================================================
    # PAUSE
    # =====================================================

    def toggle_pause(self):

        if not self.game_over:

            self.paused = not self.paused

    # =====================================================
    # SPEED
    # =====================================================

    def get_move_interval(self):

        # Deliberately slower than V3

        base_speed = 0.34

        acceleration = (
            self.level - 1
        ) * 0.008

        interval = (
            base_speed
            - acceleration
        )

        interval = max(
            0.22,
            interval
        )

        if self.turbo:

            interval *= 0.70

        return interval

    # =====================================================
    # UPDATE
    # =====================================================

    def update(
        self,
        dt
    ):

        self.particles.update(
            dt
        )

        if self.game_over:

            return

        if self.paused:

            return

        self.move_timer += dt

        if (
            self.move_timer
            < self.get_move_interval()
        ):

            return

        self.move_timer = 0

        self.direction = (
            self.next_direction
        )

        head_x, head_y = self.snake[0]

        if self.direction == "UP":

            head_y -= 1

        elif self.direction == "DOWN":

            head_y += 1

        elif self.direction == "LEFT":

            head_x -= 1

        elif self.direction == "RIGHT":

            head_x += 1

        new_head = (
            head_x,
            head_y
        )

        # =================================================
        # WALL COLLISION
        # =================================================

        if (

            head_x < 0

            or head_x >= self.cols

            or head_y < 0

            or head_y >= self.rows
        ):

            self.end_game()

            return

        # =================================================
        # SELF COLLISION
        # =================================================

        if new_head in self.snake:

            self.end_game()

            return

        self.snake.insert(
            0,
            new_head
        )

        # =================================================
        # FOOD
        # =================================================

        if new_head == self.food:

            self.score += 10

            self.level = (
                self.score // 50
            ) + 1

            px = (
                self.board_x
                + self.food[0] * self.cell
                + self.cell // 2
            )

            py = (
                self.board_y
                + self.food[1] * self.cell
                + self.cell // 2
            )

            self.particles.explode(
                px,
                py
            )

            self.food = (
                self.spawn_food()
            )

        else:

            self.snake.pop()

    # =====================================================
    # GAME OVER
    # =====================================================

    def end_game(self):

        self.game_over = True

        if self.score > self.high_score:

            self.high_score = self.score

    # =====================================================
    # DRAW
    # =====================================================

    def draw(self, screen):

        # =================================================
        # BOARD
        # =================================================

        board_rect = (

            self.board_x,

            self.board_y,

            self.board_width,

            self.board_height
        )

        pygame.draw.rect(

            screen,

            self.DARK,

            board_rect
        )

        # =================================================
        # GRID
        # =================================================

        for x in range(
            self.cols + 1
        ):

            px = (
                self.board_x
                + x * self.cell
            )

            pygame.draw.line(

                screen,

                self.GRID,

                (
                    px,
                    self.board_y
                ),

                (
                    px,
                    self.board_y
                    + self.board_height
                )
            )

        for y in range(
            self.rows + 1
        ):

            py = (
                self.board_y
                + y * self.cell
            )

            pygame.draw.line(

                screen,

                self.GRID,

                (
                    self.board_x,
                    py
                ),

                (
                    self.board_x
                    + self.board_width,
                    py
                )
            )

        # =================================================
        # BORDER
        # =================================================

        pygame.draw.rect(

            screen,

            self.GREEN,

            board_rect,

            3
        )

        # =================================================
        # FOOD
        # =================================================

        fx, fy = self.food

        center = (

            self.board_x
            + fx * self.cell
            + self.cell // 2,

            self.board_y
            + fy * self.cell
            + self.cell // 2
        )

        pygame.draw.circle(

            screen,

            self.BRIGHT,

            center,

            7
        )

        # =================================================
        # SNAKE
        # =================================================

        for i, (
            x,
            y
        ) in enumerate(
            self.snake
        ):

            rect = (

                self.board_x
                + x * self.cell
                + 2,

                self.board_y
                + y * self.cell
                + 2,

                self.cell - 4,

                self.cell - 4
            )

            color = (

                self.BRIGHT
                if i == 0
                else self.GREEN
            )

            pygame.draw.rect(

                screen,

                color,

                rect,

                border_radius=5
            )

        # =================================================
        # PARTICLES
        # =================================================

        self.particles.draw(
            screen
        )

        # =================================================
        # PAUSED
        # =================================================

        if self.paused:

            self.draw_overlay(

                screen,

                "PAUSED",

                "FIST / SPACE TO RESUME"
            )

        # =================================================
        # GAME OVER
        # =================================================

        if self.game_over:

            self.draw_overlay(

                screen,

                "GAME OVER",

                "OPEN PALM / R TO RESTART"
            )

    # =====================================================
    # OVERLAY
    # =====================================================

    def draw_overlay(
        self,
        screen,
        title,
        subtitle
    ):

        overlay = pygame.Surface(

            (
                self.board_width,
                self.board_height
            ),

            pygame.SRCALPHA
        )

        overlay.fill(
            (0, 0, 0, 175)
        )

        screen.blit(

            overlay,

            (
                self.board_x,
                self.board_y
            )
        )

        title_font = pygame.font.Font(
            None,
            46
        )

        subtitle_font = pygame.font.Font(
            None,
            20
        )

        title_surface = title_font.render(

            title,

            True,

            self.BRIGHT
        )

        subtitle_surface = subtitle_font.render(

            subtitle,

            True,

            self.WHITE
        )

        cx = (
            self.board_x
            + self.board_width // 2
        )

        cy = (
            self.board_y
            + self.board_height // 2
        )

        screen.blit(

            title_surface,

            (
                cx
                - title_surface.get_width() // 2,

                cy - 35
            )
        )

        screen.blit(

            subtitle_surface,

            (
                cx
                - subtitle_surface.get_width() // 2,

                cy + 25
            )
        )