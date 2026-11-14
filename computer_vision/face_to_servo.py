#!/usr/bin/env python3
"""
face_to_servo.py

Reads webcam, detects facial expression via MediaPipe + expression.detect_expression,
and sends a one-character command to the Arduino Mega driving the mouth servos.

Protocol: one ASCII character per line, '\n' terminated.
    N = neutral     H = happy     S = sad     A = anger     P = surprise

Requires in the same folder:
    expression.py           (your 5-way classifier)
    face_landmarker.task    (the MediaPipe model)

Dependencies:
    pip install mediapipe "opencv-python<5" pyserial

Controls (focus the preview window):
    q   quit
    r   reset "last sent" so the next detected expression resends
"""

import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from expression import detect_expression

# ---------------------------------------------------------------------------
# Config -- edit these to match your setup
# ---------------------------------------------------------------------------

SERIAL_PORT       = "/dev/cu.usbmodem11101"   # your Mega's current port
SERIAL_BAUD       = 115200
ARDUINO_BOOT_WAIT = 2.0                       # seconds to wait after opening the port
MIN_HOLD_MS       = 200                       # expression must hold this long before sending

# Flip to True to log every stage of every frame.  Leave False once things work.
DEBUG = True

EXPRESSION_TO_CHAR = {
    "neutral":  "N",
    "happy":    "H",
    "sad":      "S",
    "anger":    "A",
    "surprise": "P",
}

# ---------------------------------------------------------------------------
# Serial setup
# ---------------------------------------------------------------------------

ser = None
try:
    import serial
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0)
    print(f"[serial] Opened {SERIAL_PORT} @ {SERIAL_BAUD}. Waiting for Arduino reset...")
    time.sleep(ARDUINO_BOOT_WAIT)
    try:
        ser.reset_input_buffer()
    except Exception:
        pass
    print("[serial] Ready.")
except Exception as e:
    print(f"[serial] Could not open {SERIAL_PORT}: {e}")
    print("[serial] Running vision-only. Fix SERIAL_PORT to drive servos.")


def send_char(c):
    if ser is None:
        return False
    try:
        ser.write((c + "\n").encode())
        return True
    except Exception as e:
        print(f"[serial] Write error: {e}")
        return False


# ---------------------------------------------------------------------------
# MediaPipe setup
# ---------------------------------------------------------------------------

options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1,
    output_face_blendshapes=True,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    landmarker.close()
    raise RuntimeError("Could not open webcam.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

timestamp_ms  = 0
pending_expr  = None
pending_since = 0
last_sent     = None
frame_num     = 0

print("Face -> servo bridge running. Press Q to quit, R to force a resend.")

try:
    while True:
        if DEBUG:
            print(f"[dbg] top of loop frame_num={frame_num}")

        success, frame = camera.read()
        frame_num += 1
        if not success:
            if DEBUG:
                print("[dbg] camera.read() returned False -- exiting")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms += 33

        if DEBUG:
            print("[dbg] before mediapipe")
        result = landmarker.detect_for_video(mp_image, timestamp_ms)
        if DEBUG:
            print("[dbg] after mediapipe")

        expression = "neutral"
        if result.face_blendshapes:
            blendshapes = {bs.category_name: bs.score for bs in result.face_blendshapes[0]}
            expression  = detect_expression(blendshapes)

        # Debounce: an expression must hold for MIN_HOLD_MS before we send it.
        now_ms = int(time.time() * 1000)
        if expression != pending_expr:
            pending_expr  = expression
            pending_since = now_ms
        elif expression != last_sent and now_ms - pending_since >= MIN_HOLD_MS:
            c = EXPRESSION_TO_CHAR.get(expression)
            if c and send_char(c):
                last_sent = expression
                print(f"[send] {expression} -> {c}")

        # Overlay
        cv2.putText(frame, f"detected: {expression}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.putText(frame, f"sent:     {last_sent or '-'}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, "serial: " + ("ON" if ser else "OFF"),
                    (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 220, 0) if ser else (0, 0, 220), 1)

        if DEBUG:
            print("[dbg] before imshow")
        cv2.imshow("Face -> Servo Bridge", frame)
        if DEBUG:
            print("[dbg] before waitKey")
        key = cv2.waitKey(1) & 0xFF
        if DEBUG:
            print(f"[dbg] after waitKey key={key}")

        if key == ord("q"):
            break
        elif key == ord("r"):
            last_sent = None
            print("[send] forced resend on next detection")

finally:
    camera.release()
    cv2.destroyAllWindows()
    landmarker.close()
    if ser is not None:
        try:
            ser.close()
        except Exception:
            pass
