from flask import Flask, request, send_file
import requests
import os
import random
import traceback
import subprocess

app = Flask(__name__)

PEXELS_API_KEY = "qNjzlhYlGozNW23Xlkzv7mPVjr7a2xzuOqvs1IqVraI6wU8QdDN9hDjC"

# ---------- تحميل ملف ----------
def download(url, path):

    r = requests.get(url, stream=True, timeout=60)

    r.raise_for_status()

    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)


# ---------- جلب فيديو خفيف ----------
def get_video():

    url = "https://api.pexels.com/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": "nature",
        "per_page": 5
    }

    r = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=20
    )

    data = r.json()

    videos = data.get("videos", [])

    if not videos:
        return None

    random.shuffle(videos)

    for v in videos:

        files = sorted(
            v.get("video_files", []),
            key=lambda x: x.get("width", 9999)
        )

        for f in files:

            width = f.get("width", 0)

            # اختر جودة صغيرة لتقليل RAM
            if width <= 640:
                return f["link"]

    return None


# ---------- جلب الآية ----------
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


# ---------- الصفحة الرئيسية ----------
@app.route("/")
def home():

    return "Quran Video API Running"


# ---------- توليد الفيديو ----------
@app.route("/generate", methods=["GET"])
def generate():

    files_to_delete = []

    try:

        surah = request.args.get("surah", "1")
        ayah = request.args.get("ayah", "1")

        info = get_ayah(surah, ayah)

        video_url = get_video()

        if not video_url:
            return {"error": "No Pexels video found"}, 500

        # تحميل الفيديو والصوت
        download(video_url, "video.mp4")
        download(info["audio"], "audio.mp3")

        files_to_delete += [
            "video.mp4",
            "audio.mp3"
        ]

        # تقليل حجم الفيديو
        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", "video.mp4",
            "-t", "20",
            "-vf", "scale=720:-2",
            "small.mp4"
        ])

        files_to_delete.append("small.mp4")

        # تنظيف النص
        text = (
            info["text"]
            .replace("'", "")
            .replace(":", "")
        )

        footer = f"{info['surah']} | آية {info['ayah']}"

        output = "output.mp4"

        files_to_delete.append(output)

        # ffmpeg سريع وخفيف
        cmd = [
            "ffmpeg",
            "-y",

            "-stream_loop",
            "2",

            "-i",
            "small.mp4",

            "-i",
            "audio.mp3",

            "-vf",

            f"""
drawtext=
fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:
text='{text}':
fontsize=42:
fontcolor=white:
box=1:
boxcolor=black@0.45:
boxborderw=18:
x=(w-text_w)/2:
y=(h-text_h)/2,

drawtext=
fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:
text='{footer}':
fontsize=24:
fontcolor=white:
box=1:
boxcolor=black@0.4:
boxborderw=8:
x=(w-text_w)/2:
y=h-70
""",

            "-preset",
            "ultrafast",

            "-crf",
            "30",

            "-c:v",
            "libx264",

            "-c:a",
            "aac",

            "-shortest",

            output
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            print(result.stderr)

            return {
                "error": "ffmpeg failed",
                "details": result.stderr
            }, 500

        return send_file(
            output,
            as_attachment=True
        )

    except Exception:

        print(traceback.format_exc())

        return {
            "error": "server crashed"
        }, 500

    finally:

        # تنظيف الملفات
        for f in files_to_delete:

            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
