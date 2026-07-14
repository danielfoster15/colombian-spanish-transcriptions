"""Writers for the pipeline result: JSON, SRT, TXT, and a clickable speaker-labeled HTML page."""

import html
import json
import os

from .utils import format_timestamp, srt_timestamp

SPEAKER_COLORS = ["#0b5394", "#990000", "#38761d", "#741b47", "#b45f06", "#134f5c"]

HTML_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{ font-family: sans-serif; font-size: 18px; color: #111; max-width: 60em;
           padding: 0 1em 1em 1em; }}
    .c {{ margin: 0.4em 0; }}
    .ts a {{ color: #050; text-decoration: none; font-family: monospace; }}
    .spk {{ font-weight: bold; }}
    #player {{ position: sticky; top: 20px; float: right; }}
    {speaker_css}
  </style>
</head>
<body>
  <h2>{title}</h2>
{player}
"""

PLAYER_SNIPPET = """  <div id="player"></div>
  <script>
    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    document.getElementsByTagName('script')[0].parentNode.insertBefore(tag, document.getElementsByTagName('script')[0]);
    var player;
    function onYouTubeIframeAPIReady() {{
      player = new YT.Player('player', {{ height: '210', width: '340', videoId: '{video_id}' }});
    }}
    function seek(t) {{ player.seekTo(t); player.playVideo(); }}
  </script>
"""

HTML_FOOTER = "</body>\n</html>\n"


def speaker_labels(segments):
    """Map raw pyannote labels (SPEAKER_00, ...) to stable display names and colors."""
    order = []
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        if spk not in order:
            order.append(spk)
    return {
        spk: (f"Speaker {i + 1}" if spk != "UNKNOWN" else "Unknown",
              SPEAKER_COLORS[i % len(SPEAKER_COLORS)])
        for i, spk in enumerate(order)
    }


def write_json(segments, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"segments": segments}, f, ensure_ascii=False, indent=2)


def write_srt(segments, path, labels):
    with open(path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            name = labels[seg.get("speaker", "UNKNOWN")][0]
            f.write(f"{i}\n{srt_timestamp(seg['start'])} --> {srt_timestamp(seg['end'])}\n")
            f.write(f"[{name}] {seg['text'].strip()}\n\n")


def write_txt(segments, path, labels):
    with open(path, "w", encoding="utf-8") as f:
        for seg in segments:
            name = labels[seg.get("speaker", "UNKNOWN")][0]
            f.write(f"[{format_timestamp(seg['start'])}] {name}: {seg['text'].strip()}\n")


def write_html(segments, path, labels, title, video_id=None):
    """Clickable transcript; if video_id is given, timestamps seek an embedded YouTube player."""
    speaker_css = "\n    ".join(
        f".spk-{i} {{ color: {color}; }}"
        for i, (_name, color) in enumerate(labels.values())
    )
    css_class = {spk: f"spk-{i}" for i, spk in enumerate(labels)}
    player = PLAYER_SNIPPET.format(video_id=video_id) if video_id else ""

    parts = [HTML_HEADER.format(title=html.escape(title), speaker_css=speaker_css, player=player)]
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        name, _color = labels[spk]
        stamp = format_timestamp(seg["start"])
        if video_id:
            ts = f'<a href="javascript:void(0);" onclick="seek({int(seg["start"])})">{stamp}</a>'
        else:
            ts = stamp
        parts.append(
            f'  <div class="c"><span class="ts">{ts}</span> '
            f'<span class="spk {css_class[spk]}">{html.escape(name)}:</span> '
            f'<span class="t">{html.escape(seg["text"].strip())}</span></div>\n'
        )
    parts.append(HTML_FOOTER)

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(parts))


def write_all(segments, outdir, stem, title, video_id=None):
    """Write JSON/SRT/TXT/HTML for one video. Returns the list of paths written."""
    labels = speaker_labels(segments)
    paths = {
        "json": os.path.join(outdir, f"{stem}.json"),
        "srt": os.path.join(outdir, f"{stem}.srt"),
        "txt": os.path.join(outdir, f"{stem}.txt"),
        "html": os.path.join(outdir, f"{stem}_transcript.html"),
    }
    write_json(segments, paths["json"])
    write_srt(segments, paths["srt"], labels)
    write_txt(segments, paths["txt"], labels)
    write_html(segments, paths["html"], labels, title, video_id)
    return list(paths.values())
