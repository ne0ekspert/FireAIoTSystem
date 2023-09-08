import os, sys
import crypto
sys.modules['Crypto'] = crypto
import cv2
from ultralytics import YOLO
from gtts import gTTS
from playsound import playsound
import time, datetime
import serial
import pyrebase
import threading
import requests
import json
from dotenv import load_dotenv

## Initial Settings
load_dotenv(verbose=True)

model = YOLO('best.onnx')

background_image = cv2.imread('bg.jpg')

## Firebase
## IoT 제어용으로 사용
config = {
    "apiKey": os.getenv('FIREBASE_APIKEY') or '',
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN') or '',
    "databaseURL": os.getenv('FIREBASE_DBURL') or '',
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET') or ''
}

## Loop
done = False

detected_people: list[int] = [ 0, 0, 0, 0 ]
fire: list[bool] = [ False, False, False, False ]
detect_ready: list[bool] = [ False, False, False, False ]
result_frames = [ None, None, None, None ]

time.sleep(1)

def detect(index, changed_index) -> None:
    cap = cv2.VideoCapture(index)

    while not done:
        success, frame = cap.read()

        if success:
            detect_start_time = time.time()
            try:
                results = model.predict(frame, half=True, device='cpu', verbose=False)
            except:
                continue
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

                    if position[0] > 400:
                        continue

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

            #`MNprint(f"{index}: Detection Time: {time.time()-detect_start_time}")
    
    cap.release()

def fetch(url, message):
    def webhookData(message: str):
        return json.dumps({
            "username": "Fire Alert",
            "content": message,
            "text": message
        })
    
    res = requests.post(url, webhookData(message), headers={
        'Content-Type': 'application/json'
    })
    
    if res.ok:
        print("Webhook sent")
    else:
        print(res.status_code)

def delivery() -> None:
    # 시리얼 포트 설정
    ser = serial.Serial(port=os.getenv('SERIAL_PORT'), baudrate=9600, timeout=0)
    datetime_object = datetime.datetime.fromtimestamp(time.time())

    WEBHOOK_URL = os.getenv('WEBHOOK_URL') or ''
    WEBHOOK_REFRESH_DELAY = float(os.getenv('WEBHOOK_REFRESH_DELAY') or 5.0)
    OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

    LCD_REFRESH_DELAY = float(os.getenv('LCD_REFRESH_DELAY') or 5.0)
    ALERT_REFRESH_DELAY = float(os.getenv('ALERT_REFRESH_DELAY') or 5.0)
    WEATHER_REFRESH_DELAY = float(os.getenv('WEATHER_REFRESH_DELAY') or 600.0)

    last_sent_timestamp = time.time() - LCD_REFRESH_DELAY
    last_alert_timestamp = time.time() - ALERT_REFRESH_DELAY
    last_weather_timestamp = time.time() - WEATHER_REFRESH_DELAY

    ser.write(f"Time:{int((datetime_object - datetime.datetime(1970, 1, 1)).total_seconds())}\n".encode())

    folder = 'res'

    iot_status: dict[str, str] = {
        'LED1': 'false',
        'LED2': 'false',
        'LED3': 'false',
        'LED4': 'false'
    }
    def iot_stream_handler(message):
        ser.flush()
        path = message['path'][1:]
        if len(path) == 0:
            pass
        else:
            iot_status[path] = message['data']

        ser.write(f"CtrlIoT:".encode())
        print(f"[{time.time()}] CtrlIoT")
        ser.write(''.join('1' if iot_status[f'LED{i+1}'] == 'true' else '0' for i in range(4)).encode())
        print(f"[{time.time()}] {'1' if iot_status[f'LED{i+1}'] == 'true' else '0'}")
        ser.write('\n'.encode())
        
        print(iot_status)
        print(message)

    firebase = pyrebase.initialize_app(config)
    db = firebase.database()
    iot_stream = db.child('light').stream(iot_stream_handler)

    if not os.path.exists(folder):
        os.makedirs(folder)

    while not done:
        fire_floor = []
        for i in range(len(fire)):
            if fire[i]:
                fire_floor.append(str(i+1))

        if sum(detected_people) == 0:
            ser.write('EcoMode:1\n'.encode())
            print(f"[{time.time()}] EcoMode:1")
        else:
            ser.write('EcoMode:0\n'.encode())
            print(f"[{time.time()}] EcoMode:0")

        if len(fire_floor) > 0:
            ser.write(f"FireAt:{','.join(fire_floor)}\n".encode())

            message = f"Fire detected on floor {', '.join(fire_floor)}"
            if last_sent_timestamp + WEBHOOK_REFRESH_DELAY <= time.time():
                fetch(WEBHOOK_URL, message)
                last_sent_timestamp = time.time()

            if last_alert_timestamp + ALERT_REFRESH_DELAY <= time.time():
                text = f"{'층, '.join(fire_floor)}층에 화재가 감지되었습니다."
                filename = f"fireat_{''.join(fire_floor)}.mp3"
                filepath = os.path.join(folder, filename)

                if not os.path.exists(filepath):
                    tts = gTTS(text=text, lang='ko')
                    tts.save(filepath)
                    print(f"WAV file '{filename}' generated successfully.")
                else:
                    print(f"WAV file '{filename}' already exists.")
                
                playsound(filepath, block=False)
                last_alert_timestamp = time.time()

            if last_weather_timestamp + WEATHER_REFRESH_DELAY <= time.time():
                res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={OPENWEATHERMAP_LAT}&lon={OPENWEATHERMAP_LONG}&appid={OPENWEATHERMAP_API_KEY}&units=metric")
                weather = res.json()
                print(weather)
                ser.write(f"Weather:{weather['weather'][0]['main']}\n".encode())
                ser.write(f"Temp:{weather['main']['temp']}\n".encode())
                last_weather_timestamp = time.time()

            print(f"[{time.time()}] FireAt:{','.join(fire_floor)}")
        else:
            ser.write('FireAt:0\n'.encode())
            print(f"[{time.time()}] FireAt:0")
    
        time.sleep(LCD_REFRESH_DELAY)

    ser.close()

t0 = threading.Thread(target=detect, args=(3, 0))
t1 = threading.Thread(target=detect, args=(2, 3))
t2 = threading.Thread(target=detect, args=(1, 2))
t3 = threading.Thread(target=detect, args=(0, 1))

delivery_thread = threading.Thread(target=delivery)

t0.daemon = True
t1.daemon = True
t2.daemon = True
t3.daemon = True

delivery_thread.daemon = True

t0.start()
t1.start()
t2.start()
t3.start()

delivery_thread.start()

cv2.namedWindow("Object Detection", cv2.WINDOW_NORMAL)

while not done:
    try:
        if all(detect_ready):
            visual_frame = background_image
            result_frame = cv2.vconcat([cv2.hconcat(result_frames[:2]), cv2.hconcat(result_frames[2:])])
            visual_frame[469:1469, 690:2023] = cv2.resize(result_frame, (1333, 1000))
            cv2.imshow("Object Detection", visual_frame)

        if cv2.waitKey(1) == ord("q"):
            done = True
    except KeyboardInterrupt:
        done = True

cv2.destroyAllWindows()
sys.exit(0)