import os, sys
import crypto
sys.modules['Crypto'] = crypto
import cv2
from ultralytics import YOLO
import numpy as np
import time
import serial
import pyrebase
import threading
from dotenv import load_dotenv

## Initial Settings
load_dotenv(verbose=True)

# 시리얼 포트 설정
ser = serial.Serial(port='COM4', baudrate=115200)

model = YOLO('best.pt')

## Firebase
config = {
    "apiKey": os.getenv('FIREBASE_APIKEY'),
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN'),
    "databaseURL": os.getenv('FIREBASE_DBURL'),
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET')
}

iot_status: dict[str, str] = {}
def iot_stream_handler(message):
    global iot_status
    iot_status = message['data']
    print(message['data'])

firebase = pyrebase.initialize_app(config)
db = firebase.database()
iot_stream = db.child('light').stream(iot_stream_handler)

## Loop
done = False

detected_people: list[int] = [ 0, 0, 0, 0 ]
fire: list[bool] = [ False, False, False, False ]
detect_ready: list[bool] = [ False, False, False, False ]
result_frames = [ None, None, None, None ]

def detect(index, changed_index) -> None:
    cap = cv2.VideoCapture(index)

    while not done:
        success, frame = cap.read()

        if success:
            results = model.predict(frame, half=True, device='cpu', verbose=False)
            result_frame = frame

            person_count = 0

            for result in results:
                boxes = result.boxes

                for box in boxes:
                    color: tuple[int, int, int] = (0, 255, 0) if box.cls == 0 else (0, 0, 255)
                    # box.xyxy, box.cls는 tensor
                    position = list(map(int, box.xyxy.tolist()[0])) # 출력값은 float인데 int로 변환
                    # Class ID
                    # 0: Fire
                    # 1: Person
                    detect_class_id = int(box.cls.tolist()[0])
                    detect_class_label: str = 'person' if detect_class_id == 1 else 'fire'

                    if detect_class_id == 0: # On fire detected
                        fire[changed_index] = True

                    if detect_class_id == 1: # On person detected
                        person_count += 1

                    result_frame = cv2.rectangle(result_frame, (position[0], position[1]), (position[2], position[3]), color, 2)

                    result_frame = cv2.putText(result_frame, detect_class_label, (position[0], position[1]), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255 ,255), 1, cv2.LINE_AA)

            result_frame = cv2.putText(result_frame, f"{changed_index+1}Floor", (0, 50), cv2.FONT_HERSHEY_DUPLEX, 2, (255, 255, 0), 2, cv2.LINE_AA)

            detect_ready[changed_index] = True
            detected_people[changed_index] = person_count
            result_frames[-changed_index] = result_frame
    
    cap.release()

def sendSerial() -> None:
    while not done:
        fire_floor = fire.index(True) + 1
        
        if fire_floor > 0:
            print(f"FireAt:{fire_floor}")
            ser.write(f'FireAt:{fire_floor}\n'.encode())
        if fire_floor == 0:
            ser.write(f'FireAt:-1\n'.encode())

        if sum(detected_people) == 0:
            print('EcoMode:1')
            ser.write('EcoMode:1\n'.encode())
        else:
            print('EcoMode:0')
            ser.write('EcoMode:0\n'.encode())

t0 = threading.Thread(target=detect, args=(3, 2))
t1 = threading.Thread(target=detect, args=(2, 0))
t2 = threading.Thread(target=detect, args=(1, 1))
t3 = threading.Thread(target=detect, args=(0, 3))

serial_thread = threading.Thread(target=sendSerial)

t0.daemon = True
t1.daemon = True
t2.daemon = True
t3.daemon = True

t0.start()
t1.start()
t2.start()
t3.start()

for i in range(10, 0, -1):
    print(f"{i}... ", end='')
    time.sleep(1)

cv2.namedWindow("Object Detection", cv2.WINDOW_NORMAL)

while not done:
    try:
        if all(detect_ready):
            visual_frame = cv2.vconcat([cv2.hconcat(result_frames[:2]), cv2.hconcat(result_frames[2:])])
            cv2.imshow("Object Detection", visual_frame)

        if cv2.waitKey(1) == ord("q"):
            done = True
    except KeyboardInterrupt:
        done = True

ser.close()
cv2.destroyAllWindows()