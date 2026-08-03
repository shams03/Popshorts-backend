# Soft-import: pyannote/torchaudio mismatches shouldn't block the API from starting
import subprocess

try:
    from pyannote.audio import Pipeline
except Exception as e:
    Pipeline = None
    print(f"⚠️  pyannote.audio unavailable at import time: {e}")


class SpeakerDetector:
    def __init__(self, video_path):
        self.video_path = video_path
        self.available = False
        self.pipeline = None
        self.diarization = None

        if Pipeline is None:
            print("⚠️  SpeakerDetector not available: pyannote.audio not importable")
            return

        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization"
            )

            self.audio_path = "temp_audio.wav"

            subprocess.run(
                ["ffmpeg", "-y", "-i", video_path, "-ac", "1", "-ar", "16000", self.audio_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.diarization = self.pipeline(self.audio_path)
            self.available = True
        except Exception as e:
            print(f"⚠️  SpeakerDetector not available: {e}")
            print("⚠️  Proceeding without speaker detection")
            self.available = False

    def get_stable_speaker(self, time_sec, faces):
        """Return speaker ID if available, otherwise return None"""
        if not self.available or self.diarization is None:
            return None

        try:
            for segment, _, speaker in self.diarization.itertracks(yield_label=True):
                if segment.start <= time_sec <= segment.end:
                    return int(speaker.split("_")[1])
        except Exception as e:
            print(f"⚠️  Error getting speaker: {e}")
            return None

        return None
