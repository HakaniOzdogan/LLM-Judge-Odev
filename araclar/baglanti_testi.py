r"""Altyapı kontrolü: .env okunuyor mu, OpenRouter anahtarı çalışıyor mu?
Çalıştır:  .venv\Scripts\python araclar\baglanti_testi.py  [model_id]
Varsayılan "openrouter/auto" çok küçük kredi harcar; ücretsiz test için ":free" ile biten bir model id ver.
"""
import os, sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY", "")
if not key or "BURAYA" in key:
    sys.exit("HATA: .env dosyasında OPENROUTER_API_KEY yok. .env.example'ı .env olarak kopyala.")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
model = sys.argv[1] if len(sys.argv) > 1 else "openrouter/auto"
try:
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Türkiye'nin başkenti neresidir? Tek kelimeyle cevap ver."}],
        temperature=0, max_tokens=20,
    )
    print("OK  model:", r.model)
    print("    cevap:", r.choices[0].message.content)
    print("    token:", r.usage)
except Exception as e:
    print("BAĞLANTI HATASI:", type(e).__name__, e)
    sys.exit(1)
