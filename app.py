
from flask import Flask, request, send_file
import requests
import os
import random
import traceback
import subprocess

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

PEXELS_API_KEY = "qNjzlhYlGozNW23Xlkzv7mPVjr7a2xzuOqvs1IqVraI6wU8QdDN9hDjC"

# -----------------------------
# DOWNLOAD FILE
# -----------------------------
def download(url, path):
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)

# -----------------------------
# GET VIDEO (LOW QUALITY)
# -----------------------------
def get_video():
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}

    params = {
        "query": "nature",
        "per_page": 5
    }

    r = requests.get(url, headers=headers, params=params, timeout=20)
    data = r.json()

    videos = data.get("videos", [])
    if not videos:
        return None

    random.shuffle(videos)

    for v in videos:
        files = sorted(v.get("video_files", []), key=lambda x: x.get("width", 9999))
        for f in files:
            if f.get("width", 0) <= 640:
                return f["link"]

    return None

# -----------------------------
# QURAN AYAH
# -----------------------------
def get_ayah(surah, ayah):
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/ar.alafasy"
    r = requests.get(url, timeout=20)
    data = r.json()["data"]

    return {
        "text": data["text"],
        "audio": data["audio"],
        "surah": data["surah"]["name"],
        "ayah": data["numberInSurah"]
    }

# -----------------------------
# CREATE ARABIC OVERLAY IMAGE
# -----------------------------
def create_overlay(text, footer):
    W, H = 1280, 720

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_main = ImageFont.truetype("Amiri-Regular.ttf", 54)
    font_footer = ImageFont.truetype("Amiri-Regular.ttf", 32)

    text = get_display(arabic_reshaper.reshape(text))
    footer = get_display(arabic_reshaper.reshape(footer))

    bbox = draw.textbbox((0, 0), text, font=font_main)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]

    x = (W - tw) // 2
    y = (H - th) // 2

    draw.text((x, y), text, font=font_main, fill="white")

    bbox2 = draw.textbbox((0, 0), footer, font=font_footer)
    fw = bbox2[2]-bbox2[0]

    draw.text(((W-fw)//2, H-80), footer, font=font_footer, fill="white")

    img.save("overlay.png")

# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return "Quran Video API Running"

# -----------------------------
# GENERATE VIDEO
# -----------------------------
@app.route("/generate", methods=["GET"])
def generate():
    files = []

    try:
        surah = request.args.get("surah", "1")
        ayah = request.args.get("ayah", "1")

        info = get_ayah(surah, ayah)
        video_url = get_video()

        if not video_url:
            return {"error": "no video"}, 500

        download(video_url, "video.mp4")
        download(info["audio"], "audio.mp3")

        files += ["video.mp4", "audio.mp3"]

        # shorten video
        subprocess.run([
            "ffmpeg", "-y",
            "-i", "video.mp4",
            "-t", "25",
            "-vf", "scale=720:-2",
            "small.mp4"
        ])

        files.append("small.mp4")

        footer = f"{info['surah']} | آية {info['ayah']}"
        create_overlay(info["text"], footer)

        files.append("overlay.png")

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "2",
            "-i", "small.mp4",
            "-i", "audio.mp3",
            "-i", "overlay.png",
            "-filter_complex", "[0:v][2:v]overlay=0:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "30",
            "-c:a", "aac",
            "-shortest",
            "output.mp4"
        ]

        subprocess.run(cmd, capture_output=True)

        return send_file("output.mp4", as_attachment=True)

    except Exception:
        print(traceback.format_exc())
        return {"error": "failed"}, 500

    finally:
        for f in files + ["output.mp4"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
