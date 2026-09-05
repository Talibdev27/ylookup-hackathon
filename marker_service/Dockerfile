# Marker needs Python 3.10+ and PyTorch -- both incompatible with the main app's
# Python 3.9 target and its single lightweight Render worker. This image is built and
# deployed on its own, to Cloud Run; see README.md in this directory.
FROM python:3.11-slim

# libgl1 / libglib2.0-0: the layout-detection models pull in opencv, which needs these
# even though nothing here does any GUI work.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Download the OCR/layout model weights now, so they are baked into the image instead
# of downloaded on the first real request. Without this, whoever hits the service first
# after a cold start waits for a multi-hundred-MB download on top of the cold start
# itself -- fine for a batch job, bad for a demo. This is the same trade the other
# direction: a larger, slower image build, for a fast and predictable first request.
RUN python -c "from marker.models import create_model_dict; create_model_dict()"

# Cloud Run sets $PORT and expects the container to listen on it. Shell form so the
# variable actually expands -- exec form would pass the literal string "$PORT" to uvicorn.
ENV PORT=8080
CMD uvicorn app:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 600
