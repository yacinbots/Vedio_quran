from flask import Flask, request, send_file
import requests
import os
import random
import traceback

app = Flask(__name__)

PEXELS_API_KEY = "qNjzlhYlGozNW23Xlkzv7mPVjr7a2xzuOqvs1IqVraI6wU8QdDN9hDjC"


# -----------------------------
# GET MULTIPLE AYAT
# -----------------------------
def get_ayahs(surah, start, count=3):
    ayahs = []
    audios = []

    for i in range(start, start + count):
        url = f"https://api.alquran.cloud/v1/ayah/{surah}:{i}/ar.alafasy"
        data = requests.get(url).json()["data"]

        ayahs.append({
            "text": data["text"],
            "audio": data["audio"],
            "number": data["numberInSurah"]
        })

        audios.append(data["audio"])

    return ayahs, audios


# -----------------------------
# PEXELS VIDEOS (MULTI)
# -----------------------------
def get_videos(count=3):
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}

    params = {"query": "nature", "per_page": 15}

    r = requests.get(url, headers=headers, params=params).json()
    videos = r.get("videos", [])

    links = []

    for v in random.sample(videos, min(count, len(videos))):
        files = v.get("video_files", [])
        if files:
            links.append(files[0]["link"])

    return links


# -----------------------------
# GENERATE VIDEO
# -----------------------------
@app.route("/generate", methods=["GET"])
def generate():

    try:
        surah = request.args.get("surah", "1")
        start = int(request.args.get("ayah", "1"))
        count = int(request.args.get("count", "3"))

        ayahs, audios = get_ayahs(surah, start, count)
        video_links = get_videos(count)

        # -----------------------------
        # DOWNLOAD AUDIO (MERGE)
        # -----------------------------
        audio_files = []

        for i, a in enumerate(audios):
            fname = f"audio{i}.mp3"
            os.system(f"wget -q -O {fname} '{a}'")
            audio_files.append(fname)

        # دمج الصوت
        with open("audio_list.txt", "w") as f:
            for a in audio_files:
                f.write(f"file '{a}'\n")

        os.system("ffmpeg -y -f concat -safe 0 -i audio_list.txt -c copy full_audio.mp3")

        # -----------------------------
        # DOWNLOAD VIDEOS
        # -----------------------------
        video_files = []

        for i, v in enumerate(video_links):
            fname = f"video{i}.mp4"
            os.system(f"wget -q -O {fname} '{v}'")
            video_files.append(fname)

        # دمج الفيديوهات
        with open("video_list.txt", "w") as f:
            for v in video_files:
                f.write(f"file '{v}'\n")

        os.system("ffmpeg -y -f concat -safe 0 -i video_list.txt -c copy full_video.mp4")

        # -----------------------------
        # LOOP VIDEO IF SHORT
        # -----------------------------
        cmd = """
ffmpeg -y -stream_loop 10 -i full_video.mp4 -i full_audio.mp3 -vf "
drawtext=text='Quran Video':
fontsize=40:fontcolor=white:
x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.5
" -c:v libx264 -c:a aac -shortest output.mp4
"""

        os.system(cmd)

        return send_file("output.mp4", as_attachment=True)

    except Exception:
        print(traceback.format_exc())
        return {"error": "failed"}, 500


@app.route("/")
def home():
    return "Multi Ayah Quran Video API"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
