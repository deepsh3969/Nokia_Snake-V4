import pygame


class HUD:

    def __init__(self):

        self.title_font = pygame.font.Font(
            None,
            32
        )

        self.font = pygame.font.Font(
            None,
            21
        )

        self.small = pygame.font.Font(
            None,
            17
        )

        self.large = pygame.font.Font(
            None,
            27
        )

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
        bright=False
    ):

        font = pygame.font.Font(
            None,
            size
        )

        color = (

            (215, 255, 60)
            if bright
            else
            (225, 240, 190)
        )

        surface = font.render(

            text,

            True,

            color
        )

        screen.blit(

            surface,

            (
                x,
                y
            )
        )

    # =====================================================
    # COMPLETE HUD
    # =====================================================

    def draw(

        self,
        screen,
        game,
        gesture
    ):

        self.draw_header(
            screen,
            game
        )

        game.draw(
            screen
        )

        self.draw_camera(
            screen,
            gesture
        )

        self.draw_controls(
            screen
        )

        self.draw_status(
            screen,
            game,
            gesture
        )

        self.draw_footer(
            screen,
            game
        )

    # =====================================================
    # HEADER
    # =====================================================

    def draw_header(

        self,
        screen,
        game
    ):

        self.draw_text(

            screen,

            "NOKIA SNAKE",

            25,

            25,

            32,

            True
        )

        self.draw_text(

            screen,

            f"SCORE  {game.score}",

            275,

            31,

            21
        )

        self.draw_text(

            screen,

            f"LEVEL  {game.level}",

            410,

            31,

            21
        )

        self.draw_text(

            screen,

            "GESTURE AI",

            820,

            31,

            21,

            True
        )

    # =====================================================
    # CAMERA
    # =====================================================

    def draw_camera(

        self,
        screen,
        gesture
    ):

        x = 600

        y = 80

        width = 470

        height = 300

        frame = gesture.get(
            "preview_rgb"
        )

        pygame.draw.rect(

            screen,

            (8, 15, 5),

            (
                x,
                y,
                width,
                height
            ),

            border_radius=12
        )

        if frame is not None:

            try:

                surface = (
                    pygame.surfarray.make_surface(
                        frame.swapaxes(
                            0,
                            1
                        )
                    )
                )

                surface = (
                    pygame.transform.smoothscale(

                        surface,

                        (
                            width,
                            height
                        )
                    )
                )

                screen.blit(

                    surface,

                    (
                        x,
                        y
                    )
                )

            except Exception as error:

                print(
                    "Camera rendering error:",
                    error
                )

        else:

            self.draw_text(

                screen,

                "CAMERA INITIALIZING...",

                x + 135,

                y + 140,

                20,

                True
            )

        pygame.draw.rect(

            screen,

            (155, 188, 15),

            (
                x,
                y,
                width,
                height
            ),

            3,

            border_radius=12
        )

        # Status

        if gesture.get(
            "tracking"
        ):

            status = "● HAND TRACKING"

        else:

            status = "○ SHOW HAND"

        self.draw_text(

            screen,

            status,

            x + 15,

            y + 15,

            17,

            True
        )

    # =====================================================
    # CONTROLS
    # =====================================================

    def draw_controls(

        self,
        screen
    ):

        x = 600

        y = 405

        self.draw_text(

            screen,

            "GESTURE TEMPLATE",

            x,

            y,

            24,

            True
        )

        controls = [

            ("←", "SWIPE LEFT"),

            ("→", "SWIPE RIGHT"),

            ("↑", "SWIPE UP"),

            ("↓", "SWIPE DOWN"),

            ("🤏", "PINCH  •  TURBO"),

            ("✊", "FIST  •  PAUSE"),

            ("✋", "OPEN PALM  •  RESTART")
        ]

        for i, (
            symbol,
            label
        ) in enumerate(
            controls
        ):

            yy = (
                y
                + 38
                + i * 29
            )

            self.draw_text(

                screen,

                symbol,

                x,

                yy,

                20,

                True
            )

            self.draw_text(

                screen,

                label,

                x + 38,

                yy + 1,

                16
            )

    # =====================================================
    # STATUS
    # =====================================================

    def draw_status(

        self,
        screen,
        game,
        gesture
    ):

        x = 600

        y = 640

        swipe = gesture.get(
            "swipe"
        )

        if swipe:

            current = (
                "MOVE "
                + swipe
            )

        elif gesture.get(
            "pinch"
        ):

            current = "TURBO"

        elif gesture.get(
            "tracking"
        ):

            current = (
                f"{gesture.get('fingers', 0)} "
                "FINGERS"
            )

        else:

            current = "READY"

        self.draw_text(

            screen,

            f"CURRENT: {current}",

            x,

            y,

            21,

            True
        )

        self.draw_text(

            screen,

            f"CAMERA: {gesture.get('fps', 0):.0f} FPS",

            x + 230,

            y,

            17
        )

    # =====================================================
    # FOOTER
    # =====================================================

    def draw_footer(

        self,
        screen,
        game
    ):

        self.draw_text(

            screen,

            "WASD / ARROWS  •  MOVE",

            25,

            705,

            16
        )

        self.draw_text(

            screen,

            "SPACE  •  PAUSE",

            250,

            705,

            16
        )

        self.draw_text(

            screen,

            "R  •  RESTART",

            410,

            705,

            16
        )

        self.draw_text(

            screen,

            f"HIGH SCORE  {game.high_score}",

            820,

            705,

            16,

            True
        )