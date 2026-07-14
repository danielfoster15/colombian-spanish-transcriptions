"""Speaker-labeled transcription of YouTube videos and audio files using WhisperX."""

import os

# We only use torch; keep transformers from importing any TensorFlow install
# (an old TF compiled against numpy 1.x crashes on import under numpy 2.x).
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")

__version__ = "1.0.0"
