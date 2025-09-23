FROM #{Docker.Internal.Registry}#/library/python:3.13.0-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN mkdir -p /home/sign/{input,output,backup}


ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FOLDER_PATH_SYNC=/home/sign

CMD ["python", "-m", "src.main"]