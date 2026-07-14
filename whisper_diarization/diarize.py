"""Speaker diarization only: who speaks when, written as TSV and RTTM.

Usage:
    wd-diarize --ids fkxVtGHE6V4 --num-speakers 2
    wd-diarize --files interview.wav --outdir diarizations/
"""

import argparse
import os

import torch

from .utils import get_hf_token, read_video_ids


def parse_args():
    parser = argparse.ArgumentParser(
        description="Diarize speakers in YouTube videos or local audio files."
    )
    parser.add_argument("--ids", default="", help="Comma-separated YouTube video ids.")
    parser.add_argument("--urls-file", help="File with one YouTube URL or video id per line.")
    parser.add_argument("--files", nargs="*", default=[], help="Local audio files to process.")
    parser.add_argument("--outdir", default="diarizations/", help="Output directory.")
    parser.add_argument("--device", default=None, help="cuda or cpu (default: auto).")
    parser.add_argument("--num-speakers", type=int, help="Exact number of speakers, if known.")
    parser.add_argument("--min-speakers", type=int, help="Minimum number of speakers.")
    parser.add_argument("--max-speakers", type=int, help="Maximum number of speakers.")
    parser.add_argument("--hf-token", help="HuggingFace token (defaults to the HF_TOKEN env var).")
    return parser.parse_args()


def main():
    args = parse_args()
    ids = read_video_ids(args.urls_file, args.ids)
    if not ids and not args.files:
        raise SystemExit("No input given. Use --ids, --urls-file, and/or --files.")

    token = get_hf_token(args.hf_token)
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(args.outdir, exist_ok=True)

    import whisperx
    from .utils import download_audio

    diarize_model = whisperx.diarize.DiarizationPipeline(token=token, device=device)

    jobs = []
    for video_id in ids:
        wav_path, _title = download_audio(video_id, args.outdir)
        jobs.append((wav_path, video_id))
    for path in args.files:
        jobs.append((path, os.path.splitext(os.path.basename(path))[0]))

    for audio_path, stem in jobs:
        print(f"diarizing {audio_path}...")
        audio = whisperx.load_audio(audio_path)
        segments = diarize_model(
            audio,
            num_speakers=args.num_speakers,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
        )
        write_outputs(segments, args.outdir, stem)


def write_outputs(segments, outdir, stem):
    """Write a diarization DataFrame (start, end, speaker) as TSV and RTTM."""
    tsv_path = os.path.join(outdir, f"{stem}.tsv")
    rttm_path = os.path.join(outdir, f"{stem}.rttm")

    with open(tsv_path, "w") as f:
        f.write("start\tend\tspeaker\n")
        for row in segments.itertuples():
            f.write(f"{row.start:.3f}\t{row.end:.3f}\t{row.speaker}\n")

    with open(rttm_path, "w") as f:
        for row in segments.itertuples():
            f.write(
                f"SPEAKER {stem} 1 {row.start:.3f} {row.end - row.start:.3f} "
                f"<NA> <NA> {row.speaker} <NA> <NA>\n"
            )
    print(f"wrote {tsv_path} and {rttm_path}")


if __name__ == "__main__":
    main()
