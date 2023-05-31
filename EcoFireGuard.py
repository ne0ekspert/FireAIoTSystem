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

LCD_REFRESH_DELAY = float(os.getenv('LCD_REFRESH_DELAY'))

# 시리얼 포트 설정
ser = serial.Serial(port=os.getenv('SERIAL_PORT'), baudrate=115200)

model = YOLO('best.pt')

## Firebase
config = {
    "apiKey": os.getenv('FIREBASE_APIKEY'),
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN'),
    "databaseURL": os.getenv('FIREBASE_DBURL'),
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET')
}

iot_status: dict[str, str] = {
    'LED1': 'false',
    'LED2': 'false',
    'LED3': 'false',
    'LED4': 'false',
    'MOTOR1': 'false',
    'MOTOR2': 'false'
}
def iot_stream_handler(message):
    global iot_status
    path = message['path'][1:]
    iot_status[path] = message['data']
    print(message)

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

            detected_objects = {
                'fire': 0,
                'person': 0
            }

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
                        detected_objects['fire'] += 1

                    if detect_class_id == 1: # On person detected
                        detected_objects['person'] += 1

                    result_frame = cv2.rectangle(result_frame, (position[0], position[1]), (position[2], position[3]), color, 2)

                    result_frame = cv2.putText(result_frame, detect_class_label, (position[0], position[1]), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255 ,255), 1, cv2.LINE_AA)

            result_frame = cv2.putText(result_frame, f"{changed_index+1}Floor", (0, 50), cv2.FONT_HERSHEY_DUPLEX, 2, (255, 255, 0), 2, cv2.LINE_AA)

            detect_ready[changed_index] = True
            detected_people[changed_index] = detected_objects['person']
            fire[changed_index] = True if detected_objects['fire'] > 0 else False
            result_frames[-changed_index-1] = result_frame
    
    cap.release()
    return 

def sendSerial() -> None:
    while not done:
        try:
            fire_floor = []
            for i in range(len(fire)):
                if fire[i]:
                    fire_floor.append(str(i+1))
            
            if len(fire_floor) > 0:
                print(f"FireAt:{','.join(fire_floor)}")
                ser.write(f"FireAt:{','.join(fire_floor)}\n".encode())
        except:
            ser.write(f'FireAt:-1\n'.encode())

        if sum(detected_people) == 0:
            print('EcoMode:1')
            ser.write('EcoMode:1\n'.encode())
        else:
            print('EcoMode:0')
            ser.write('EcoMode:0\n'.encode())

        ser.write(f"CtrlIoT:0{iot_status['LED1']}".encode())
        ser.write(f"CtrlIoT:1{iot_status['LED2']}".encode())
        ser.write(f"CtrlIoT:2{iot_status['LED3']}".encode())
        ser.write(f"CtrlIoT:3{iot_status['LED4']}".encode())

        ser.write(f"CtrlIoT:X{iot_status['MOTOR1']}".encode())
        ser.write(f"CtrlIoT:Y{iot_status['MOTOR2']}".encode())

        time.sleep(LCD_REFRESH_DELAY)

    ser.close()
    return

t0 = threading.Thread(target=detect, args=(3, 0))
t1 = threading.Thread(target=detect, args=(2, 2))
t2 = threading.Thread(target=detect, args=(1, 3))
t3 = threading.Thread(target=detect, args=(0, 1))

serial_thread = threading.Thread(target=sendSerial)

t0.daemon = True
t1.daemon = True
t2.daemon = True
t3.daemon = True

serial_thread.daemon = True

t0.start()
t1.start()
t2.start()
t3.start()

serial_thread.start()

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

cv2.destroyAllWindows()