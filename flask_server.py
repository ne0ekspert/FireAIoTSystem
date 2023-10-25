import cv2
import flask
from flask import Flask, render_template
from flask import request
from flask import Response

app = Flask(__name__)

@app.route('/')
def index():
    cam_id = request.args.get("camid")

    return render_template('index.html', cam_id=cam_id)

@app.route('/video/<int:camera_id>')
def video(camera_id):
    return Response(webviewer.gen_frames(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

class WebServer:
    """
    여러 카메라의 영상 스트리밍을 위한 클래스

    Args:
        cam0 (FireDetector): 화재 감지 객체 0
        cam1 (FireDetector): 화재 감지 객체 1
        cam2 (FireDetector): 화재 감지 객체 2
        cam3 (FireDetector): 화재 감지 객체 3
    """
    def __init__(self, cam0, cam1, cam2, cam3):
        self.camList = [cam0, cam1, cam2, cam3]

    def gen_frames(self, id):
        while True:
            success, frame = self.camList[id].resultFrame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

    def run(self):
        app.run(debug=True)

if __name__ == "__main__":
    webviewer = WebServer()
    webviewer.run()