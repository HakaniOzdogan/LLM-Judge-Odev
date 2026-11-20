# BONUS: tüm deneyi konteynerde çalıştırır (toplama → hakem → sonuclar.xlsx).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Anahtar imaja GÖMÜLMEZ; çalıştırırken verilir:  docker compose up  (env_file: .env)
CMD ["sh", "-c", "python topla.py && python hakem.py"]
