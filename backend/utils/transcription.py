import assemblyai as aai
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("ASSEMBLYAI_API_KEY")
def get_word_array(audio_file: str) -> Optional[List[Dict]]:
    """
    Returns array of words with timestamps in seconds and confidence.
    
    Returns:
        List of dicts:
        [{"word": "hello", "start": 1.234, "end": 1.456, "confidence": 0.98}]
    """
    aai.settings.api_key = api_key
    transcriber = aai.Transcriber()
    
    config = aai.TranscriptionConfig(word_boost=[])
    transcript = transcriber.transcribe(audio_file, config=config)
    
    if transcript.status != aai.TranscriptStatus.completed:
        print(f"Error: {transcript.error}")
        return None
    
    words_array = []
    for word in transcript.words:
        words_array.append({
            "word": word.text.strip(),
            "start": word.start / 1000.0,  # seconds
            "end": word.end / 1000.0,      # seconds
            "confidence": word.confidence
        })
    
    return words_array


# Usage
# words = get_word_array("audio.wav", "")
# print(words)
# print(words[:5])  # First 5 words
# [{'text': 'welcome', 'start': 200, 'end': 800, 'confidence': 0.98}, ...]
