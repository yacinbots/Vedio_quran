from flask import Flask, request, send_file
import requests
import os
import random
import traceback

app = Flask(__name__)

PEXELS_API_KEY = "qNjzlhYlGozNW23Xlkzv7mPVjr7a2xzuOqvs1IqVraI6wU8QdDN9hDjC"

# -----------------------------
# PEXELS VIDEO
# -----------------------------
def get_video():
    url = "https://api.pexels.com/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": "nature",
        "per_page": 10
    }

    r = requests.get(url, headers=headers, params=params)
    data = r.json()

    videos = data.get("videos", [])
    if not videos:
        return None

    video = random.choice(videos)
    files = video.get("video_files", [])

    if not files:
        return None

    return files[0]["link"]


# -----------------------------
# QURAN API
# -----------------------------
def get_ayah():
    url = "https://api.alquran.cloud/v1/ayah/1:1/ar.alafasy"
    data = requests.get(url).json()["data"]

    return data["text"], data["audio"]


# -----------------------------
# GENERATE
# -----------------------------
@app.route("/generate", methods=["POST"])
def generate():

    try:
        text, audio = get_ayah()
        video_url = get_video()

        if not video_url:
            return {"error": "no video found"}

        print("Downloading video...")
        os.system(f"wget -q -O video.mp4 '{video_url}'")

        print("Downloading audio...")
        os.system(f"wget -q -O audio.mp3 '{audio}'")

        output = "output.mp4"

        # ⚠️ بدون drawtext (لتجنب crash)
        cmd = f"""
ffmpeg -y -i video.mp4 -i audio.mp3 -c:v libx264 -c:a aac -shortest {output}
"""

        os.system(cmd)

        return send_file(output, as_attachment=True)

    except Exception:
        print(traceback.format_exc())
        return {"error": "server crashed"}, 500


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return "Quran Video API Running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
