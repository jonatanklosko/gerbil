from flask import Flask, render_template, Response
import cv2
from gerbil import Gerbil

app = Flask(__name__)

gerbil = None

@app.before_first_request
def initialize():
    global gerbil
    gerbil = Gerbil()

@app.route("/")
def index():
    return Response(get_video_feed(), mimetype="multipart/x-mixed-replace; boundary=frame")

def get_video_feed():
    global gerbil

    while True:
        frame = gerbil.step(debug=True)
        if frame is not None:
            _, encoded_frame = cv2.imencode(".jpeg", frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + bytes(encoded_frame) + b"\r\n\r\n")
