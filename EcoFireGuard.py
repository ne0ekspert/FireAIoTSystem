import cv2
from ultralytics import YOLO
import serial

# 시리얼 포트 설정
#py_serial = serial.Serial(port='COM11', baudrate=9600)

model = YOLO('best.pt')

cap = cv2.VideoCapture(2)

bbox = []

while cap.isOpened():
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

        cv2.imshow("Object Detection", result_frame)

        if cv2.waitKey(1) == ord("q"):
            break
    else:
        break

cap.release()
cv2.destroyAllWindows()