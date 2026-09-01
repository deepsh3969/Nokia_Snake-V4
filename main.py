import pygame
import sys

from core.game import SnakeGame
from core.highscore import HighScore
from vision.hand_tracker import HandTracker
from ui.hud import HUD


WIDTH = 1100
HEIGHT = 760
FPS = 60


def main():

    print("\n==============================")
    print("     NOKIA SNAKE V4")
    print("   GESTURE AI EDITION")
    print("==============================\n")

    pygame.init()

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT)
    )

    pygame.display.set_caption(
        "Nokia Snake V4 - Gesture AI"
    )

    clock = pygame.time.Clock()

    highscore = HighScore()

    game = SnakeGame(
        high_score=highscore.get()
    )

    hud = HUD()

    # --------------------------------------------------
    # CAMERA
    # --------------------------------------------------

    tracker = None

    try:

        print("Opening webcam...")

        tracker = HandTracker(
            camera_index=0
        )

        print("Webcam started.")

    except Exception as e:

        print("\nCamera could not start:")
        print(e)
        print("\nKeyboard controls will still work.\n")

    running = True

    while running:

        dt = clock.tick(FPS) / 1000.0

        # =================================================
        # EVENTS
        # =================================================

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False

            elif event.type == pygame.KEYDOWN:

                # ------------------------------
                # QUIT
                # ------------------------------

                if event.key == pygame.K_ESCAPE:

                    running = False

                # ------------------------------
                # MOVEMENT
                # ------------------------------

                elif event.key in (
                    pygame.K_UP,
                    pygame.K_w
                ):

                    game.set_direction("UP")

                elif event.key in (
                    pygame.K_DOWN,
                    pygame.K_s
                ):

                    game.set_direction("DOWN")

                elif event.key in (
                    pygame.K_LEFT,
                    pygame.K_a
                ):

                    game.set_direction("LEFT")

                elif event.key in (
                    pygame.K_RIGHT,
                    pygame.K_d
                ):

                    game.set_direction("RIGHT")

                # ------------------------------
                # PAUSE
                # ------------------------------

                elif event.key == pygame.K_SPACE:

                    game.toggle_pause()

                # ------------------------------
                # RESTART
                # ------------------------------

                elif event.key == pygame.K_r:

                    game.restart()

        # =================================================
        # CAMERA
        # =================================================

        if tracker:

            gesture = tracker.update()

        else:

            gesture = {
                "tracking": False,
                "swipe": None,
                "pinch": False,
                "fist_edge": False,
                "open_edge": False,
                "fingers": 0,
                "confidence": 0,
                "preview_rgb": None,
                "fps": 0
            }

        # =================================================
        # GESTURE MOVEMENT
        # =================================================

        swipe = gesture.get("swipe")

        if swipe:

            game.set_direction(
                swipe
            )

        # =================================================
        # PINCH = TURBO
        # =================================================

        game.turbo = gesture.get(
            "pinch",
            False
        )

        # =================================================
        # FIST = PAUSE
        # =================================================

        if gesture.get(
            "fist_edge",
            False
        ):

            game.toggle_pause()

        # =================================================
        # OPEN PALM = RESTART
        # =================================================

        if gesture.get(
            "open_edge",
            False
        ):

            if game.game_over:

                game.restart()

        # =================================================
        # GAME UPDATE
        # =================================================

        game.update(
            dt
        )

        # =================================================
        # HIGH SCORE
        # =================================================

        if game.score > highscore.get():

            highscore.save(
                game.score
            )

        # =================================================
        # DRAW
        # =================================================

        screen.fill(
            game.BLACK
        )

        hud.draw(
            screen,
            game,
            gesture
        )

        pygame.display.flip()

    # =====================================================
    # CLEANUP
    # =====================================================

    if tracker:

        tracker.close()

    pygame.quit()

    sys.exit()


if __name__ == "__main__":

    main()