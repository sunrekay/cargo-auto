# Playwright official image: Chromium + all system deps preinstalled
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:99

WORKDIR /app

# uv resolves and installs an order of magnitude faster than pip.
# --system targets the image's interpreter; the distro's typing-extensions is
# apt-owned with no RECORD file, so it is replaced rather than upgraded.
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/
COPY requirements.txt .
RUN uv pip install --system --no-cache --reinstall-package typing-extensions \
        -r requirements.txt

# Xvfb + VNC so a human can watch the browser and clear the site's anti-bot
# check themselves. The parser never solves that check on its own.
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb x11vnc x11-utils novnc websockify \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY parser/ ./parser/
COPY tools/ ./tools/

EXPOSE 6080
VOLUME ["/app/data"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "-m", "parser.main"]
