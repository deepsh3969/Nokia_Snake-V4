import pygame
import sys

from core.game import SnakeGame
from core.highscore import HighScore
from vision.hand_tracker import (
    HandTracker,
    CameraError,
    default_result,
    STATUS_CAMERA_UNAVAILABLE
)
from ui.hud import HUD


WIDTH = 1100
HEIGHT = 760
FPS = 60


def main():

    print(
        "\nNOKIA SNAKE V4 - GESTURE AI\n"
        "============================",
        flush=True
    )

    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    pygame.display.set_caption(
        "Nokia Snake V4 - Gesture AI"
    )

    clock = pygame.time.Clock()

    highscore = HighScore()

    game = SnakeGame(high_score=highscore.get())

    hud = HUD()

    # --------------------------------------------------
    # CAMERA (never fatal: keyboard always works)
    # --------------------------------------------------

    tracker = None

    camera_status = default_result(
        STATUS_CAMERA_UNAVAILABLE,
        "Camera unavailable"
    )

    try:

        tracker = HandTracker(camera_index=0)

        print("Camera: started", flush=True)

    except CameraError as error:

        print(f"Camera: {error}", flush=True)
        print("Keyboard controls active.", flush=True)

    except Exception as error:

        print(f"Camera error: {error}", flush=True)
        print("Keyboard controls active.", flush=True)

    running = True

    while running:

        dt = clock.tick(FPS) / 1000.0

        game_fps = clock.get_fps()

        # =================================================
        # EVENTS (keyboard fallback)
        # =================================================

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    running = False

                elif event.key in (pygame.K_UP, pygame.K_w):

                    game.set_direction("UP")

                elif event.key in (pygame.K_DOWN, pygame.K_s):

                    game.set_direction("DOWN")

                elif event.key in (pygame.K_LEFT, pygame.K_a):

                    game.set_direction("LEFT")

                elif event.key in (pygame.K_RIGHT, pygame.K_d):

                    game.set_direction("RIGHT")

                elif event.key == pygame.K_SPACE:

                    game.toggle_pause()

                elif event.key == pygame.K_r:

                    game.restart()

        # =================================================
        # CAMERA / GESTURES (non-blocking)
        # =================================================

        gesture = (
            tracker.get_result()
            if tracker
            else camera_status
        )

        # Swipe -> direction

        swipe = gesture.get("swipe")

        if swipe:

            game.set_direction(swipe)

        # Pinch -> turbo (only while held)

        game.turbo = gesture.get("pinch", False)

        # Fist -> pause (edge triggered)

        if gesture.get("fist_edge", False):

            game.toggle_pause()

        # Open palm -> restart (only when game over)

        if gesture.get("open_edge", False) and game.game_over:

            game.restart()

        # =================================================
        # GAME UPDATE
        # =================================================

        game.update(dt)

        # =================================================
        # HIGH SCORE
        # =================================================

        if game.score > highscore.get():

            highscore.save(game.score)

        # =================================================
        # DRAW
        # =================================================

        screen.fill(game.BLACK)

        hud.draw(screen, game, gesture, game_fps)

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
