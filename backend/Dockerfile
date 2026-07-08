FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# Debian's own apt `nodejs`/`npm` packages are notoriously inconsistent
# about where global npm installs actually land (prefix/PATH quirks that
# bit us here: `npm install -g lighthouse` reported success at build time
# but the binary wasn't reachable at runtime). Using Node's official
# NodeSource setup instead, which installs to the predictable, standard
# /usr/bin location.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Lighthouse CLI — the adapter in app/adapters/lighthouse_cli.py shells out
# to the `lighthouse` binary. Chrome discovery is wired up right after the
# Playwright install below, once a known-working Chromium actually exists
# in the image.
#
# The `lighthouse --version` check is deliberate: if the npm global install
# ever lands somewhere not on PATH again (exactly what happened with
# Debian's bundled npm), this makes the BUILD fail immediately with a clear
# error, instead of silently producing an image that only reveals the
# problem three retries into a real audit run, much later and much less
# debuggably.
RUN npm install -g lighthouse && lighthouse --version

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

# Lighthouse's bundled chrome-launcher needs its own way to find a Chrome
# binary. Rather than install a *second* separate Chromium via apt for it
# (tried this — Debian's minimal apt chromium was missing runtime
# libraries needed to actually launch headless, failing with "Unable to
# connect to Chrome"), point it at the Chromium Playwright just installed
# above with --with-deps, which is already confirmed to have everything it
# needs to run. CHROME_PATH is chrome-launcher's own documented override —
# checked before any auto-detection — so this is a supported, not hacky,
# way to wire this up. The actual binary lives in a versioned directory
# name that changes with Playwright releases, so a fixed-path symlink
# created here (not baked into the Dockerfile as a literal path) is what
# CHROME_PATH points at.
RUN ln -s "$(find /ms-playwright -type f -name chrome | head -n1)" /usr/local/bin/chrome-for-lighthouse
ENV CHROME_PATH=/usr/local/bin/chrome-for-lighthouse

COPY . .

RUN useradd --create-home --uid 1000 leadforge && \
    mkdir -p /app/storage && chown -R leadforge:leadforge /app
USER leadforge

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]