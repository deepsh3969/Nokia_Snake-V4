import pygame


class Menu:

    def __init__(self):

        self.font = pygame.font.Font(
            None,
            40
        )

        self.small = pygame.font.Font(
            None,
            20
        )

    def draw(
        self,
        screen
    ):

        screen.fill(
            (4, 8, 3)
        )

        title = self.font.render(

            "NOKIA SNAKE",

            True,

            (215, 255, 60)
        )

        subtitle = self.small.render(

            "GESTURE AI EDITION",

            True,

            (225, 240, 190)
        )

        screen.blit(

            title,

            (
                screen.get_width() // 2
                - title.get_width() // 2,

                250
            )
        )

        screen.blit(

            subtitle,

            (
                screen.get_width() // 2
                - subtitle.get_width() // 2,

                305
            )
        )