import pygame


class Panel:

    def __init__(
        self,
        rect
    ):

        self.rect = rect

    def draw(
        self,
        screen,
        border=(155, 188, 15),
        background=(10, 18, 7)
    ):

        pygame.draw.rect(

            screen,

            background,

            self.rect,

            border_radius=10
        )

        pygame.draw.rect(

            screen,

            border,

            self.rect,

            2,

            border_radius=10
        )


class ProgressBar:

    def __init__(
        self,
        rect,
        maximum=100
    ):

        self.rect = rect

        self.maximum = maximum

    def draw(

        self,
        screen,
        value
    ):

        x, y, w, h = self.rect

        pygame.draw.rect(

            screen,

            (20, 30, 10),

            self.rect,

            border_radius=5
        )

        ratio = max(

            0,

            min(
                1,
                value / self.maximum
            )
        )

        pygame.draw.rect(

            screen,

            (155, 188, 15),

            (
                x,
                y,
                int(w * ratio),
                h
            ),

            border_radius=5
        )