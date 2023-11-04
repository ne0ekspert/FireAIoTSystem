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

        fire (bool): 화재 감지 플래그

        detected_people (int): 카메라에 감지된 인원 수

        result_frame: 출력 프레임

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
            # 카메라에서 프레임 읽어오기
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

                    # 감지된 물체들을 하나씩 화면에 추가
                    for box in boxes:
                        # 외곽선 색을 인식된 물체가 불인 경우 초록색, 아닐 경우 붉은색으로 설정
                        color: tuple[int, int, int] = (0, 255, 0) if box.cls == 0 else (0, 0, 255)

                        position = list(map(int, box.xyxy.tolist()[0])) # 출력값은 float인데 int로 변환
                        # 감지된 물체 Class ID가 다음 값으로 저장됨
                        # 0: 불
                        # 1: 사람
                        detect_class_id = int(box.cls.tolist()[0])
                        detect_class_label: str = 'person' if detect_class_id == 1 else 'fire' # 문자열 값으로 변경 1: 'person', 0: 'fire'

                        # 감지된 물체가 감지 범위 외에 있을 경우 무시하고 진행
                        if position[0] > 400:
                            continue

                        if detect_class_id == 0: # 불이 감지되었을 때 감지된 물체 목록에 1 추가
                            detected_objects['fire'] += 1

                        if detect_class_id == 1: # 사람이 감지되었을 때 사람에 1 추가
                            detected_objects['person'] += 1

                        # 감지된 물체 외곽선
                        result_frame = cv2.rectangle(result_frame, (position[0], position[1]), (position[2], position[3]), color, 2)

                        # 감지된 물체 종류 텍스트
                        result_frame = cv2.putText(result_frame, detect_class_label, (position[0], position[1]), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255 ,255), 1, cv2.LINE_AA)

                # 화면에 층 수 표시
                result_frame = cv2.putText(result_frame, f"{self.changed_index+1}Floor", (0, 50), cv2.FONT_HERSHEY_DUPLEX, 2, (255, 255, 0), 2, cv2.LINE_AA)

                self.detect_ready = True # 준비 완료 설정
                self.detected_people = detected_objects['person']
                self.fire = detected_objects['fire'] > 0 # 불이 감지된 경우 True, 아닌 경우 False
                self.result_frame = result_frame

    def release_camera(self):
        """
        카메라를 연결 해제하고 스레드 정지
        """
        print(f"Releasing Camera ID: {self.index}")
        self.done = True
        self.cap.release()

    @property
    def isReady(self):
        """
        감지 준비 완료 값
        """
        return self.detect_ready

    @property
    def personCount(self):
        """
        감지된 인원 수
        """
        return self.detected_people
    
    @property
    def fireDetectedFloor(self) -> str:
        """
        불이 감지되었을 경우 층 수를 반환
        """
        return str(self.changed_index) if self.fire else '0'

    @property
    def originalFrame(self):
        return self.original_frame

    @property
    def resultFrame(self):
        return self.result_frame