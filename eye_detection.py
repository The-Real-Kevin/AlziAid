import cv2
import numpy as np
import time

asdf222 = 225
class multi_eye_pupil_detection():
    def __init__(self):
        self._pupils = []
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.blink_threshold = 1  # Frames to consider a blink
        self.eye_states = {}  # Track state of each eye
        self.blink_counters = {}  # Count frames for potential blinks

    def detect_eyes(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray)
        eyes = []
        for (x, y, w, h) in faces:
            x = int(x+w // 7.2)
            y = int(y+h // 4.2)
            w = int(w // 1.4)
            h = int(h//4)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            roi_gray = gray[y:y+h, x:x+w]
            eyes_in_face = self.eye_cascade.detectMultiScale(roi_gray)
            for (ex, ey, ew, eh) in eyes_in_face:
                eyes.append((x+ex, y+ey, ew, eh))
        return eyes

    def detect_pupil(self, eye_frame):
        global asdf222
        dst = cv2.fastNlMeansDenoisingColored(eye_frame, None, 10, 10, 7, 21)
        
        threshold = cv2.cvtColor(cv2.bitwise_not(cv2.GaussianBlur(dst, (5, 5), 0)), cv2.COLOR_BGR2GRAY)
        
        kernel = np.ones((2, 2), np.uint8)
        erosion = cv2.erode(threshold, kernel, iterations=1)
        
        _, thresh1 = cv2.threshold(erosion, asdf222, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            eye_center = (eye_frame.shape[1] // 2, eye_frame.shape[0] // 2)
            closest_cnt = min(contours, key=lambda cnt: 
                            abs(cv2.minEnclosingCircle(cnt)[0][0] - eye_center[0]) + 
                            abs(cv2.minEnclosingCircle(cnt)[0][1] - eye_center[1]))
            
            (x, y), radius = cv2.minEnclosingCircle(closest_cnt)
            center = (int(x), int(y))
            radius = int(radius)
            
            return center, radius
        
        return None, None

    def process_frame(self, frame):
        eyes = self.detect_eyes(frame)
        self._pupils = []
        current_time = time.time()

        for i, (x, y, w, h) in enumerate(eyes):
            eye_frame = frame[y:y+h, x:x+w]
            center, radius = self.detect_pupil(eye_frame)
            
            if center and radius:
                center = (x + center[0], y + center[1])
                self._pupils.append((center, radius))
                
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(frame, center, radius, (0, 0, 255, 100), 1)

                # Eye is open
                if i in self.eye_states:
                    if self.eye_states[i] == 'c':
                        if self.blink_counters[i] >= self.blink_threshold:
                            print(f"Blink detected for eye {i+1}")
                        self.blink_counters[i] = 0
                self.eye_states[i] = 'o'
                self.blink_counters[i] = 0
            else:
                # Eye is closed or pupil not detected
                if i not in self.eye_states or self.eye_states[i] == 'o':
                    self.eye_states[i] = 'c'
                    self.blink_counters[i] = 1
                else:
                    self.blink_counters[i] += 1

        return frame

    def start_detection(self):
        global asdf222
        cap = cv2.VideoCapture(0)

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            print(f"current thres {asdf222}")
            result_frame = self.process_frame(frame)

            cv2.imshow("frame", result_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

detector = multi_eye_pupil_detection()
detector.start_detection()