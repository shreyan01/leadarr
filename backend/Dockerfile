FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Installed to a fixed path (PLAYWRIGHT_BROWSERS_PATH above) rather than
# the installing user's home directory. This step runs as root, but the
# container runs as the unprivileged `leadforge` user below — without a
# fixed shared path, root's browser install lands in /root/.cache and is
# invisible to the leadforge user at runtime ("Executable doesn't exist").
# No `|| true` here: if this fails, the build should fail loudly, not
# silently produce an image that's broken at first real use.
RUN playwright install --with-deps chromium && chmod -R a+rx /ms-playwright

COPY . .

RUN useradd --create-home --uid 1000 leadforge && \
    mkdir -p /app/storage && chown -R leadforge:leadforge /app
USER leadforge

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]