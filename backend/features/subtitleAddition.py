import os
import subprocess
import shutil
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _escape_ffmpeg_value(s: str) -> str:
    s = str(s)
    s = s.replace("'", "")
    s = s.replace('"', "")
    s = s.replace("/", "")
    s = s.replace("\\", "")
    return s


def _hex_rgb(col) -> str:
    if not col:
        return "ffffff"
    if isinstance(col, (tuple, list)):
        return f"{int(col[0]):02x}{int(col[1]):02x}{int(col[2]):02x}"
    return str(col).lstrip("#")[:6]


def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    h = _hex_rgb(hex_str)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _ffmpeg_exists():
    return shutil.which("ffmpeg") is not None


def _has_drawtext_filter() -> bool:
    if not _ffmpeg_exists():
        return False
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "drawtext" in (r.stdout or "")
    except Exception:
        return False


def build_lines(words, min_words=2, max_words=4):
    lines = []
    buffer = []
    for w in words:
        buffer.append(w)

        if len(buffer) >= max_words:
            lines.append({
                "text": " ".join(x["word"] for x in buffer),
                "start": buffer[0]["start"],
                "end": buffer[-1]["end"],
            })
            buffer = []

    if buffer:
        lines.append({
            "text": " ".join(x["word"] for x in buffer),
            "start": buffer[0]["start"],
            "end": buffer[-1]["end"],
        })

    return lines


def _resolve_font(font_size: int, font_family: Optional[str] = None) -> ImageFont.ImageFont:
    candidates = []
    if font_family and os.path.isfile(font_family):
        candidates.append(font_family)
    candidates.extend([
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ])
    for path in candidates:
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue
    return ImageFont.load_default()


def _prepare_units(words, mode, min_words, max_words):
    if mode == "line":
        units = build_lines(words, min_words, max_words)
        return units, (lambda u: u["text"]), (lambda u: u["start"]), (lambda u: u["end"])
    return words, (lambda u: u["word"]), (lambda u: u["start"]), (lambda u: u["end"])


def _add_subtitles_opencv(
    video_path,
    words,
    style,
    output_path,
    mode="word",
    min_words=2,
    max_words=4,
):
    """Burn subtitles with PIL/OpenCV — works without ffmpeg drawtext."""
    units, get_text, get_start, get_end = _prepare_units(words, mode, min_words, max_words)

    font_size = int(style.get("font_size", 48))
    fill = _hex_to_rgb(style.get("color", "#ffffff"))
    stroke_fill = _hex_to_rgb(style.get("stroke_fill", "#000000"))
    stroke_w = int(style.get("stroke_width", 2))
    margin = int(style.get("margin", 60))
    pos = style.get("position", "bottom")
    font = _resolve_font(font_size, style.get("font_family"))

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tmp_video = output_path + ".nosound.mp4"
    writer = cv2.VideoWriter(
        tmp_video,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        t = frame_idx / fps
        active = [
            u for u in units
            if get_start(u) is not None
            and get_end(u) is not None
            and get_start(u) <= t <= get_end(u)
        ]
        if active:
            text = get_text(active[-1])
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (width - tw) // 2
            if pos == "top":
                y = margin
            elif pos == "center":
                y = (height - th) // 2
            else:
                y = height - th - margin - 60
            draw.text(
                (x, y),
                text,
                font=font,
                fill=fill,
                stroke_width=stroke_w,
                stroke_fill=stroke_fill,
            )
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    # Re-attach original audio
    cmd = [
        "ffmpeg", "-y",
        "-i", tmp_video,
        "-i", video_path,
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        if os.path.exists(tmp_video):
            os.remove(tmp_video)
    except OSError:
        pass
    if r.returncode != 0:
        raise RuntimeError(r.stderr or "ffmpeg failed while muxing subtitled video")
    return output_path


def _add_subtitles_ffmpeg_drawtext(
    video_path,
    words,
    style,
    output_path,
    mode="word",
    min_words=2,
    max_words=4,
):
    units, get_text, get_start, get_end = _prepare_units(words, mode, min_words, max_words)

    font_size = int(style.get("font_size", 48))
    color_hex = _hex_rgb(style.get("color"))
    opacity = float(style.get("opacity", 1))
    stroke_w = int(style.get("stroke_width", 0))
    stroke_color = _hex_rgb(style.get("stroke_fill"))
    margin = int(style.get("margin", 50))

    fontfile = None
    if style.get("font_family") and os.path.isfile(style["font_family"]):
        fontfile = _escape_ffmpeg_value(style["font_family"])

    pos = style.get("position", "bottom")
    if pos == "top":
        x, y = "(w-text_w)/2", str(margin)
    elif pos == "center":
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    else:
        x, y = "(w-text_w)/2", f"h-text_h-{margin}-60"

    filters = []
    for u in units:
        text = _escape_ffmpeg_value(get_text(u))
        start = get_start(u)
        end = get_end(u)
        parts = [f"drawtext=text='{text}'"]
        if fontfile:
            parts.append(f"fontfile='{fontfile}'")
        parts += [
            f"fontsize={font_size}",
            f"fontcolor=0x{color_hex}@{opacity}",
            f"x={x}",
            f"y={y}",
            f"enable='between(t,{start},{end})'",
        ]
        if stroke_w > 0:
            parts.append(f"borderw={stroke_w}")
            parts.append(f"bordercolor=0x{stroke_color}")
        filters.append(":".join(parts))

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", ",".join(filters),
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return output_path


def add_subtitles(
    video_path,
    words,
    style,
    output_path,
    mode="word",
    min_words=2,
    max_words=4,
):
    if not _ffmpeg_exists():
        raise RuntimeError("ffmpeg not found")

    style = style or {}

    # Homebrew ffmpeg often ships without drawtext — prefer OpenCV burn-in.
    if _has_drawtext_filter():
        try:
            return _add_subtitles_ffmpeg_drawtext(
                video_path, words, style, output_path, mode, min_words, max_words
            )
        except Exception as e:
            print(f"⚠️  drawtext path failed, falling back to OpenCV: {e}")

    return _add_subtitles_opencv(
        video_path, words, style, output_path, mode, min_words, max_words
    )


if __name__ == "__main__":
    words = [
        {"word": "Thi's", "start": 0.2, "end": 0.5},
        {"word": "is", "start": 0.5, "end": 0.7},
        {"word": "a", "start": 0.7, "end": 0.9},
        {"word": "reel", "start": 0.9, "end": 1.3},
        {"word": "style", "start": 1.3, "end": 1.7},
        {"word": "subtitle", "start": 1.7, "end": 2.3},
    ]

    style = {
        "font_size": 48,
        "color": "#ffffff",
        "stroke_width": 2,
        "stroke_fill": "#000000",
        "position": "bottom",
        "margin": 60,
    }

    add_subtitles("trim.mp4", words, style, "out_line.mp4", mode="line")
