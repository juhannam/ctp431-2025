"""
MediaPipe FaceMesh -> OSC sender

Webcam + MediaPipe FaceMesh to estimate mouth width/height and send:
- /gesture/mouth/width
- /gesture/mouth/height

Landmarks are visualized on the preview window. Press 'q' to quit.

Note: This example demonstrates face landmarks only. For pose and hand landmark implementations, see:
- Pose Landmarker: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
- Hand Landmarker: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
"""

import argparse
import time
from typing import Optional, Tuple

import cv2
import math
from pythonosc.udp_client import SimpleUDPClient

try:
    import mediapipe as mp
except Exception as exc:
    raise RuntimeError(
        "Failed to import mediapipe. Please install mediapipe first."
    ) from exc

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# FaceMesh landmark indices (468-point topology)
# Reference for indices: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
# Mouth corners and lips
LMK_MOUTH_LEFT = 61
LMK_MOUTH_RIGHT = 291
LMK_UPPER_LIP = 13
LMK_LOWER_LIP = 14
# Reference cheek points for approximate face width normalization
LMK_CHEEK_LEFT = 234
LMK_CHEEK_RIGHT = 454


# Fixed mapping ranges (empirical defaults)
WIDTH_MIN_RATIO = 0.35
WIDTH_MAX_RATIO = 0.65
HEIGHT_MIN_RATIO = 0.05
HEIGHT_MAX_RATIO = 0.65


def euclidean_distance(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    dx = float(a[0] - b[0])
    dy = float(a[1] - b[1])
    return float(math.hypot(dx, dy))


def map_to_range(value: float, vmin: float, vmax: float, out_min: float, out_max: float) -> float:
    if vmax <= vmin:
        return out_min
    t = (value - vmin) / (vmax - vmin)
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return out_min + t * (out_max - out_min)


def extract_landmark_xy(
    landmarks, index: int, img_w: int, img_h: int
) -> Tuple[int, int]:
    l = landmarks[index]
    return int(l.x * img_w), int(l.y * img_h)


def compute_mouth_metrics(
    landmarks, img_w: int, img_h: int
) -> Tuple[float, float]:
    """
    Returns:
        (mouth_width_ratio, mouth_height_ratio) normalized by approximate face width
    """
    p_left = extract_landmark_xy(landmarks, LMK_MOUTH_LEFT, img_w, img_h)
    p_right = extract_landmark_xy(landmarks, LMK_MOUTH_RIGHT, img_w, img_h)
    p_upper = extract_landmark_xy(landmarks, LMK_UPPER_LIP, img_w, img_h)
    p_lower = extract_landmark_xy(landmarks, LMK_LOWER_LIP, img_w, img_h)
    p_cheek_l = extract_landmark_xy(landmarks, LMK_CHEEK_LEFT, img_w, img_h)
    p_cheek_r = extract_landmark_xy(landmarks, LMK_CHEEK_RIGHT, img_w, img_h)

    mouth_width_px = euclidean_distance(p_left, p_right)
    mouth_height_px = euclidean_distance(p_upper, p_lower)
    face_width_px = max(1.0, euclidean_distance(p_cheek_l, p_cheek_r))

    width_ratio = mouth_width_px / face_width_px
    height_ratio = mouth_height_px / face_width_px
    return width_ratio, height_ratio


def draw_landmarks(frame, face_landmarks, lms, img_w: int, img_h: int):
    # Draw full facemesh (tesselation + contours)
    mp_drawing.draw_landmarks(
        image=frame,
        landmark_list=face_landmarks,
        connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
        landmark_drawing_spec=None,
        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style(),
    )
    mp_drawing.draw_landmarks(
        image=frame,
        landmark_list=face_landmarks,
        connections=mp.solutions.face_mesh.FACEMESH_CONTOURS,
        landmark_drawing_spec=None,
        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style(),
    )

    # Highlight mouth landmarks
    mouth_indices = [LMK_MOUTH_LEFT, LMK_MOUTH_RIGHT, LMK_UPPER_LIP, LMK_LOWER_LIP]
    for idx in mouth_indices:
        x, y = extract_landmark_xy(lms, idx, img_w, img_h)
        cv2.circle(frame, (x, y), 3, (0, 255, 255), -1)


def main():
    parser = argparse.ArgumentParser(description="MediaPipe FaceMesh -> OSC (FaceOSC-compatible)")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="OSC target IP")
    parser.add_argument("--port", type=int, default=8338, help="OSC target port")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--width", type=int, default=1280, help="Capture width")
    parser.add_argument("--height", type=int, default=720, help="Capture height")
    parser.add_argument("--no-show", action="store_true", help="Disable preview window")
    parser.add_argument("--flip", action="store_true", help="Flip preview for mirror-like view")
    parser.add_argument("--detection", type=float, default=0.5, help="min_detection_confidence")
    parser.add_argument("--tracking", type=float, default=0.5, help="min_tracking_confidence")
    args = parser.parse_args()

    client = SimpleUDPClient(args.ip, args.port)
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=float(args.detection),
        min_tracking_confidence=float(args.tracking),
    )

    show = not args.no_show

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read from camera.")
                break

            if args.flip:
                frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            width_ratio: Optional[float] = None
            height_ratio: Optional[float] = None

            if results.multi_face_landmarks:
                h, w = frame.shape[:2]
                lms = results.multi_face_landmarks[0].landmark
                wr, hr = compute_mouth_metrics(lms, w, h)

                width_ratio = wr
                height_ratio = hr

                mapped_w = map_to_range(width_ratio, WIDTH_MIN_RATIO, WIDTH_MAX_RATIO, 10.0, 16.0)
                mapped_h = map_to_range(height_ratio, HEIGHT_MIN_RATIO, HEIGHT_MAX_RATIO, 5.0, 10.0)

                client.send_message("/gesture/mouth/width", float(mapped_w))
                client.send_message("/gesture/mouth/height", float(mapped_h))
                if show:
                    draw_landmarks(frame, results.multi_face_landmarks[0], lms, w, h)
                    cv2.putText(frame, f"width: {mapped_w:.2f}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(frame, f"height: {mapped_h:.2f}", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

            if show:
                cv2.imshow("MediaPipe FaceMesh -> OSC", frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    break

            else:
                # Headless mode: still allow clean exit with Ctrl+C
                time.sleep(0.001)

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()


