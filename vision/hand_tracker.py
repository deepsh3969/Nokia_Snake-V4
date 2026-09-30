import threading
import time
from collections import deque

import cv2
import numpy as np

try:
    import mediapipe as mp

    MEDIAPIPE_AVAILABLE = True

except Exception:

    mp = None

    MEDIAPIPE_AVAILABLE = False


STATUS_STARTING = "STARTING"
STATUS_OK = "OK"
STATUS_CAMERA_UNAVAILABLE = "CAMERA_UNAVAILABLE"
STATUS_TRACKING_UNAVAILABLE = "TRACKING_UNAVAILABLE"


class CameraError(RuntimeError):
    pass


def default_result(
    status=STATUS_STARTING,
    message="Starting camera..."
):

    return {
        "tracking": False,
        "swipe": None,
        "pinch": False,
        "fist_edge": False,
        "open_edge": False,
        "fingers": 0,
        "confidence": 0,
        "preview_rgb": None,
        "fps": 0.0,
        "status": status,
        "message": message
    }


class SwipeDetector:

    def __init__(
        self,
        cooldown=0.45,
        threshold=0.12,
        min_points=7,
        maxlen=10
    ):

        self.cooldown = cooldown
        self.threshold = threshold
        self.min_points = min_points

        self.history = deque(maxlen=maxlen)

        self.last_time = float("-inf")

    def feed(self, x, y, now=None):

        if now is None:

            now = time.time()

        self.history.append((x, y))

        if len(self.history) < self.min_points:

            return None

        if now - self.last_time < self.cooldown:

            return None

        start = self.history[0]
        end = self.history[-1]

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        gesture = None

        if abs(dx) > abs(dy):

            if abs(dx) > self.threshold:

                gesture = "RIGHT" if dx > 0 else "LEFT"

        else:

            if abs(dy) > self.threshold:

                gesture = "DOWN" if dy > 0 else "UP"

        if gesture:

            self.history.clear()
            self.last_time = now

        return gesture

    def clear(self):

        self.history.clear()


def open_camera(preferred_index=0):

    candidates = []

    for index in (preferred_index, 0, 1, 2):

        if index not in candidates:

            candidates.append(index)

    backends = []

    if hasattr(cv2, "CAP_DSHOW"):

        backends.append(cv2.CAP_DSHOW)

    backends.append(cv2.CAP_ANY)

    errors = []

    for index in candidates:

        for backend in backends:

            cap = cv2.VideoCapture(index, backend)

            if cap.isOpened():

                cap.set(
                    cv2.CAP_PROP_FRAME_WIDTH,
                    640
                )

                cap.set(
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    480
                )

                cap.set(
                    cv2.CAP_PROP_FPS,
                    30
                )

                return cap, index, backend

            cap.release()

            errors.append(
                f"index {index} backend {backend}"
            )

    raise CameraError(
        "Camera unavailable. Tried: "
        + ", ".join(errors)
    )


class HandTracker:

    def __init__(
        self,
        camera_index=0
    ):

        self.cap, self.camera_index, self.backend = (
            open_camera(camera_index)
        )

        # ------------------------------
        # MEDIAPIPE
        # ------------------------------

        self.tracking_available = False

        self.hands = None

        if MEDIAPIPE_AVAILABLE:

            try:

                self.hands = (
                    mp.solutions.hands.Hands(
                        static_image_mode=False,
                        max_num_hands=1,
                        model_complexity=0,
                        min_detection_confidence=0.55,
                        min_tracking_confidence=0.55
                    )
                )

                self.mp_hands = mp.solutions.hands
                self.mp_draw = mp.solutions.drawing_utils

                self.tracking_available = True

            except Exception:

                self.hands = None
                self.tracking_available = False

        # ------------------------------
        # GESTURE STATE
        # ------------------------------

        self.swipe_detector = SwipeDetector()

        self.last_fist = False
        self.last_open = False

        self.last_toggle_time = 0.0
        self.toggle_cooldown = 0.7

        # ------------------------------
        # THREAD STATE
        # ------------------------------

        self._lock = threading.Lock()

        self._result = default_result()

        self._running = True

        self._frame_count = 0
        self._fps_window_start = time.time()
        self._camera_fps = 0.0

        self._started_at = time.time()

        self._thread = threading.Thread(
            target=self._worker,
            name="hand-tracker",
            daemon=True
        )

        self._thread.start()

    # =====================================================
    # WORKER
    # =====================================================

    def _worker(self):

        consecutive_failures = 0

        got_frame = False

        while self._running:

            ok, frame = self.cap.read()

            if not ok or frame is None:

                consecutive_failures += 1

                if consecutive_failures >= 8:

                    self._publish(
                        default_result(
                            STATUS_CAMERA_UNAVAILABLE,
                            "Camera unavailable"
                        )
                    )

                time.sleep(0.05)

                continue

            consecutive_failures = 0

            got_frame = True

            now = time.time()

            # --------------------------
            # FPS
            # --------------------------

            self._frame_count += 1

            elapsed = now - self._fps_window_start

            if elapsed >= 1.0:

                self._camera_fps = (
                    self._frame_count / elapsed
                )

                self._frame_count = 0
                self._fps_window_start = now

            # --------------------------
            # NO SIGNAL DETECTION
            # (camera opens but stream is dead/too slow)
            # --------------------------

            if (
                now - self._started_at > 6
                and
                self._camera_fps < 2
            ):

                preview = self._build_preview(
                    frame,
                    default_result(
                        STATUS_CAMERA_UNAVAILABLE,
                        "Camera unavailable (no signal)"
                    )
                )

                self._publish({
                    **default_result(
                        STATUS_CAMERA_UNAVAILABLE,
                        "Camera unavailable (no signal)"
                    ),
                    "preview_rgb": preview,
                    "fps": self._camera_fps
                })

                time.sleep(0.2)

                continue

            # --------------------------
            # MIRROR (selfie view)
            # --------------------------

            frame = cv2.flip(frame, 1)

            # --------------------------
            # MEDIAPIPE
            # --------------------------

            hand = None

            if self.tracking_available:

                try:

                    rgb = cv2.cvtColor(
                        frame,
                        cv2.COLOR_BGR2RGB
                    )

                    processed = self.hands.process(rgb)

                    if processed.multi_hand_landmarks:

                        hand = (
                            processed.multi_hand_landmarks[0]
                        )

                except Exception:

                    hand = None

            # --------------------------
            # RESULT
            # --------------------------

            if not self.tracking_available:

                result = default_result(
                    STATUS_TRACKING_UNAVAILABLE,
                    "Hand tracking unavailable"
                )

            else:

                result = default_result(
                    STATUS_OK,
                    "Live camera feed"
                )

            result["fps"] = self._camera_fps

            swipe = None
            pinch = False
            fist_edge = False
            open_edge = False
            fingers = 0
            tracking = hand is not None

            if hand is not None:

                lm = hand.landmark

                # --------------------------
                # DRAW LANDMARKS
                # --------------------------

                try:

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

                except Exception:

                    pass

                # --------------------------
                # SWIPE
                # --------------------------

                swipe = self.swipe_detector.feed(
                    lm[9].x,
                    lm[9].y,
                    now
                )

                # --------------------------
                # FINGERS
                # --------------------------

                fingers = self._count_fingers(lm)

                # --------------------------
                # PINCH (level: turbo while held)
                # --------------------------

                pinch = (
                    self._distance(lm[4], lm[8]) < 0.055
                )

                # --------------------------
                # FIST / PALM (edge + cooldown)
                # --------------------------

                fist = fingers <= 1 and not pinch
                palm = fingers >= 4

                if (
                    fist
                    and not self.last_fist
                    and now - self.last_toggle_time >= self.toggle_cooldown
                ):

                    fist_edge = True
                    self.last_toggle_time = now

                if (
                    palm
                    and not self.last_open
                    and now - self.last_toggle_time >= self.toggle_cooldown
                ):

                    open_edge = True
                    self.last_toggle_time = now

                self.last_fist = fist
                self.last_open = palm

            else:

                self.swipe_detector.clear()
                self.last_fist = False
                self.last_open = False

            result["tracking"] = tracking
            result["swipe"] = swipe
            result["pinch"] = pinch
            result["fist_edge"] = fist_edge
            result["open_edge"] = open_edge
            result["fingers"] = fingers
            result["confidence"] = 100 if tracking else 0

            result["preview_rgb"] = self._build_preview(
                frame,
                result
            )

            self._publish(result)

        # end while

        if not got_frame:

            self._publish(
                default_result(
                    STATUS_CAMERA_UNAVAILABLE,
                    "Camera unavailable"
                )
            )

    # =====================================================
    # PREVIEW
    # =====================================================

    def _build_preview(self, frame, result):

        try:

            height, width = frame.shape[:2]

            cv2.rectangle(
                frame,
                (0, 0),
                (width, 44),
                (5, 10, 5),
                -1
            )

            status = result.get("status")

            if status == STATUS_CAMERA_UNAVAILABLE:

                banner = "CAMERA UNAVAILABLE"

            elif status == STATUS_TRACKING_UNAVAILABLE:

                banner = "LIVE  |  HAND TRACKING UNAVAILABLE"

            elif result.get("tracking"):

                banner = "LIVE  |  HAND DETECTED"

            else:

                banner = "LIVE  |  SHOW YOUR HAND"

            cv2.putText(
                frame,
                banner,
                (10, 29),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (215, 255, 60),
                2,
                cv2.LINE_AA
            )

            if status == STATUS_OK:

                if result.get("swipe"):

                    gesture_text = "SWIPE " + result["swipe"]

                elif result.get("pinch"):

                    gesture_text = "PINCH  |  TURBO"

                elif result.get("tracking"):

                    gesture_text = (
                        f"HAND  |  {result.get('fingers', 0)} FINGERS"
                    )

                else:

                    gesture_text = "READY"

                cv2.putText(
                    frame,
                    gesture_text,
                    (10, 74),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (230, 240, 190),
                    2,
                    cv2.LINE_AA
                )

            # Downscale for the Pygame panel

            frame = cv2.resize(
                frame,
                (480, 360),
                interpolation=cv2.INTER_AREA
            )

            return cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

        except Exception:

            return None

    # =====================================================
    # PUBLISH / READ
    # =====================================================

    def _publish(self, result):

        with self._lock:

            self._result = result

    def get_result(self):

        with self._lock:

            return dict(self._result)

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _distance(a, b):

        return float(
            np.sqrt(
                (a.x - b.x) ** 2
                +
                (a.y - b.y) ** 2
            )
        )

    @staticmethod
    def _count_fingers(lm):

        count = 0

        if lm[8].y < lm[6].y:
            count += 1
        if lm[12].y < lm[10].y:
            count += 1
        if lm[16].y < lm[14].y:
            count += 1
        if lm[20].y < lm[18].y:
            count += 1

        thumb = HandTracker._distance(lm[4], lm[5])
        reference = HandTracker._distance(lm[4], lm[17])

        if thumb > reference * 0.65:
            count += 1

        return count

    # =====================================================
    # COMPATIBILITY
    # =====================================================

    def update(self):

        return self.get_result()

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        self._running = False

        try:

            self._thread.join(timeout=2.0)

        except Exception:

            pass

        if self.hands is not None:

            try:

                self.hands.close()

            except Exception:

                pass

        try:

            self.cap.release()

        except Exception:

            pass
