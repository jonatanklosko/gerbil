from flask import Flask, render_template, Response
from imutils.video import VideoStream
import cv2
import numpy as np
import time
import os
import struct

app = Flask(__name__)

state = {
    "primary_pressed": False,
    "secondary_pressed": False,
    "cursor_x": 0,
    "cursor_y": 0
}

def buttons_byte(primary_pressed, secondary_pressed):
    primary_mask = int(primary_pressed)
    secondary_mask = int(secondary_pressed) << 1
    return primary_mask | secondary_mask

def state_to_report(state):
    buttons = buttons_byte(state["primary_pressed"], state["secondary_pressed"])
    return struct.pack("<BHH", buttons, state["cursor_x"], state["cursor_y"])

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

    if contour is None or cv2.contourArea(contour) < 1000:
        return preview

    # Compute convex hull surrounding the largest contour
    convex_hull = cv2.convexHull(contour)

    top_point, right_point, bottom_point, left_point = convex_hull_extreme_points(convex_hull)
    thumb_shown = is_thumb_shown(top_point, right_point, bottom_point, left_point)
    pinky_shown = is_pinky_shown(top_point, right_point, bottom_point, left_point)

    # Handle gestures

    if not state["primary_pressed"] and thumb_shown:
        state["primary_pressed"] = True
    elif state["primary_pressed"] and not thumb_shown:
        state["primary_pressed"] = False

    if not state["secondary_pressed"] and pinky_shown:
        state["secondary_pressed"] = True
    elif state["secondary_pressed"] and not pinky_shown:
        state["secondary_pressed"] = False

    # Handle cursor

    frame_height, frame_width = frame.shape
    screen_width, screen_height = (32767, 32767)

    # Take the topmost hand point as our pointer.
    pointer_x, pointer_y = top_point

    # Limit the pointer movement to a smaller window.
    pointer_window_tl = np.array([50, 50])
    pointer_window_br = np.array([350, 350])
    pointer_window_width, pointer_window_height = pointer_window_br - pointer_window_tl

    # Compute the pointer coordinates relatively to the pointer window.
    x = np.clip(pointer_x, pointer_window_tl[0], pointer_window_br[0]) - pointer_window_tl[0]
    y = np.clip(pointer_y, pointer_window_tl[1], pointer_window_br[1]) - pointer_window_tl[1]

    # Scale pointer position within its window onto cursor position on the screen.
    # Note that we mirror the x coordinate as the camera perceives horizontal
    # movement in the opposite direction.
    cursor_x = screen_width - int(x / pointer_window_width * screen_width)
    cursor_y = int(y / pointer_window_height * screen_height)

    current_cursor_x, current_cursor_y = state["cursor_x"], state["cursor_y"]

    delta_x = cursor_x - current_cursor_x
    delta_y = cursor_y - current_cursor_y
    distance = np.sqrt(delta_x ** 2 + delta_y ** 2)

    # For increased controllability we don't actually move directly to the computed position,
    # because this results in jumpy and inaccurate movement.
    # Instead we "slow down" the cursor depending on the virtual pixel distance,
    # so that long moves are relatively quick and short moves are slow hence more precise.
    if distance > 2000:
        cursor_x = current_cursor_x + int(delta_x / 2)
        cursor_y = current_cursor_y + int(delta_y / 2)
    elif distance > 1500:
        cursor_x = current_cursor_x + int(delta_x / 4)
        cursor_y = current_cursor_y + int(delta_y / 4)
    elif distance > 800:
        cursor_x = current_cursor_x + int(delta_x / 8)
        cursor_y = current_cursor_y + int(delta_y / 8)
    else:
        cursor_x = current_cursor_x
        cursor_y = current_cursor_y

    state["cursor_x"] = cursor_x
    state["cursor_y"] = cursor_y

    # TODO: send only if changed
    os.write(dev, state_to_report(state))

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

    if right_point[0] == top_point[0]:
        # So that we don't divide by 0
        return False

    # Calculate the angle between top-right line and the X axis.
    # A steep slope indicates that thumb is hidden, otherwise shown.
    tg = abs(right_point[1] - top_point[1]) / abs(right_point[0] - top_point[0])
    angle = np.arctan(tg)
    angle_deg = np.rad2deg(angle)

    return angle_deg < 50

def is_pinky_shown(top_point, right_point, bottom_point, left_point):
    """A heuristic checking whether the pinky is shown or hidden."""

    if left_point[0] == top_point[0]:
        # So that we don't divide by 0
        return False

    # Calculate the angle between top-left line and the X axis.
    # A steep slope indicates that pinky is hidden, otherwise shown.
    tg = abs(left_point[1] - top_point[1]) / abs(left_point[0] - top_point[0])
    angle = np.arctan(tg)
    angle_deg = np.rad2deg(angle)

    return angle_deg < 40
