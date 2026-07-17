FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Hisob-faktura PDF'i uchun kirill+lotin shrifti (matnda "АНДИЖОН" ham,
# "MAS'ULIYATI CHEKLANGAN" ham bor — reportlab ichki shriftlarida kirill yo'q).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]

