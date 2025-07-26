FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# Copiar requirements.txt desde la carpeta app
COPY app/requirements.txt .
RUN pip install -r requirements.txt

# Copiar todo el código desde la carpeta app
COPY app/ .

# Copiar también el .env (está en la raíz)
COPY .env .

# Copiar firebase credentials si existe
COPY app/firebase-credentials.json* ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]