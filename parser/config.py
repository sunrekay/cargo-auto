"""Runtime configuration, all overridable through the environment."""
import os
from pathlib import Path

DATA = Path("data")
IMAGES = DATA / "images"
RAW = DATA / "raw"            # per-car HTML, so data can be re-extracted offline
PROFILE = DATA / "profile"    # persistent browser profile (keeps the cleared check)
STATE = DATA / "state.json"
CARS_JSON = DATA / "cars.json"
CARS_CSV = DATA / "cars.csv"
LOG = DATA / "parser.log"

BASE_URL = os.getenv("BASE_URL", "https://en.guazi.com").rstrip("/")
CITY = os.getenv("CITY", "bin")
# Entry page. Query strings are stripped: robots.txt forbids them.
START_URL = os.getenv("START_URL", "").split("?")[0]

TARGET_CARS = int(os.getenv("TARGET_CARS", "150"))
MAX_IMAGES_PER_CAR = int(os.getenv("MAX_IMAGES_PER_CAR", "40"))
DOWNLOAD_IMAGES = os.getenv("DOWNLOAD_IMAGES", "1") == "1"

# Headed by default: it runs on the Xvfb display, which is also what lets a
# person take over through noVNC when the site asks for a human check.
HEADLESS = os.getenv("HEADLESS", "0") == "1"

REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2.5"))   # polite pause between pages
NAV_TIMEOUT = int(os.getenv("NAV_TIMEOUT", "60000"))
HUMAN_WAIT = int(os.getenv("HUMAN_WAIT", "900"))           # seconds to wait for a human
IMAGE_CONCURRENCY = int(os.getenv("CONCURRENCY", "4"))

USER_AGENT = os.getenv("USER_AGENT", (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"))

for d in (DATA, IMAGES, RAW, PROFILE):
    d.mkdir(parents=True, exist_ok=True)
