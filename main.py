import sys
import cv2
import threading
from detect import FireDetector
from delivery import delivery

from flask import Flask, render_template
from flask import request
from flask import Response

background_image = cv2.imread('bg.jpg', cv2.IMREAD_COLOR)

## Loop
done = False
app = Flask(__name__)

# 카메라 / 화재 인식 객체
camera0 = FireDetector(3, 0)
camera1 = FireDetector(2, 3)
camera2 = FireDetector(1, 2)
camera3 = FireDetector(0, 1)

@app.route('/')
def index():
    cam_id = request.args.get("camid")
    if cam_id == None:
        cam_id = 0

    return render_template('index.html', cam_id=cam_id, floor1cam=camera0, floor2cam=camera1, floor3cam=camera2, floor4cam=camera3)

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
            frame = self.camList[id].resultFrame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

    def run(self):
        app.run(host='0.0.0.0', port=80, debug=False)

webviewer = WebServer(camera0, camera1, camera2, camera3)

# 화재 인식 스레드
t0 = threading.Thread(target=camera0.detect)
t1 = threading.Thread(target=camera1.detect)
t2 = threading.Thread(target=camera2.detect)
t3 = threading.Thread(target=camera3.detect)

# 데이터 전송, 카메라 웹뷰어 스레드
delivery_thread = threading.Thread(target=delivery, args=(camera0, camera1, camera2, camera3))
viewer_thread = threading.Thread(target=webviewer.run)

t0.daemon = True
t1.daemon = True
t2.daemon = True
t3.daemon = True

delivery_thread.daemon = True
viewer_thread.daemon = True

# 스레드 시작
t0.start()
t1.start()
t2.start()
t3.start()

delivery_thread.start()
viewer_thread.start()

# 창 생성
cv2.namedWindow("Object Detection", cv2.WINDOW_NORMAL)

while not done:
    try:
        if all([camera0.isReady, camera1.isReady, camera2.isReady, camera3.isReady]):
            visual_frame = background_image
            result_frame = cv2.vconcat([cv2.hconcat([camera0.resultFrame, camera1.resultFrame]),
                                        cv2.hconcat([camera2.resultFrame, camera3.resultFrame])])
            visual_frame[469:1469, 690:2023] = cv2.resize(result_frame, (1333, 1000))
            cv2.imshow("Object Detection", visual_frame)

        if cv2.waitKey(1) == ord("q"):
            done = True
    except KeyboardInterrupt:
        done = True

camera0.release_camera()
camera1.release_camera()
camera2.release_camera()
camera3.release_camera()

cv2.destroyAllWindows()
sys.exit(0)