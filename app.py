from flask import Flask, request, send_file
import requests
import os
import random

app = Flask(__name__)

# -----------------------------
# PEXELS API
# -----------------------------
PEXELS_API_KEY = "qNjzlhYlGozNW23Xlkzv7mPVjr7a2xzuOqvs1IqVraI6wU8QdDN9hDjC"

def get_video():
    url = "https://api.pexels.com/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": "nature",
        "per_page": 10
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    videos = data.get("videos", [])

    if not videos:
        return None

    video = random.choice(videos)
    files = video.get("video_files", [])

    # نختار أفضل جودة
    for f in files:
        if f.get("quality") == "sd" or f.get("quality") == "hd":
            return f.get("link")

    return files[0].get("link") if files else None


# -----------------------------
# QURAN API
# -----------------------------
def get_ayah():
    url = "https://api.alquran.cloud/v1/ayah/1:1/ar.alafasy"
    data = requests.get(url).json()["data"]

    text = data["text"]
    audio = data["audio"]

    return text, audio


# -----------------------------
# GENERATE VIDEO
# -----------------------------
@app.route("/generate", methods=["POST"])
def generate():

    # جلب البيانات
    text, audio = get_ayah()
    video_url = get_video()

    if not video_url:
        return {"error": "no video found"}

    # تحميل الملفات
    os.system(f"wget -O video.mp4 '{video_url}'")
    os.system(f"wget -O audio.mp3 '{audio}'")

    output = "output.mp4"

    # تنظيف النص (مهم لـ ffmpeg)
    text_clean = text.replace("'", "").replace(":", "")

    # FFmpeg تركيب الفيديو
    cmd = f"""
ffmpeg -y -i video.mp4 -i audio.mp3 -vf 
"drawtext=text='{text_clean}':fontsize=45:fontcolor=white:
x=(w-text_w)/2:y=(h-text_h)/2:
box=1:boxcolor=black@0.5:boxborderw=20"
-c:v libx264 -c:a aac -shortest {output}
"""

    os.system(cmd)

    return send_file(output, as_attachment=True)


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
