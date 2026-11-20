# BONUS iskeleti. Ana betiğini yazınca CMD satırındaki dosya adını güncelle.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Anahtar imaja GÖMÜLMEZ; çalıştırırken verilir:  docker compose up  (env_file: .env)
CMD ["python", "araclar/baglanti_testi.py"]
