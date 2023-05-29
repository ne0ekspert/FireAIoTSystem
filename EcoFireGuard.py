import os
import cv2
from ultralytics import YOLO
import serial
import pyrebase
import threading
from dotenv import load_dotenv

## Initial Settings
load_dotenv(verbose=True)

config = {
    "apiKey": os.getenv('FIREBASE_APIKEY'),
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN'),
    "databaseURL": os.getenv('FIREBASE_DBURL'),
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET')
}

# 시리얼 포트 설정
#py_serial = serial.Serial(port='COM11', baudrate=9600)

model = YOLO('best.pt')

## Firebase
def iot_stream_handler(message):
    print(message['data'])

firebase = pyrebase.initialize_app(config)
db = firebase.database()
iot_stream = db.child('').stream(iot_stream_handler)

def detect(index):
    cap = cv2.VideoCapture(index)

    while True:
        success, frame = cap.read()

        if success:
            results = model.predict(frame, half=True)
            result_frame = frame

            for result in results:
                boxes = result.boxes
                probs = result.probs

                for box in boxes:
                    color = (0, 255, 0) if box.cls == 0 else (0, 0, 255)
                    # box.xyxy, box.cls는 tensor
                    position = list(map(int, box.xyxy.tolist()[0])) # 출력값은 float인데 int로 변환
                    detect_class_id = int(box.cls.tolist()[0])
                    detect_class_label = 'person' if detect_class_id == 1 else 'fire'

                    result_frame = cv2.rectangle(result_frame, (position[0], position[1]), (position[2], position[3]), color, 2)

                    result_frame = cv2.putText(frame, detect_class_label, (position[0], position[1]), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255 ,255))

            
                # 아두이노로 데이터 전송
                #py_serial.write(b'Fire detected\n')

while True:
    cv2.imshow("Object Detection", result_frame)

    if cv2.waitKey(1) == ord("q"):
        break

t0 = threading.Thread(target=detect, args=(0,))
t1 = threading.Thread(target=detect, args=(1,))
t2 = threading.Thread(target=detect, args=(2,))
t3 = threading.Thread(target=detect, args=(3,))

t0.start()
t1.start()
t2.start()
t3.start()

cv2.destroyAllWindows()