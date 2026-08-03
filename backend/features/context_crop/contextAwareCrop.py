import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from face_tracker import FaceTracker
from speaker_detector import SpeakerDetector
from cropper import Cropper
from smoother import SmoothCamera
import cv2

def generate_context_aware_crop(video_path: str, output_path: str):
    """
    Generates a context-aware portrait crop of the input video.
    
    Args:
        video_path (str): Path to the input video file.
        output_path (str): Path where the output video will be saved.
        
    Returns:
        str: Path to the generated output video.
    """
    face_tracker = FaceTracker()
    speaker_detector = SpeakerDetector(video_path)
    cropper = Cropper()
    camera = SmoothCamera()

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (1080, 1920)
    )

    frame_idx = 0
    last_speaker_id = None  # Track the last person who spoke

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        time_sec = frame_idx / fps

        faces = face_tracker.detect_and_track(frame)
        active_speaker_id = speaker_detector.get_stable_speaker(time_sec, faces)

        # Update last_speaker_id when someone is speaking
        if active_speaker_id is not None:
            last_speaker_id = active_speaker_id

        # Determine which speaker to focus on
        if active_speaker_id is not None:
            # Someone is speaking, focus on them
            target_crop = cropper.get_crop(frame, faces, active_speaker_id)
            smooth_crop = camera.smooth(target_crop)
            portrait_frame = cropper.apply_crop(frame, smooth_crop)
        elif last_speaker_id is not None:
            # No one speaking, but we have a last speaker - keep focus on them
            target_crop = cropper.get_crop(frame, faces, last_speaker_id)
            smooth_crop = camera.smooth(target_crop)
            portrait_frame = cropper.apply_crop(frame, smooth_crop)
        else:
            # No one has spoken yet (start of video), crop based on largest face
            target_crop = cropper.get_default_crop(frame, faces)
            smooth_crop = camera.smooth(target_crop)
            portrait_frame = cropper.apply_crop(frame, smooth_crop)

        out.write(portrait_frame)
        frame_idx += 1

    cap.release()
    out.release()
    print("✅ Context-aware portrait video generated")
    return output_path

if __name__ == "__main__":
    # VIDEO_PATH = "input.mp4"
    project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
    VIDEO_PATH = os.path.join(project_root, "testing", "testing-assets", "test2.mp4")
    OUTPUT_PATH = os.path.join(project_root, "testing", "testing-assets", "output_portrait.mp4")
    
    generate_context_aware_crop(VIDEO_PATH, OUTPUT_PATH)
