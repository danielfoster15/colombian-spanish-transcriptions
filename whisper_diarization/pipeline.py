"""End-to-end pipeline: YouTube/local audio -> WhisperX transcription + alignment
+ speaker diarization -> speaker-labeled JSON/SRT/TXT/HTML transcripts.

This replaces the tutorial notebook. Typical use:

    export HF_TOKEN=hf_...
    wd-pipeline --ids fkxVtGHE6V4 --language es --num-speakers 2
    wd-pipeline --urls-file video_links.txt --outdir outputs/
    wd-pipeline --files interview.wav --no-diarize
"""

import argparse
import gc
import os
import re

import torch

from .output import write_all
from .utils import get_hf_token, read_video_ids

YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Transcribe and diarize YouTube videos or local audio files with WhisperX."
    )
    src = parser.add_argument_group("input")
    src.add_argument("--ids", default="", help="Comma-separated YouTube video ids.")
    src.add_argument("--urls-file", help="File with one YouTube URL or video id per line.")
    src.add_argument("--files", nargs="*", default=[], help="Local audio files to process.")

    parser.add_argument("--outdir", default="outputs/", help="Directory for audio and transcripts.")
    parser.add_argument("--language", default=None,
                        help="Language code, e.g. es, en (default: auto-detect).")
    parser.add_argument("--model", default="large-v3",
                        help="Whisper model size (default: large-v3).")
    parser.add_argument("--device", default=None, help="cuda or cpu (default: auto).")
    parser.add_argument("--compute-type", default=None,
                        help="ctranslate2 compute type (default: float16 on cuda, int8 on cpu).")
    parser.add_argument("--batch-size", type=int, default=8, help="Transcription batch size.")
    parser.add_argument("--html-style", choices=["auto", "speaker", "classic"], default="auto",
                        help="HTML layout: 'speaker' labels, 'classic' original layout "
                             "(no speakers, feeds wd-highlight), or 'auto' (default: classic "
                             "when not diarizing, speaker when diarizing).")

    dia = parser.add_argument_group("diarization")
    dia.add_argument("--no-diarize", action="store_true", help="Transcription only, no speakers.")
    dia.add_argument("--num-speakers", type=int, help="Exact number of speakers, if known.")
    dia.add_argument("--min-speakers", type=int, help="Minimum number of speakers.")
    dia.add_argument("--max-speakers", type=int, help="Maximum number of speakers.")
    dia.add_argument("--hf-token", help="HuggingFace token (defaults to the HF_TOKEN env var).")
    return parser.parse_args()


def main():
    args = parse_args()
    ids = read_video_ids(args.urls_file, args.ids)
    if not ids and not args.files:
        raise SystemExit("No input given. Use --ids, --urls-file, and/or --files.")

    hf_token = None if args.no_diarize else get_hf_token(args.hf_token)
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    compute_type = args.compute_type or ("float16" if device == "cuda" else "int8")
    os.makedirs(args.outdir, exist_ok=True)

    # Imported late: whisperx pulls in torch/ctranslate2 and takes a while.
    import whisperx
    from .utils import download_audio

    print(f"loading whisper model '{args.model}' on {device} ({compute_type})")
    model = whisperx.load_model(
        args.model, device, compute_type=compute_type, language=args.language
    )

    jobs = []  # (audio_path, output stem, page title, youtube id or None)
    for video_id in ids:
        wav_path, title = download_audio(video_id, args.outdir)
        jobs.append((wav_path, video_id, title, video_id))
    for path in args.files:
        stem = os.path.splitext(os.path.basename(path))[0]
        # If a local file is named after its YouTube id (e.g. 0RJMxQOi2zQ.wav),
        # reuse it so the HTML player links back to the video without downloading.
        video_id = stem if YT_ID_RE.match(stem) else None
        jobs.append((path, stem, stem, video_id))

    for audio_path, stem, title, video_id in jobs:
        process_one(audio_path, stem, title, video_id, model, device, hf_token, args)

    print("done")


def process_one(audio_path, stem, title, video_id, model, device, hf_token, args):
    import whisperx

    print(f"\n=== {title} ({audio_path}) ===")
    audio = whisperx.load_audio(audio_path)

    print("transcribing...")
    result = model.transcribe(audio, batch_size=args.batch_size, language=args.language)
    language = result["language"]

    print(f"aligning ({language})...")
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, device,
        return_char_alignments=False,
    )
    del align_model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    if not args.no_diarize:
        print("diarizing speakers...")
        diarize_model = whisperx.diarize.DiarizationPipeline(
            token=hf_token, device=device
        )
        diarize_segments = diarize_model(
            audio,
            num_speakers=args.num_speakers,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
        )
        result = whisperx.assign_word_speakers(diarize_segments, result)
        del diarize_model
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()

    paths = write_all(result["segments"], args.outdir, stem, title, video_id,
                      html_style=args.html_style)
    print("wrote:\n  " + "\n  ".join(paths))


if __name__ == "__main__":
    main()
