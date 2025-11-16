from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media"
IMAGE_DIR = MEDIA_DIR / "images"
HTML_TAG_RE = re.compile(r"<[^>]+>")
IMG_TAG_RE = re.compile(r"<img[^>]*?>", re.IGNORECASE)
IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\'>]+)["\']', re.IGNORECASE)
SOUND_TAG_RE = re.compile(r"\[sound:[^\]]+\]")
NBSP_RE = re.compile(r"&nbsp;?", re.IGNORECASE)
