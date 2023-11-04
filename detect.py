import cv2
import time
from ultralytics import YOLO

# 화재 인식 모델 불러오기
model = YOLO('best.pt', task='detect')

class FireDetector:
    """
    화재 감지 클래스

    Args:
        index (int): 실제 카메라의 ID

        changed_index (int): 카메라와 층 수가 맞지 않을 경우 변경할 번호
    
    Attributes:
        index (int): 카메라의 ID

        changed_index (int): 바꿀 ID

        done (bool): 동작 완료 플래그

        detect_ready (bool): 인식 준비 완료 플래그

        cap (VideoCapture): 카메라 객체

    """
    def __init__(self, index, changed_index):
        self.index = index
        self.changed_index = changed_index

        self.fire = False
        self.detected_people = 0
        self.result_frame = None

        self.done = False
        self.detect_ready = False
        self.cap = cv2.VideoCapture(index)

    def detect(self) -> None:
        """
        화재 인식 스레드 함수
        """
        print(f"{self.index}: 감지 스레드 시작")
        while not self.done:
            success, frame = self.cap.read()

            if success:
                self.original_frame = frame
                detect_start_time = time.time()
                try:
                    # 화재 감지 모델로 화재 감지
                    results = model.predict(frame, half=True, device='cpu', verbose=False)
                except Exception as e:
                    print(f"ERROR: {e}")
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

                result_frame = cv2.putText(result_frame, f"{self.changed_index+1}Floor", (0, 50), cv2.FONT_HERSHEY_DUPLEX, 2, (255, 255, 0), 2, cv2.LINE_AA)

                self.detect_ready = True
                self.detected_people = detected_objects['person']
                self.fire = detected_objects['fire'] > 0
                self.result_frame = result_frame
            else:
                self.cap = cv2.VideoCapture(self.index)

    def release_camera(self):
        print(f"Releasing Camera ID: {self.index}")
        self.done = True
        self.cap.release()

    @property
    def isReady(self):
        return self.detect_ready

    @property
    def personCount(self):
        return self.detected_people
    
    @property
    def fireDetectedFloor(self) -> str:
        return str(self.changed_index + 1) if self.fire else '0'

    @property
    def originalFrame(self):
        return self.original_frame

    @property
    def resultFrame(self):
        return self.result_frame