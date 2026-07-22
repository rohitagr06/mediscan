# MediScan public demo image (Sprint 8.10) — slim, CPU-only, text-PDF.
FROM python:3.12-slim

# WeasyPrint's rendering libraries (pango / cairo / gdk-pixbuf) + base fonts.
# These are the Linux equivalent of the Homebrew libs used on macOS.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        libffi-dev \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code only (src/ layout; app.py puts src/ on sys.path).
COPY app.py ./
COPY src ./src

# Public-demo default; the host overrides $PORT at runtime.
ENV MEDISCAN_DEMO_MODE=1
EXPOSE 7860

CMD ["python", "app.py"]
