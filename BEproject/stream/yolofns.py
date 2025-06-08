from ultralytics import YOLO
import cv2
from .models import YoloClassifier
import threading
from .Distance_cal import ServoController
from .TOF import TMF

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
        self.tmf = TMF()
        self.angle_controller = ServoController()
        self.current_angle = 45  # Start from middle angle (assuming 0-90 degrees)
        self.angle_controller.set_angle(self.current_angle)
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

            # If no detections, skip servo adjustment
            if not results or not results[0].boxes:
                with self.lock:
                    self.frame = frame
                continue

            # Take the highest confidence box to track
            result = results[0]
            sorted_boxes = sorted(result.boxes, key=lambda b: b.conf[0], reverse=True)
            box = sorted_boxes[0]
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Convert box center from resized frame to original frame scale
            h_ratio = frame.shape[0] / 96
            w_ratio = frame.shape[1] / 96

            center_x = int(((x1 + x2) / 2) * w_ratio)
            center_y = int(((y1 + y2) / 2) * h_ratio)

            # Draw box and center point on frame for visualization
            x1_o = int(x1 * w_ratio)
            x2_o = int(x2 * w_ratio)
            y1_o = int(y1 * h_ratio)
            y2_o = int(y2 * h_ratio)
            cv2.rectangle(frame, (x1_o, y1_o), (x2_o, y2_o), (0, 255, 0), 1)
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

            # Calculate how far the center_x is from the frame center
            frame_center_x = frame.shape[1] // 2
            error_x = center_x - frame_center_x

            # Sensitivity factor: how much angle to move per pixel error
            sensitivity = 0.1  # Adjust this experimentally

            # Calculate new angle (invert error because servo angle 0 is left, 90 is right)
            new_angle = self.current_angle - error_x * sensitivity
            # Clamp angle between 0 and 90 degrees
            new_angle = max(0, min(90, new_angle))

            # Update servo only if angle changed sufficiently (avoid jitter)
            if abs(new_angle - self.current_angle) > 1:
                self.angle_controller.set_angle(new_angle)
                self.current_angle = new_angle

            print('Current ANGLE is ... ',self.current_angle)

            # Optionally display current angle on frame
            cv2.putText(frame, f"Angle: {int(self.current_angle)}", (10, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            # Also show distance if available
            if dist := self.tmf.get_distance():
                cv2.putText(frame, f"Distance: {dist}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            with self.lock:
                self.frame = frame

    def get_all_categories(self):
        return self.model.model.names

    def get_active_categories(self):
        return YoloClassifier.objects.all()
    
    def post_new_categories(self,categories):
        YoloClassifier.objects.all().delete()
        for category in categories:
            YoloClassifier.objects.create(categories=category)


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
