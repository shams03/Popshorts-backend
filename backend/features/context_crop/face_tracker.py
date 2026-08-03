# import mediapipe as mp

# class FaceTracker:
#     def __init__(self):
#         self.mp_face = mp.solutions.face_detection.FaceDetection(0.6)
#         self.next_id = 0
#         self.tracks = {}

#     def detect_and_track(self, frame):
#         h, w, _ = frame.shape
#         results = self.mp_face.process(frame[:, :, ::-1])
#         faces = []

#         if not results.detections:
#             return faces

#         for det in results.detections:
#             box = det.location_data.relative_bounding_box
#             bbox = [
#                 int(box.xmin * w),
#                 int(box.ymin * h),
#                 int(box.width * w),
#                 int(box.height * h),
#             ]
#             faces.append({
#                 "track_id": self.next_id,
#                 "bbox": bbox
#             })
#             self.next_id += 1

#         return faces

import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class FaceTracker:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "..", "..", "models", "blaze_face_short_range.tflite")
        base_options = python.BaseOptions(
            model_asset_path=model_path
        )

        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=0.6
        )

        self.detector = vision.FaceDetector.create_from_options(options)
        self.prev_faces = {}  # Store smoothed face positions
        self.face_smoothing = 0.85  # Higher = more stable
        self.min_face_movement = 8  # Pixels threshold to update face position

    def detect_and_track(self, frame):
        h, w, _ = frame.shape

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame
        )

        detection_result = self.detector.detect(mp_image)
        faces = []

        for i, det in enumerate(detection_result.detections):
            bbox = det.bounding_box
            current_bbox = [
                bbox.origin_x,
                bbox.origin_y,
                bbox.width,
                bbox.height
            ]
            
            # Apply smoothing to face position to reduce jitter
            if i in self.prev_faces:
                prev_bbox = self.prev_faces[i]
                
                # Check if movement is significant
                movement = sum(abs(c - p) for p, c in zip(current_bbox, prev_bbox))
                
                if movement < self.min_face_movement:
                    # Movement too small, use previous smoothed position
                    smoothed_bbox = prev_bbox
                else:
                    # Movement significant, apply smoothing
                    smoothed_bbox = [
                        int(self.face_smoothing * p + (1 - self.face_smoothing) * c)
                        for p, c in zip(prev_bbox, current_bbox)
                    ]
            else:
                # First detection of this face
                smoothed_bbox = current_bbox
            
            self.prev_faces[i] = smoothed_bbox
            
            faces.append({
                "track_id": i,
                "bbox": smoothed_bbox
            })

        return faces
