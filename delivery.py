import os, sys, time
import json
import serial
import datetime
import crypto
sys.modules['Crypto'] = crypto # Pyrebase에서 Crypto모듈을 찾을 수 없어 crypto 모듈을 Crypto 이름으로 추가
import pyrebase
from gtts import gTTS
from playsound import playsound
import requests
from dotenv import load_dotenv

load_dotenv(verbose=True)

# IoT 활용을 위한 Firebase 설정
# 보안을 위해 설정값은 .env파일에 저장
config = {
    "apiKey": os.getenv('FIREBASE_APIKEY') or '',
    "authDomain": os.getenv('FIREBASE_AUTHDOMAIN') or '',
    "databaseURL": os.getenv('FIREBASE_DBURL') or '',
    "storageBucket": os.getenv('FIREBASE_STORAGEBUCKET') or ''
}

# Firebase 실시간 데이터베이스를 사용하기 위한 객체
firebase = pyrebase.initialize_app(config)
db = firebase.database()

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
        """
        웹훅 데이터를 슬랙, 디스코드에 호환되도록 설정
        """
        return json.dumps({
            "username": "Fire Alert",
            "content": message,
            "text": message
        })
    
    # 웹훅 요청
    try:
        res = requests.post(url, webhookData(message), headers={
            'Content-Type': 'application/json'
        })
        
        if res.ok:
            print("Webhook sent")
        else:
            print(res.status_code)
    except:
        pass

def delivery(cam0, cam1, cam2, cam3) -> None:
    """
    각 데이터를 전송하는 함수

    Args:
        cam0 (FireDetector): 화재감지 객체 0

        cam1 (FireDetector): 화재감지 객체 1

        cam2 (FireDetector): 화재감지 객체 2

        cam3 (FireDetector): 화재감지 객체 3

    """
    # 시리얼 통신 연결
    ser = serial.Serial(port=os.getenv('SERIAL_PORT'), baudrate=9600, timeout=0)
    datetime_object = datetime.datetime.fromtimestamp(time.time())

    WEBHOOK_URL = os.getenv('WEBHOOK_URL') or ''
    WEBHOOK_REFRESH_DELAY = float(os.getenv('WEBHOOK_REFRESH_DELAY') or 5.0) # 웹훅을 보내고 기다릴 시간 (초)
    OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
    OPENWEATHERMAP_LAT = 37.4685318
    OPENWEATHERMAP_LONG = 127.0390682

    LCD_REFRESH_DELAY = float(os.getenv('LCD_REFRESH_DELAY') or 5.0) # LCD에 정보를 전송하고 기다릴 시간 (초)
    ALERT_REFRESH_DELAY = float(os.getenv('ALERT_REFRESH_DELAY') or 5.0) # TTS로 경고를 하고 기다릴 시간 (초)
    WEATHER_REFRESH_DELAY = float(os.getenv('WEATHER_REFRESH_DELAY') or 60.0)

    # 마지막으로 보낸 데이터를 보내고 지난 시간
    last_sent_timestamp = 0
    last_alert_timestamp = 0
    last_weather_timestamp = 0

    # TTS 데이터를 저장할 폴도
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

        # CtrlIoT:0000 형식으로 데이터 전송
        # 값이 1이면 LED ON, 값이 0이면 LED OFF
        ser.write(f"CtrlIoT:".encode())
        print(f"[{time.time()}] CtrlIoT")
        # 값이 'true'이면 '1', 값이 'false'이면 '0'으로 변환 
        ser.write(''.join('1' if iot_status[f'LED{i+1}'] == 'true' else '0' for i in range(4)).encode())
        print(f"[{time.time()}] {('1' if iot_status[f'LED{i+1}'] == 'true' else '0' for i in range(4))}")
        ser.write('\n'.encode())
        
        print(iot_status)
        print(message)

    # Firebase 모듈 초기화
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()
    iot_stream = db.child('light').stream(iot_stream_handler)

    if not os.path.exists(folder):
        os.makedirs(folder)

    while True:
        # 불이 인식된 층 (0이 아닌 곳)을 필터하여 리스트로 변환
        fire_floor = list(
            filter(lambda x: int(x) > 0,
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
            # 화재 감지 데이터 전송
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

                # 파일이 없는 경우 gTTS로 새로운 목소리 파일을 받아오기
                if not os.path.exists(filepath):
                    tts = gTTS(text=text, lang='ko')
                    tts.save(filepath)
                    print(f"WAV file '{filename}' generated successfully.")
                else:
                    print(f"WAV file '{filename}' already exists.")
                
                # 소리 파일 재생
                playsound(filepath, block=False)
                last_alert_timestamp = time.time()

            # 날씨 데이터 전송

            print(f"[{time.time()}] FireAt:{','.join(fire_floor)}")
        else: # 불이 감지되지 않으면 FireAt:0을 전송
            ser.write('FireAt:0\n'.encode())
            print(f"[{time.time()}] FireAt:0")
        """
        if last_weather_timestamp + WEATHER_REFRESH_DELAY <= time.time():
            res = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={OPENWEATHERMAP_LAT}&lon={OPENWEATHERMAP_LONG}&appid={OPENWEATHERMAP_API_KEY}&units=metric")
            weather = res.json()
            print(weather)
            ser.write(f"Weather:{weather['weather'][0]['main']}\n".encode())
            ser.write(f"Temp:{weather['main']['temp']}\n".encode())
            print(weather['weather'][0]['main'])
            print(weather['main']['temp'])
            last_weather_timestamp = time.time()
            """
            
        time.sleep(LCD_REFRESH_DELAY)

    ser.close()

def updateLED(id: int, value: str):
    db.child("light").update({f"LED{id+1}": value})