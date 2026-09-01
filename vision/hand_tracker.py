import cv2
import mediapipe as mp
import numpy as np
import time
from collections import deque


class HandTracker:

    def __init__(
        self,
        camera_index=0
    ):

        # =================================================
        # CAMERA
        # =================================================

        self.cap = cv2.VideoCapture(
            camera_index,
            cv2.CAP_DSHOW
        )

        if not self.cap.isOpened():

            self.cap.release()

            self.cap = cv2.VideoCapture(
                camera_index
            )

        if not self.cap.isOpened():

            raise RuntimeError(
                "Could not open webcam."
            )

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            30
        )

        # =================================================
        # MEDIAPIPE
        # =================================================

        self.mp_hands = (
            mp.solutions.hands
        )

        self.mp_draw = (
            mp.solutions.drawing_utils
        )

        self.hands = self.mp_hands.Hands(

            static_image_mode=False,

            max_num_hands=1,

            model_complexity=0,

            min_detection_confidence=0.55,

            min_tracking_confidence=0.55
        )

        # =================================================
        # MOTION HISTORY
        # =================================================

        self.history = deque(
            maxlen=10
        )

        self.last_swipe_time = 0

        self.swipe_cooldown = 0.45

        # =================================================
        # EDGE STATES
        # =================================================

        self.last_pinch = False

        self.last_fist = False

        self.last_open = False

        # =================================================
        # FPS
        # =================================================

        self.frame_count = 0

        self.fps = 0

        self.fps_timer = time.time()

    # =====================================================
    # DISTANCE
    # =====================================================

    @staticmethod
    def distance(
        a,
        b
    ):

        return np.sqrt(

            (a.x - b.x) ** 2

            +

            (a.y - b.y) ** 2
        )

    # =====================================================
    # FINGER COUNT
    # =====================================================

    def count_fingers(
        self,
        lm
    ):

        count = 0

        # Index
        if lm[8].y < lm[6].y:

            count += 1

        # Middle
        if lm[12].y < lm[10].y:

            count += 1

        # Ring
        if lm[16].y < lm[14].y:

            count += 1

        # Pinky
        if lm[20].y < lm[18].y:

            count += 1

        # Thumb
        thumb = self.distance(
            lm[4],
            lm[5]
        )

        thumb_tip = self.distance(
            lm[4],
            lm[17]
        )

        if thumb > thumb_tip * 0.65:

            count += 1

        return count

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self):

        result = {

            "tracking": False,

            "swipe": None,

            "pinch": False,

            "fist_edge": False,

            "open_edge": False,

            "fingers": 0,

            "confidence": 0,

            "preview_rgb": None,

            "fps": self.fps
        }

        # =================================================
        # CAMERA FRAME
        # =================================================

        success, frame = self.cap.read()

        if not success:

            return result

        # =================================================
        # MIRROR
        # =================================================

        frame = cv2.flip(
            frame,
            1
        )

        # =================================================
        # FPS
        # =================================================

        self.frame_count += 1

        now = time.time()

        elapsed = (
            now
            - self.fps_timer
        )

        if elapsed >= 1.0:

            self.fps = (
                self.frame_count
                / elapsed
            )

            self.frame_count = 0

            self.fps_timer = now

        result["fps"] = self.fps

        # =================================================
        # MEDIAPIPE
        # =================================================

        rgb = cv2.cvtColor(

            frame,

            cv2.COLOR_BGR2RGB
        )

        processed = self.hands.process(
            rgb
        )

        # =================================================
        # HAND
        # =================================================

        if processed.multi_hand_landmarks:

            hand = (
                processed.multi_hand_landmarks[0]
            )

            lm = hand.landmark

            result["tracking"] = True

            result["confidence"] = 100

            # -------------------------------------------------
            # DRAW LANDMARKS
            # -------------------------------------------------

            self.mp_draw.draw_landmarks(

                frame,

                hand,

                self.mp_hands.HAND_CONNECTIONS,

                self.mp_draw.DrawingSpec(

                    color=(155, 188, 15),

                    thickness=2,

                    circle_radius=3
                ),

                self.mp_draw.DrawingSpec(

                    color=(215, 255, 60),

                    thickness=2
                )
            )

            # =================================================
            # PALM CENTER
            # =================================================

            center = np.array([

                lm[9].x,

                lm[9].y
            ])

            self.history.append(
                center
            )

            # =================================================
            # SWIPE
            # =================================================

            if len(self.history) >= 7:

                now = time.time()

                if (
                    now
                    - self.last_swipe_time
                    >= self.swipe_cooldown
                ):

                    start = self.history[0]

                    end = self.history[-1]

                    dx = end[0] - start[0]

                    dy = end[1] - start[1]

                    abs_dx = abs(dx)

                    abs_dy = abs(dy)

                    gesture = None

                    # -----------------------------------------
                    # RIGHT / LEFT
                    # -----------------------------------------

                    if abs_dx > abs_dy:

                        if abs_dx > 0.12:

                            if dx > 0:

                                gesture = "RIGHT"

                            else:

                                gesture = "LEFT"

                    # -----------------------------------------
                    # UP / DOWN
                    # -----------------------------------------

                    else:

                        if abs_dy > 0.12:

                            if dy > 0:

                                gesture = "DOWN"

                            else:

                                gesture = "UP"

                    if gesture:

                        result["swipe"] = gesture

                        self.history.clear()

                        self.last_swipe_time = now

            # =================================================
            # FINGERS
            # =================================================

            fingers = self.count_fingers(
                lm
            )

            result["fingers"] = fingers

            # =================================================
            # PINCH
            # =================================================

            pinch_distance = self.distance(

                lm[4],

                lm[8]
            )

            pinch = (
                pinch_distance < 0.055
            )

            result["pinch"] = pinch

            # =================================================
            # FIST
            # =================================================

            fist = (
                fingers <= 1
                and
                not pinch
            )

            fist_edge = (
                fist
                and
                not self.last_fist
            )

            result["fist_edge"] = (
                fist_edge
            )

            # =================================================
            # OPEN PALM
            # =================================================

            open_palm = (
                fingers >= 4
            )

            open_edge = (

                open_palm

                and

                not self.last_open
            )

            result["open_edge"] = (
                open_edge
            )

            # =================================================
            # SAVE STATES
            # =================================================

            self.last_pinch = pinch

            self.last_fist = fist

            self.last_open = open_palm

        else:

            self.history.clear()

            self.last_pinch = False

            self.last_fist = False

            self.last_open = False

        # =================================================
        # CAMERA UI
        # =================================================

        cv2.rectangle(

            frame,

            (
                0,
                0
            ),

            (
                640,
                48
            ),

            (
                5,
                10,
                5
            ),

            -1
        )

        if result["tracking"]:

            status = "LIVE  |  HAND DETECTED"

        else:

            status = "LIVE  |  SHOW YOUR HAND"

        cv2.putText(

            frame,

            status,

            (
                12,
                30
            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.65,

            (
                215,
                255,
                60
            ),

            2
        )

        # =================================================
        # GESTURE TEXT
        # =================================================

        if result["swipe"]:

            gesture_text = (
                "MOVE "
                + result["swipe"]
            )

        elif result["pinch"]:

            gesture_text = (
                "PINCH | TURBO"
            )

        elif result["fist_edge"]:

            gesture_text = (
                "FIST | PAUSE"
            )

        elif result["open_edge"]:

            gesture_text = (
                "OPEN PALM"
            )

        else:

            gesture_text = "READY"

        cv2.putText(

            frame,

            gesture_text,

            (
                12,
                78
            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.55,

            (
                230,
                240,
                190
            ),

            2
        )

        # =================================================
        # CONVERT FOR PYGAME
        # =================================================

        result["preview_rgb"] = (
            cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )
        )

        return result

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        try:

            self.hands.close()

        except Exception:

            pass

        try:

            self.cap.release()

        except Exception:

            pass

        cv2.destroyAllWindows()