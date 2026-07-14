# Colombian Spanish transcriptions

Speaker-labeled transcription of YouTube videos and audio files, built on
[WhisperX](https://github.com/m-bain/whisperX) (faster-whisper transcription +
wav2vec2 word alignment + pyannote speaker diarization). Given a video or an
audio file, it produces a transcript that says *who* said *what* and *when*,
as JSON, SRT, TXT, and a clickable HTML page with an embedded player.

Tuned for Spanish-language material, but the language is configurable and
auto-detected by default.

## Quick start

```bash
pip install -e .
# ffmpeg must be on your PATH (e.g. apt install ffmpeg)

# Diarization needs a HuggingFace token with access to the gated
# pyannote/speaker-diarization-community-1 model:
# https://huggingface.co/settings/tokens (accept the model's terms first)
export HF_TOKEN=hf_your_token_here
```

## Commands

| Command | Purpose |
|---|---|
| `wd-pipeline` | End-to-end: download → transcribe → align → diarize → speaker-labeled JSON/SRT/TXT/HTML |
| `wd-diarize` | Diarization only: who speaks when, as TSV + RTTM |
| `wd-highlight` | Highlight 2nd-person-singular (voseo/tuteo) verb forms in HTML transcripts with spaCy |

```bash
# One YouTube video, Spanish, two speakers -> outputs/<id>_transcript.html etc.
wd-pipeline --ids fkxVtGHE6V4 --language es --num-speakers 2

# Batch: every video listed in video_links.txt (one URL or id per line)
wd-pipeline --urls-file video_links.txt --outdir outputs/

# Local audio file, transcription only (no HF token needed)
wd-pipeline --files interview.wav --no-diarize

# Diarize only
wd-diarize --ids fkxVtGHE6V4 --num-speakers 2

# Highlight voseo forms in transcripts placed in <dir>/original/
wd-highlight --dir my_transcripts --spacy-model es_dep_news_trf
```

Useful `wd-pipeline` flags: `--model` (default `large-v3`; use `small` for quick
runs), `--device cuda|cpu` (auto-detected), `--batch-size`,
`--min-speakers` / `--max-speakers` when the exact speaker count is unknown, and
`--html-style` (`speaker`, `classic`, or `auto`).

### Reproducing the "classic" voseo transcripts

The original workflow for this project produced clickable HTML transcripts with
no speaker labels, then highlighted informal 2nd-person forms (voseo/tuteo). To
regenerate that from already-downloaded audio (filenames that are YouTube ids
get a working player link automatically):

```bash
# 1. Transcribe -> classic HTML (auto-selected because --no-diarize means no speakers)
wd-pipeline --files /path/to/audio/*.wav --language es --no-diarize --outdir outputs/show

# 2. Highlight voseo forms
mkdir -p outputs/show_hl/original && cp outputs/show/*_transcript.html outputs/show_hl/original/
wd-highlight --dir outputs/show_hl
# -> outputs/show_hl/modified/*.html
```

## Output

For each input, `wd-pipeline` writes four files into `--outdir` (default
`outputs/`):

- `<name>.json` — full segments with start/end times, text, and speaker labels
- `<name>.srt` — subtitles, each cue prefixed with `[Speaker N]`
- `<name>.txt` — plain reading transcript, one line per segment
- `<name>_transcript.html` — clickable transcript; for YouTube inputs the
  timestamps seek an embedded player

Speakers are labeled `Speaker 1`, `Speaker 2`, … in the order they first speak.

Downloaded audio and generated transcripts go to git-ignored output directories,
so the repository only tracks code and docs.

## Layout

```
whisper_diarization/     the package
  pipeline.py            wd-pipeline: end-to-end transcribe + diarize
  diarize.py             wd-diarize: diarization only (TSV/RTTM)
  postprocess.py         wd-highlight: voseo/tuteo highlighter
  output.py              JSON/SRT/TXT/HTML writers
  utils.py               downloads, video-id parsing, timestamps
video_links.txt          YouTube URLs/ids for batch runs
pyproject.toml           package + console-script definitions
transcription_diarization.ipynb   the original manual walkthrough (see below)
```

## Background

This project grew out of a lablab.ai tutorial that did the same task manually in
a notebook: run pyannote to get speaker segments, splice the audio with silence
spacers, transcribe each chunk with Whisper, then stitch the pieces back into an
HTML transcript. That approach still lives in
[`transcription_diarization.ipynb`](transcription_diarization.ipynb) for
reference. The package here replaces it with WhisperX, which does transcription,
word-level alignment, and diarization in one pass with proper word-to-speaker
assignment instead of the spacer-splicing workaround.

## Credits

Based on the lablab.ai tutorial
[**Whisper transcription and diarization (speaker-identification)**](https://github.com/lablab-ai/Whisper-transcription_and_diarization-speaker-identification-).
Built with [WhisperX](https://github.com/m-bain/whisperX),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[OpenAI Whisper](https://github.com/openai/whisper), and
[pyannote.audio](https://github.com/pyannote/pyannote-audio).
