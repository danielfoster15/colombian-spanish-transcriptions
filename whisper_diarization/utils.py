"""Shared helpers: video id parsing, downloads, tokens, timestamp formatting."""

import os

import yt_dlp


def get_hf_token(cli_value=None):
    """Return the HuggingFace token from --hf-token or the HF_TOKEN env var."""
    token = cli_value or os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit(
            "No HuggingFace token found. Set the HF_TOKEN environment variable "
            "or pass --hf-token. Create one at https://huggingface.co/settings/tokens "
            "(read access), and accept the pyannote speaker-diarization terms."
        )
    return token


def read_video_ids(urls_file=None, ids_arg=""):
    """Collect YouTube video ids from a file of URLs/ids and/or a comma-separated list."""
    ids = []
    if urls_file:
        with open(urls_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "v=" in line:
                    line = line.split("v=")[-1].split("&")[0]
                elif "youtu.be/" in line:
                    line = line.split("youtu.be/")[-1].split("?")[0]
                ids.append(line)
    if ids_arg:
        ids.extend(i.strip() for i in ids_arg.split(",") if i.strip())
    return ids


def download_audio(video_id, outdir):
    """Download a YouTube video's audio as <outdir>/<id>.wav. Returns (path, title)."""
    os.makedirs(outdir, exist_ok=True)
    wav_path = os.path.join(outdir, f"{video_id}.wav")
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(outdir, "%(id)s.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
        ],
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=not os.path.exists(wav_path))
    return wav_path, info.get("title", video_id)


def format_timestamp(seconds):
    """Seconds -> 'HH:MM:SS' display string."""
    seconds = max(seconds, 0)
    return "{:02d}:{:02d}:{:02d}".format(
        int(seconds // 3600), int(seconds % 3600 // 60), int(seconds % 60)
    )


def srt_timestamp(seconds):
    """Seconds -> 'HH:MM:SS,mmm' SRT timestamp."""
    seconds = max(seconds, 0)
    ms = int(round((seconds % 1) * 1000))
    return "{:02d}:{:02d}:{:02d},{:03d}".format(
        int(seconds // 3600), int(seconds % 3600 // 60), int(seconds % 60), ms
    )
