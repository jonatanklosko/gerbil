from flask import Flask, render_template, Response
from imutils.video import VideoStream
import cv2
import time

app = Flask(__name__)

@app.route("/")
def index():
  return Response(get_video_feed(), mimetype="multipart/x-mixed-replace; boundary=frame")

def get_video_feed():
  video_stream = VideoStream(usePiCamera=True, resolution=(640, 480)).start()
  # Allow the camera to warmup
  time.sleep(1)

  while True:
    frame = video_stream.read()
    _, encoded_frame = cv2.imencode(".jpeg", frame)
    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + bytes(encoded_frame) + b"\r\n\r\n")
