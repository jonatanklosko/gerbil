from imutils.video import VideoStream
import cv2
import numpy as np
import time
import os
import os.path
import struct

class Gerbil:
    """
    Encapsulates the virtual cursor state, processing video feed
    from camera and sending HID reports to the USB host.
    """

    def __init__(self, hid_path="/dev/hidg0"):
        if not os.path.exists(hid_path):
            raise RuntimeError(f"no virtual device found under {hid_path}. Make sure to run bin/enable_mouse_hid_gadget.sh")

        self.dev = os.open(hid_path, os.O_WRONLY)

        self.video_stream = VideoStream(usePiCamera=True, resolution=(640, 480)).start()
        # Allow the camera to warmup
        time.sleep(1)

        self.state = {
            "primary_pressed": False,
            "secondary_pressed": False,
            "cursor_x": 0,
            "cursor_y": 0
        }

        self.last_report = None

    def stop(self):
        """Clean up resources"""

        self.video_stream.stop()

        # Send the last report with buttons state back to initial
        self.state["primary_pressed"] = False
        self.state["secondary_pressed"] = False
        self.__send_report()
        os.close(self.dev)

    def __send_report(self):
        report = self.__get_report()

        if report != self.last_report:
            os.write(self.dev, report)
            self.last_report = report

    def __get_report(self):
        primary_mask = int(self.state["primary_pressed"])
        secondary_mask = int(self.state["secondary_pressed"]) << 1
        buttons_byte = primary_mask | secondary_mask

        return struct.pack("<BHH", buttons_byte, self.state["cursor_x"], self.state["cursor_y"])

    def step(self, debug=False):
        """
        Reads the next frame from video stream, analyses it
        and sends new HID report to the USB host.

        ## Parameters

            `debug` - whether to return the processed frame. Defaults to `False`.
        """

        frame = self.video_stream.read()
        return self.__process_frame(frame, debug)

    def __process_frame(self, frame, debug=False):
        frame = frame[0:420, 0:420]

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
        kernel = np.ones((5, 5), np.uint8)
        frame = cv2.dilate(frame, kernel, iterations=1)
        elliptic_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE , (5, 5))
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

        if not self.state["primary_pressed"] and thumb_shown:
            self.state["primary_pressed"] = True
        elif self.state["primary_pressed"] and not thumb_shown:
            self.state["primary_pressed"] = False

        if not self.state["secondary_pressed"] and pinky_shown:
            self.state["secondary_pressed"] = True
        elif self.state["secondary_pressed"] and not pinky_shown:
            self.state["secondary_pressed"] = False

        # Handle cursor

        frame_height, frame_width = frame.shape
        screen_width, screen_height = (32767, 32767)

        # Take the topmost hand point as our pointer.
        pointer_x, pointer_y = top_point

        # Limit the pointer movement to a smaller window.
        pointer_window_tl = np.array([5, 5])
        pointer_window_br = np.array([320, 320])
        pointer_window_width, pointer_window_height = pointer_window_br - pointer_window_tl

        # Compute the pointer coordinates relatively to the pointer window.
        x = np.clip(pointer_x, pointer_window_tl[0], pointer_window_br[0]) - pointer_window_tl[0]
        y = np.clip(pointer_y, pointer_window_tl[1], pointer_window_br[1]) - pointer_window_tl[1]

        # Scale pointer position within its window onto cursor position on the screen.
        # Note that we mirror the x coordinate as the camera perceives horizontal
        # movement in the opposite direction.
        cursor_x = screen_width - int(x / pointer_window_width * screen_width)
        cursor_y = int(y / pointer_window_height * screen_height)

        current_cursor_x, current_cursor_y = self.state["cursor_x"], self.state["cursor_y"]

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

        self.state["cursor_x"] = cursor_x
        self.state["cursor_y"] = cursor_y

        self.__send_report()

        if debug:
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

    return angle_deg < 55

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
