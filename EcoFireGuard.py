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
ser = serial.Serial(port='COM11', baudrate=9600)

model = YOLO('best.pt')

## Firebase
config = {
    "apiKey": os.getenv('FIREBASE_APIKEY'),
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN'),
    "databaseURL": os.getenv('FIREBASE_DBURL'),
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET')
}

def iot_stream_handler(message):
    print(message['data'])

firebase = pyrebase.initialize_app(config)
db = firebase.database()
iot_stream = db.child('').stream(iot_stream_handler)

## Loop
done = False

detected_people = [ 0, 0, 0, 0 ]
fire = [ False, False, False, False ]
detect_ready = [ False, False, False, False ]
result_frames = [ None, None, None, None ]

def detect(index, changed_index):
    cap = cv2.VideoCapture(index)

    while not done:
        success, frame = cap.read()

        if success:
            print(f"predict {index}")
            results = model.predict(frame, half=True, device='cpu')
            result_frame = frame

            person_count = 0

            for result in results:
                boxes = result.boxes

                for box in boxes:
                    color = (0, 255, 0) if box.cls == 0 else (0, 0, 255)
                    # box.xyxy, box.cls는 tensor
                    position = list(map(int, box.xyxy.tolist()[0])) # 출력값은 float인데 int로 변환
                    # Class ID
                    # 0: Fire
                    # 1: Person
                    detect_class_id = int(box.cls.tolist()[0])
                    detect_class_label = 'person' if detect_class_id == 1 else 'fire'

                    if detect_class_id == 1:
                        person_count += 1

                    result_frame = cv2.rectangle(result_frame, (position[0], position[1]), (position[2], position[3]), color, 2)

                    result_frame = cv2.putText(result_frame, detect_class_label, (position[0], position[1]), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255 ,255), 1, cv2.LINE_AA)

            result_frame = cv2.putText(result_frame, f"{changed_index+1}Floor", (0, 50), cv2.FONT_HERSHEY_DUPLEX, 2, (255, 255, 0), 2, cv2.LINE_AA)

            
                # 아두이노로 데이터 전송
                #py_serial.write(b'Fire detected\n')

            fire[changed_index] = True
    
            detect_ready[changed_index] = True
            detected_people[changed_index] = person_count
            result_frames[changed_index] = result_frame
    
    cap.release()

t0 = threading.Thread(target=detect, args=(0, 1))
t1 = threading.Thread(target=detect, args=(1, 3))
t2 = threading.Thread(target=detect, args=(2, 2))
t3 = threading.Thread(target=detect, args=(3, 0))

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

        try:
            fire_floor = fire.index(True) + 1
            if fire_floor > 0:
                ser.write(f'FireAt:{fire_floor}\n'.encode())
            if sum(detected_people) == 0:
                ser.write('EcoMode:1'.encode())
            else:
                ser.write('EcoMode:0'.encode())
        except:
            pass


        if cv2.waitKey(1) == ord("q"):
            done = True
    except KeyboardInterrupt:
        done = True

cv2.destroyAllWindows()