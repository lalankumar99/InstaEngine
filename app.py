
import os
import re
import glob
import shutil
import tempfile
import yt_dlp

from flask import (
    Flask, render_template, request,
    jsonify, send_file
)

app = Flask(__name__)

os.makedirs("templates", exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/insta-download", methods=["GET"])
def insta_download():

    video_url = request.args.get("url", "").strip()

    if not video_url:
        return jsonify({
            "success": False,
            "error": "Instagram video URL is required."
        }), 400

    # Allow Instagram URLs only
    if not re.match(
        r"^https?://(www\.)?instagram\.com/",
        video_url
    ):
        return jsonify({
            "success": False,
            "error": "Please provide a valid Instagram URL."
        }), 400

    temp_dir = tempfile.mkdtemp(prefix="lk_insta_")

    try:

        ydl_opts = {
            # Download actual video with audio
            "format": (
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                "best[ext=mp4]/best"
            ),

            # Merge into MP4
            "merge_output_format": "mp4",

            # Save downloaded video
            "outtmpl": os.path.join(
                temp_dir,
                "%(title).80s-%(id)s.%(ext)s"
            ),

            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,

            # No audio-only downloads
            "postprocessors": [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4"
                }
            ],

            "overwrites": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                video_url,
                download=True
            )

        # Find final MP4 video
        mp4_files = glob.glob(
            os.path.join(temp_dir, "*.mp4")
        )

        if not mp4_files:
            raise Exception(
                "MP4 video could not be generated. "
                "Check FFmpeg installation."
            )

        video_file = max(
            mp4_files,
            key=os.path.getsize
        )

        if os.path.getsize(video_file) == 0:
            raise Exception("Downloaded video is empty.")

        # Original video quality is preserved;
        # no artificial 4K upscaling.
        response = send_file(
            video_file,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="Instagram_Video.mp4"
        )

        # Clean temporary files after response
        response.call_on_close(
            lambda: shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )
        )

        return response

    except Exception as e:

        print("[InstaEngine Error]", str(e))

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        return jsonify({
            "success": False,
            "error": (
                "Video download failed. "
                "Make sure the video is publicly accessible "
                "and you have permission to download it."
            )
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )