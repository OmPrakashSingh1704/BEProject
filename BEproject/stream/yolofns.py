from ultralytics import YOLO
import cv2
from .models import YoloClassifier
import threading

class YoloController:
    def __init__(self, feed=None):
        self.cap = None
        if feed is not None:
            self.cap = cv2.VideoCapture(feed)

        self.model = YOLO("yolov8s-worldv2.pt")
        
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.frame_skip = 0

        self.thread = threading.Thread(target=self._update_frames, daemon=True)
        self.thread.start()

    def close(self):
        """Called by Django to release resources when streaming ends."""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def _update_frames(self):
        while self.running:
            if not self.cap:
                return
            category_qs = YoloClassifier.objects.filter()
            if category_qs.exists():
                categories = [c.categories for c in category_qs]

                self.model.set_classes(categories)
            success, frame = self.cap.read()
            if not success:
                continue

            self.frame_skip += 1
            if self.frame_skip % 2 != 0:
                continue

            resized = cv2.resize(frame, (96, 96))
            results = self.model(resized, imgsz=96, device='cpu')

            for result in results:
                class_counter = {}
                sorted_boxes = sorted(result.boxes, key=lambda b: b.conf[0], reverse=True)

                for i, box in enumerate(sorted_boxes):
                    if i > 10:
                        break

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    label_base = self.model.names[cls]

                    class_counter[label_base] = class_counter.get(label_base, 0) + 1
                    label = f"{label_base} {class_counter[label_base]}"

                    h_ratio = frame.shape[0] / 96
                    w_ratio = frame.shape[1] / 96
                    x1 = int(x1 * w_ratio)
                    x2 = int(x2 * w_ratio)
                    y1 = int(y1 * h_ratio)
                    y2 = int(y2 * h_ratio)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                    cv2.putText(frame, label, (x1, y1 + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            with self.lock:
                self.frame = frame

    def get_all_categories(self):
        return self.model.model.names

    def get_active_categories(self):
        return YoloClassifier.objects.all()
    
    def post_new_categories(self,categories):
        YoloClassifier.objects.update_or_create(categories=categories)


class StreamWrapper:
    def __init__(self, yolo_controller: YoloController):
        self.controller = yolo_controller

    def __iter__(self):
        try:
            while self.controller.running:
                with self.controller.lock:
                    if self.controller.frame is None:
                        continue
                    ret, buffer = cv2.imencode('.jpg', self.controller.frame)
                    if not ret:
                        continue
                    frame_bytes = buffer.tobytes()

                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                )
        except Exception as e:
            print(f"Error in streaming: {e}")
        finally:
            self.close()

    def close(self):
        """Called by Django when the stream ends."""
        self.controller.close()
