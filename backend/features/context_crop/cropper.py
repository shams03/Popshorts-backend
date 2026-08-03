import cv2

class Cropper:
    def get_crop(self, frame, faces, speaker_id):
        h, w, _ = frame.shape
        face = next((f for f in faces if f["track_id"] == speaker_id), None)

        if not face:
            return None

        x, y, fw, fh = face["bbox"]

        # Increased multiplier to create larger crop region = less jitter from small movements
        crop_h = int(fh * 4.5)
        crop_w = int(crop_h * 9 / 16)

        # Position face slightly higher for better framing
        cx = x + fw // 2
        cy = y + int(fh * 0.35)

        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)

        return (x1, y1, x2, y2)

    def get_default_crop(self, frame, faces):
        """Generate crop centered on largest face if no speaker detected"""
        h, w, _ = frame.shape
        
        if not faces:
            # No faces, crop center of frame
            crop_w = int(h * 9 / 16)
            cx = w // 2
            cy = h // 2
            x1 = max(0, cx - crop_w // 2)
            y1 = max(0, cy - h // 2)
            x2 = min(w, x1 + crop_w)
            y2 = min(h, y1 + h)
            return (x1, y1, x2, y2)
        
        # Find largest face
        largest_face = max(faces, key=lambda f: f["bbox"][2] * f["bbox"][3])
        x, y, fw, fh = largest_face["bbox"]
        
        # Increased multiplier to create larger crop region = less jitter from small movements
        crop_h = int(fh * 4.5)
        crop_w = int(crop_h * 9 / 16)
        
        cx = x + fw // 2
        cy = y + int(fh * 0.35)
        
        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, x1 + crop_w)
        y2 = min(h, y1 + crop_h)
        
        return (x1, y1, x2, y2)

    def apply_crop(self, frame, crop):
        if crop is None:
            return cv2.resize(frame, (1080, 1920))

        x1, y1, x2, y2 = crop
        cropped = frame[y1:y2, x1:x2]
        return cv2.resize(cropped, (1080, 1920))
