import sys
import cv2
import threading
from dotenv import load_dotenv
from detect import FireDetector
from delivery import delivery
from flask_server import WebServer

## Initial Settings
load_dotenv(verbose=True)

background_image = cv2.imread('bg.jpg')

## Loop
done = False

# 카메라 / 화재 인식 객체
camera0 = FireDetector(3, 0)
camera1 = FireDetector(2, 3)
camera2 = FireDetector(1, 2)
camera3 = FireDetector(0, 1)

webviewer = WebServer(camera0, camera1, camera2, camera3)

# 화재 인식 스레드
t0 = threading.Thread(target=camera0.detect, args=(3, 0))
t1 = threading.Thread(target=camera1.detect, args=(2, 3))
t2 = threading.Thread(target=camera2.detect, args=(1, 2))
t3 = threading.Thread(target=camera3.detect, args=(0, 1))

delivery_thread = threading.Thread(target=delivery, args=(camera0, camera1, camera2, camera3))
viewer_thread = threading.Thread(target=webviewer.run)

t0.daemon = True
t1.daemon = True
t2.daemon = True
t3.daemon = True

delivery_thread.daemon = True

# 스레드 시작
t0.start()
t1.start()
t2.start()
t3.start()

delivery_thread.start()

# 창 생성
cv2.namedWindow("Object Detection", cv2.WINDOW_NORMAL)

while not done:
    try:
        if all([camera0.isReady, camera1.isReady, camera2.isReady, camera3.isReady]):
            visual_frame = background_image
            result_frame = cv2.vconcat([cv2.hconcat(camera0.resultFrame, camera1.resultFrame),
                                             cv2.hconcat(camera2.resultFrame, camera3.resultFrame)])
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