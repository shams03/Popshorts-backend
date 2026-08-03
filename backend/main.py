# pipeline
import os
import json
import uuid
from utils.llm import llm_query, llm_structured
from utils.transcription import get_word_array
from utils.videoProcessing import get_video_dimensions, extract_audio_for_asr, extract_audio, trim_video, find_clip_times, attach_audio_segment, combine_videos
from features.subtitleAddition import add_subtitles
from models import ContentIdeasList, ShortScript, ShortsExtractionResult, ShortMetadata
from features.context_crop.contextAwareCrop import generate_context_aware_crop
from features.autoUpload import upload_short
import pickle


def process_video(file_path, upload=False, mode="sequential",number=4):

    temp_files = []

    # width, height = get_video_dimensions(file_path)

    audio_uuid = str(uuid.uuid4())
    audio_path = os.path.join("shorts", f"{audio_uuid}_audio.wav")
    audio_path = extract_audio_for_asr(file_path,audio_path)
    
    # Save audio to shorts folder with UUID
  
    temp_files.append(audio_path)
    
    # audio_path = "audio.wav"

    word_array = get_word_array(audio_path)

    with open(os.path.join("shorts", "word_array.json"), "w") as f:
        json.dump(word_array, f)

    with open(os.path.join("shorts", "word_array.json"), "r") as f:
        word_array = json.load(f)

    script = ""
    for word in word_array:
        script += f"{word['word']} "

    output_format = """ {
    "contentList": [
        {
        "topic": "...",
        "vitality_score": 0,
        "reason": "...",
        "quote": "..."
        }
    ]
    }"""
    shorts_prompt = f"""SYSTEM:
    You are a YouTube Shorts content extraction engine.
    You are NOT allowed to invent, infer, paraphrase, or summarize.
    You must ONLY extract exact words that already exist in the provided script.

    USER:
    You are given the FULL TRANSCRIPT of a long-form video or podcast.

    Your task is to extract SHORT-FORM CONTENT IDEAS suitable for YouTube Shorts.
    We want {number} of shorts.

    INPUT:
    Full Script:
    {script}

    TASK:
    From the script, extract {number} SHORTS candidates.

    For EACH short, return the following fields:

    1. topic  
    - A concise hook-style title
    - Must be inferred ONLY from the extracted quote (no new ideas)

    2. virality_score  
    - Integer from 1–10
    - Based on emotional impact, clarity, and short-form virality
    - Do NOT justify the score with new statements

    3. reason  
    - Why this clip works as a short
    - Must ONLY reference what is explicitly said in the quote
    - No external interpretation or assumptions

    4. quote  
    - EXACT words copied VERBATIM from the script
    - No paraphrasing
    - No added words
    - Must be continuous text from the script (no stitching from different places)

    
    5. content_category  
    type of content like educative, controversial or other types.

    RULES (VERY IMPORTANT):
    - ❌ No random statements
    - ❌ No paraphrasing
    - ❌ No summarization
    - ❌ No words outside the script
    - ✅ Use ONLY exact text spans from the script
    - ✅ If something is not explicitly stated, DO NOT include it
    - ✅ Quotes must be suitable for a 25-90 second short when spoken

    OUTPUT FORMAT:
    Return JSON ONLY in the following structure:

    {output_format}
    """ 

    print("final shorts propmpt ,. ", shorts_prompt)
    shorts = llm_structured(shorts_prompt,ShortsExtractionResult)

    shorts = shorts.contentList

    print("final shorts content . ", shorts)
    # shorts = [ShortScript(quote="You think about a person like that. You think of them as in this, like, static, fully formed version, right? You don't usually get to see. You went into so much depth about your rise and fall. It wasn't like a straight linear process. You see a guy who runs eight 100 mile races eight weekends in a row. It's an insane accomplishment. I fell on my ass. I started from scratch again. Scratch became my friend. Just a real raw version of how my life was. You're so honest about your vulnerabilities. For people that see someone who's a beast, who's done great things, you assume they're different than you. But then you hear about your insecurities and your pitfalls, and you realize, those are the same things that go wrong with me. Maybe I have that inside of me. We all have a jacked up life in one way or another. Life is one big psychological warfare that you play on yourself.", phrases=['You think about a person like that.', 'You think of them as in this, like, static,', 'fully formed version, right?', "You don't usually get to see.", 'You went into so much depth', 'about your rise and fall.', "It wasn't like a straight linear process.", 'You see a guy who runs', 'eight 100 mile races', 'eight weekends in a row.', "It's an insane accomplishment.", 'I fell on my ass.', 'I started from scratch again.', 'Scratch became my friend.', 'Just a real raw version of how my life was.', "You're so honest about your vulnerabilities.", "For people that see someone who's a beast,", "who's done great things,", "you assume they're different than you.", 'But then you hear about your insecurities', 'and your pitfalls,', 'and you realize,', 'those are the same things', 'that go wrong with me.', 'Maybe I have that inside of me.', 'We all have a jacked up life', 'in one way or another.', 'Life is one big psychological warfare', 'that you play on yourself.'])]
    final_shorts = []
    for index, short in enumerate(shorts):
        short_id_base = f"short_{index}"
        
        style = {
            "font_size": 48,
            "color": "#ffffff",
            "stroke_width": 2,
            "stroke_fill": "#000000",
            "position": "bottom",
            "margin": 60,
        }

        if mode == "sequential":
            # Attempt to find the full sequential text
            full_text = short.quote
            start_time, end_time, start_index, end_index = find_clip_times(word_array, full_text)

            if start_time is None or end_time is None or start_index is None or end_index is None:
                print(f"⚠️  Skipping short {index}: could not locate quote in transcript")
                print(f"    quote preview: {str(full_text)[:120]}...")
                continue

            if end_time <= start_time:
                print(f"⚠️  Skipping short {index}: invalid times {start_time} → {end_time}")
                continue

            trimmed_path = trim_video(file_path, start_time, end_time, os.path.join("shorts", f"{short_id_base}_seq_trim.mp4"))
            temp_files.append(trimmed_path)

            contextCroppedVideo = generate_context_aware_crop(trimmed_path, os.path.join("shorts", f"{short_id_base}_seq_crop.mp4"))
            temp_files.append(contextCroppedVideo)

            audio_path_out = os.path.join("shorts", f"{short_id_base}_seq_audio.mp4")
            attach_audio_segment(contextCroppedVideo, audio_path, start_time, end_time, audio_path_out)
            temp_files.append(audio_path_out)

            # Adjust timestamps for subtitles
            words_in_clip = word_array[start_index:end_index + 1]

            adjusted_words = []
            for w in words_in_clip:
                new_w = w.copy()
                new_w["start"] = max(0.0, round(float(w["start"]) - start_time, 2))
                new_w["end"]   = max(0.0, round(float(w["end"]) - start_time, 2))
                adjusted_words.append(new_w)

            final_video = os.path.join("shorts", f"{short_id_base}.mp4")
            subtitleAddedVideo = add_subtitles(
                audio_path_out,
                adjusted_words,
                style,
                final_video,
                mode="line"
            )

            final_shorts.append({
                "quote": short.quote,
                "virality_score":short.virality_score,
                "content_category":short.content_category,
                "reason":short.reason,
                "topic":short.topic,
                "start_time": start_time,
                "end_time": end_time,
                "trimmed_path": trimmed_path,
                "subtitleAddedVideo": subtitleAddedVideo
            })
        
        elif mode == "combined":
            clips_to_combine = []
            
            for p_idx, phrase in enumerate(short.phrases):
                p_start, p_end, p_s_idx, p_e_idx = find_clip_times(word_array, phrase)
                
                if p_start is None:
                    print(f"Phrase not found: {phrase}")
                    continue
                
                # Trim
                p_trim = trim_video(file_path, p_start, p_end, os.path.join("shorts", f"{short_id_base}_p{p_idx}_trim.mp4"))
                temp_files.append(p_trim)
                
                # Crop
                p_crop = generate_context_aware_crop(p_trim, os.path.join("shorts", f"{short_id_base}_p{p_idx}_crop.mp4"))
                temp_files.append(p_crop)
                
                # Attach Audio
                p_audio_out = os.path.join("shorts", f"{short_id_base}_p{p_idx}_audio.mp4")
                attach_audio_segment(p_crop, audio_path, p_start, p_end, p_audio_out)
                temp_files.append(p_audio_out)
                
                # Subtitles
                # Get exact words for this phrase
                words = word_array[p_s_idx:p_e_idx+1]
                adj_words = []
                for w in words:
                    nw = w.copy()
                    nw["start"] = max(0.0, round(float(w["start"]) - p_start, 2))
                    nw["end"] = max(0.0, round(float(w["end"]) - p_start, 2))
                    adj_words.append(nw)
                
                p_sub = os.path.join("shorts", f"{short_id_base}_p{p_idx}_sub.mp4")
                add_subtitles(p_audio_out, adj_words, style, p_sub, mode="line")
                temp_files.append(p_sub)
                
                clips_to_combine.append(p_sub)
            
            if clips_to_combine:
                final_combined_video = os.path.join("shorts", f"{short_id_base}_combined.mp4")
                combine_videos(clips_to_combine, final_combined_video)
                
                final_shorts.append({
                    "quote": short.quote,
                    "phrases": short.phrases,
                    "subtitleAddedVideo": final_combined_video
                })
    
    # Generate metadata for each short using LLM
    print("🤖 Generating metadata for shorts...")
    for short in final_shorts:
        metadata_prompt = f"""You are a YouTube Shorts content expert. Generate metadata for a short video based on the following information:

Quote/Script: "{short['quote']}"
Topic: {short['topic']}
Virality Score: {short['virality_score']}/10
Reason it works: {short['reason']}

Generate:
1. A catchy, clickable title (under 60 characters)
2. A YouTube description (2-3 sentences) with 3-5 hashtags included at the end
3. Comma-separated SEO tags (5-10 keywords, no hashtags)

Make the metadata engaging and optimized for discoverability on YouTube."""

        try:
            metadata = llm_structured(metadata_prompt, ShortMetadata)
            short['title'] = metadata.title
            short['description'] = metadata.description
            short['tags'] = metadata.tags
            print(f"✅ Generated metadata for: {metadata.title}")
        except Exception as e:
            print(f"❌ Error generating metadata: {e}")
            short['title'] = short['topic']
            short['description'] = f"{short['reason']} #{short['topic'].replace(' ', '')}"
            short['tags'] = short['topic']
    

    # Upload shorts if requested
    if upload:
        print("📤 Uploading shorts to YouTube...")
        try:
            # Load credentials from secrets
            # from google.auth.transport.requests import Request
            # from google.oauth2.credentials import Credentials
            
            # secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", "client_secrets.json")
            # credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", "credentials.json")
            
            # if os.path.exists(credentials_path):
            #     creds = Credentials.from_authorized_user_file(credentials_path)
            #     if creds.expired:
            #         creds.refresh(Request())
            with open(os.getenv("AUTO_UPLOAD_PKL"), "rb") as f:
                credentials = pickle.load(f)

            for index, short in enumerate(final_shorts):
                url = upload_short(
                    credentials=credentials,
                    video_path=short['subtitleAddedVideo'],
                    title=short.get('title', short.get('topic', 'Untitled')),
                    description=short.get('description', short.get('reason', '')),
                    tags=short.get('tags', '').split(', ') if isinstance(short.get('tags', ''), str) else short.get('tags', [])
                )
                final_shorts[index]['url'] = url
                print(f"✅ Uploaded: {short.get('title', 'Untitled')}")
            else:
                print("⚠️ Credentials not found. Skipping upload.")
        except Exception as e:
            print(f"❌ Error uploading shorts: {e}")

    with open(os.path.join("shorts", "shorts.json"), "w") as f:
        json.dump(final_shorts, f)
    # Cleanup temporary videos
    print("🧹 Cleaning up temporary videos...")
    for video_path in temp_files:
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
                print(f"Deleted temp file: {video_path}")
            except Exception as e:
                print(f"Error deleting {video_path}: {e}")
    return final_shorts

    # add_subtitles("test.mp4", words, style, "out_line.mp4", mode="line")
    
    # trimmed_path = trim_video(file_path, start_time=0, end_time=60)


# process_video(os.path.join("trimmed_output.mp4"), mode="sequential")