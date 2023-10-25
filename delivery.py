import os, time
import json
import serial
import datetime
#import crypto
#sys.modules['Crypto'] = crypto
import pyrebase
from gtts import gTTS
from playsound import playsound
import requests

# IoT 활용을 위한 Firebase 설정
# 보안을 위해 설정값은 .env파일에 저장
config = {
    "apiKey": os.getenv('FIREBASE_APIKEY') or '',
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN') or '',
    "databaseURL": os.getenv('FIREBASE_DBURL') or '',
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET') or ''
}
 
def fetch(url, message):
    """
    디스코드에 웹훅을 보내는 함수

    Args:
        url (str): 웹훅을 보낼 URL
        message (str): 웹훅에 보낼 메세지

    Returns:
        None
    """
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

def delivery(cam0, cam1, cam2, cam3) -> None:
    """
    각 데이터를 전송하는 함수

    Args:
        cam0 (FireDetector): 화재감지 객체 0
        cam1 (FireDetector): 화재감지 객체 1
        cam2 (FireDetector): 화재감지 객체 2
        cam3 (FireDetector): 화재감지 객체 3
    """
    ser = serial.Serial(port=os.getenv('SERIAL_PORT'), baudrate=9600, timeout=0)
    datetime_object = datetime.datetime.fromtimestamp(time.time())

    WEBHOOK_URL = os.getenv('WEBHOOK_URL') or ''
    WEBHOOK_REFRESH_DELAY = float(os.getenv('WEBHOOK_REFRESH_DELAY') or 5.0) # 웹훅을 보내고 기다릴 시간 (초)
    OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
    OPENWEATHERMAP_LAT = 0.0
    OPENWEATHERMAP_LONG = 0.0

    LCD_REFRESH_DELAY = float(os.getenv('LCD_REFRESH_DELAY') or 5.0) # LCD에 정보를 전송하고 기다릴 시간 (초)
    ALERT_REFRESH_DELAY = float(os.getenv('ALERT_REFRESH_DELAY') or 5.0) # TTS로 경고를 하고 기다릴 시간 (초)
    WEATHER_REFRESH_DELAY = float(os.getenv('WEATHER_REFRESH_DELAY') or 600.0)

    # 마지막으로 보낸 데이터
    last_sent_timestamp = time.time() - LCD_REFRESH_DELAY
    last_alert_timestamp = time.time() - ALERT_REFRESH_DELAY
    last_weather_timestamp = time.time() - WEATHER_REFRESH_DELAY

    folder = 'res'

    iot_status: dict[str, str] = {
        'LED1': 'false',
        'LED2': 'false',
        'LED3': 'false',
        'LED4': 'false'
    }
    def iot_stream_handler(message) -> None:
        """
        Firebase에서 IoT가 제어되었을 때 실행되는 함수
        """
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

    while True:
        fire_floor = list(
            filter(lambda x: x > 0,
                map(lambda x: x.fireDetectedFloor, [cam0, cam1, cam2, cam3])
            )
        )

        # 사람이 없을 경우 아두이노에 절전 모드 신호 전송
        if sum([cam0.personCount, cam1.personCount, cam2.personCount, cam3.personCount]) == 0:
            ser.write('EcoMode:1\n'.encode())
            print(f"[{time.time()}] EcoMode:1")
        else:
            ser.write('EcoMode:0\n'.encode())
            print(f"[{time.time()}] EcoMode:0")

        if len(fire_floor) > 0:
            ser.write(f"FireAt:{','.join(fire_floor)}\n".encode())

            # 웹훅 전송
            message = f"Fire detected on floor {', '.join(fire_floor)}"
            if last_sent_timestamp + WEBHOOK_REFRESH_DELAY <= time.time():
                fetch(WEBHOOK_URL, message)
                last_sent_timestamp = time.time()

            # TTS로 화재 위치 알림
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
        else: # 불이 감지되지 않으면 FireAt:0을 전송
            ser.write('FireAt:0\n'.encode())
            print(f"[{time.time()}] FireAt:0")
    
        time.sleep(LCD_REFRESH_DELAY)

    ser.close()