import sys
import cv2
import threading
from detect import FireDetector
from delivery import delivery

from flask import Flask, render_template
from flask import request
from flask import Response

background_image = cv2.imread('bg.jpg', cv2.IMREAD_COLOR)

# 반복 완료 변수
done = False
app = Flask(__name__)

# 카메라 연결 / 화재 인식 객체
camera0 = FireDetector(2, 0) 
camera1 = FireDetector(1, 1)
camera2 = FireDetector(0, 2)
camera3 = FireDetector(3, 3)

@app.route('/')
def index():
    # 카메라 번호
    cam_id = request.args.get("camid")
    
    # cam_id값이 설정되지 않았을 떄 기본 카메라 ID인 0으로 설정
    if cam_id == None:
        cam_id = 0

    return render_template('index.html', cam_id=cam_id, floor1cam=camera0, floor2cam=camera1, floor3cam=camera2, floor4cam=camera3)

# 영상 스트림 URL
@app.route('/video/<int:camera_id>')
def video(camera_id):
    return Response(webviewer.gen_frames(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

class WebServer:
    """
    여러 카메라의 영상 실시간 송출을 위한 클래스

    Args:
        cam0 (FireDetector): 화재 감지 객체 0

        cam1 (FireDetector): 화재 감지 객체 1
        
        cam2 (FireDetector): 화재 감지 객체 2
        
        cam3 (FireDetector): 화재 감지 객체 3
    
    """
    def __init__(self, cam0, cam1, cam2, cam3):
        self.camList = [cam0, cam1, cam2, cam3]

    def gen_frames(self, id):
        """
        영상을 웹으로 스트리밍 하기 위한 함수
        """
        while True:
            frame = self.camList[id].resultFrame # frame에 카메라 화면 받아오기
            ret, buffer = cv2.imencode('.jpg', frame) # buffer에 JPG 형식으로 저장
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # 화면 데이터를 전송

    def run(self):
        app.run(host='0.0.0.0', port=80, debug=False)

# 웹 카메라 뷰어 객체
webviewer = WebServer(camera0, camera1, camera2, camera3)

# 화재 인식 코드를 병렬로 실행
t0 = threading.Thread(target=camera0.detect)
t1 = threading.Thread(target=camera1.detect)
t2 = threading.Thread(target=camera2.detect)    
t3 = threading.Thread(target=camera3.detect)

# 데이터 전송, 카메라 웹뷰어 병렬처리
delivery_thread = threading.Thread(target=delivery, args=(camera0, camera1, camera2, camera3))
viewer_thread = threading.Thread(target=webviewer.run)

t0.daemon = True
t1.daemon = True
t2.daemon = True
t3.daemon = True

delivery_thread.daemon = True
viewer_thread.daemon = True

# 병렬 처리 시작
t0.start()
t1.start()
t2.start()
t3.start()

delivery_thread.start()
viewer_thread.start()

# 크기 변경 가능한 창 생성
cv2.namedWindow("Object Detection", cv2.WINDOW_NORMAL)

# 창 내부 표시
while not done:
    try:
        # 모든 카메라가 준비가 되었을 때
        if all([camera0.isReady, camera1.isReady, camera2.isReady, camera3.isReady]):
            visual_frame = background_image
            # 모든 카메라를 한 화면에 합치기
            result_frame = cv2.vconcat([cv2.hconcat([camera0.resultFrame, camera1.resultFrame]),
                                        cv2.hconcat([camera2.resultFrame, camera3.resultFrame])])
            visual_frame[469:1469, 690:2023] = cv2.resize(result_frame, (1333, 1000))
            cv2.imshow("Object Detection", visual_frame)

        if cv2.waitKey(1) == ord("q"):
            done = True
    except KeyboardInterrupt:
        done = True

# 카메라 사용 해제
camera0.release_camera()
camera1.release_camera()
camera2.release_camera()
camera3.release_camera()

# 프로그램 종료
cv2.destroyAllWindows()
sys.exit(0)