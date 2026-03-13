FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

RUN pip install --no-cache-dir cryptography

COPY lbh_sello.py ./

RUN mkdir -p /app/imagenes

ENTRYPOINT ["python3", "lbh_sello.py"]
