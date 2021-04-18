from flask import Flask, render_template, Response
from imutils.video import VideoStream
import cv2
import numpy as np
import time
import os

app = Flask(__name__)

state = {
    "primary_pressed": False,
    "secondary_pressed": False,
    "pointer": None
}

# TODO: wrap in some object responsible for sending clicks/coordinates
dev = os.open("/dev/hidg0", os.O_WRONLY)

@app.route("/")
def index():
    return Response(get_video_feed(), mimetype="multipart/x-mixed-replace; boundary=frame")

def get_video_feed():
    video_stream = VideoStream(usePiCamera=True, resolution=(640, 480)).start()
    # Allow the camera to warmup
    time.sleep(1)

    while True:
        frame = video_stream.read()
        frame = process_frame(frame)
        if frame is not None:
            _, encoded_frame = cv2.imencode(".jpeg", frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + bytes(encoded_frame) + b"\r\n\r\n")

def process_frame(frame):
    global state
    global dev

    frame = frame[0:400, 0:400]

    preview = frame.copy()

    # Create basic mask for ignoring areas with low lightness
    img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 0, 100], dtype=np.float32)
    upper = np.array([255, 255, 255], dtype=np.float32)
    color_mask = cv2.inRange(img_hsv, lower, upper)

    # Apply blur, so edge detection is less prone to camera noise
    frame = cv2.GaussianBlur(frame, (5, 5), 0)
    frame = cv2.Canny(frame, 30, 40)

    # Apply dilations followed by erosion to get more solid contour
    kernel = np.ones((3, 3), np.uint8)
    frame = cv2.dilate(frame, kernel, iterations=1)
    elliptic_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE , (3, 3))
    frame = cv2.morphologyEx(frame, cv2.MORPH_DILATE, elliptic_kernel)
    frame = cv2.erode(frame, kernel, iterations=1)

    # Now that we have binary image, apply the mask
    frame = cv2.bitwise_and(frame, frame, mask=color_mask)

    # Perform contour detection and find the one with maximum area
    contours, _ = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = max(contours, key=cv2.contourArea, default=None)

    if contour is None:
        return None

    # Compute convex hull surrounding the largest contour
    convex_hull = cv2.convexHull(contour)

    top_point, right_point, bottom_point, left_point = convex_hull_extreme_points(convex_hull)
    thumb_shown = is_thumb_shown(top_point, right_point, bottom_point, left_point)
    pinky_shown = is_pinky_shown(top_point, right_point, bottom_point, left_point)

    # Handle gestures

    if not state["primary_pressed"] and thumb_shown:
        os.write(dev, b"\x01\x00\x00")
        state["primary_pressed"] = True
    elif state["primary_pressed"] and not thumb_shown:
        os.write(dev, b"\x00\x00\x00")
        state["primary_pressed"] = False

    if not state["secondary_pressed"] and pinky_shown:
        os.write(dev, b"\x02\x00\x00")
        state["secondary_pressed"] = True
    elif state["secondary_pressed"] and not pinky_shown:
        os.write(dev, b"\x00\x00\x00")
        state["secondary_pressed"] = False

    # Draw the contour and convex hull for debugging
    cv2.drawContours(preview, [contour], -1, (255, 0, 0), 3)
    cv2.drawContours(preview, [convex_hull], -1, (0, 255, 255), 2)

    return preview

def convex_hull_extreme_points(convex_hull):
    """Returns top, right, bottom and left extreme points of the given convex hull."""

    # As noted earlier we need to unpack every point
    convex_hull_points = [point[0] for point in convex_hull]

    top_point = min(convex_hull_points, key=lambda point: point[1])
    bottom_point = max(convex_hull_points, key=lambda point: point[1])
    left_point = min(convex_hull_points, key=lambda point: point[0])
    right_point = max(convex_hull_points, key=lambda point: point[0])

    return top_point, right_point, bottom_point, left_point


def is_thumb_shown(top_point, right_point, bottom_point, left_point):
    """A heuristic checking whether the thumb is shown or hidden."""

    a = np.linalg.norm(top_point - right_point)
    b = np.linalg.norm(bottom_point - right_point)
    c = np.linalg.norm(top_point - bottom_point)

    if a == 0 or b == 0:
        # So that we don't divide by 0
        return False

    # Calculate the angle between top-to-right and bottom-to-right lines
    # Cosine law
    angle = np.arccos((a ** 2 + b ** 2 - c ** 2) / (2 * a * b))
    angle_deg = np.rad2deg(angle)

    return angle_deg < 120

def is_pinky_shown(top_point, right_point, bottom_point, left_point):
    """A heuristic checking whether the pinky is shown or hidden."""

    a = np.linalg.norm(top_point - left_point)
    b = np.linalg.norm(bottom_point - left_point)
    c = np.linalg.norm(top_point - bottom_point)

    if left_point[0] == top_point[0]:
        # So that we don't divide by 0
        return False

    # Calculate the angle between top-left line and the X axis.
    # A steep slope indicates that pinky is hidden, otherwise shown.
    tg = abs(left_point[1] - top_point[1]) / abs(left_point[0] - top_point[0])
    angle = np.arctan(tg)
    angle_deg = np.rad2deg(angle)

    return angle_deg < 40
