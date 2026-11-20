r"""OpenRouter'daki TÜM modelleri fiyat, bağlam ve parametre desteğiyle Excel'e döker.
Model SEÇİMİ senin işin (ödev kuralı) — bu araç sadece karşılaştırmayı kolaylaştırır.
Anahtar gerekmez. Çalıştır:  .venv\Scripts\python araclar\model_katalogu.py
Sağlayıcı (provider) detayı için:  ... model_katalogu.py qwen/qwen3-32b
"""
import sys, requests, pandas as pd

if len(sys.argv) > 1:  # tek modelin sağlayıcıları
    mid = sys.argv[1]
    d = requests.get(f"https://openrouter.ai/api/v1/models/{mid}/endpoints", timeout=30).json()["data"]
    rows = [{
        "provider": e.get("provider_name"),
        "quantization": e.get("quantization"),
        "context": e.get("context_length"),
        "input_$/1M": float(e["pricing"]["prompt"]) * 1e6,
        "output_$/1M": float(e["pricing"]["completion"]) * 1e6,
        "uptime_30m": e.get("uptime_last_30m"),
        "params": ", ".join(e.get("supported_parameters") or []),
    } for e in d["endpoints"]]
    df = pd.DataFrame(rows)
    print(df.to_string())
    out = f"veri/saglayicilar_{mid.replace('/', '_')}.xlsx"
else:
    d = requests.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
    rows = []
    for m in d:
        sp = m.get("supported_parameters") or []
        rows.append({
            "id": m["id"], "ad": m.get("name"),
            "input_$/1M": float(m["pricing"]["prompt"]) * 1e6,
            "output_$/1M": float(m["pricing"]["completion"]) * 1e6,
            "context": m.get("context_length"),
            "temperature": "temperature" in sp, "top_p": "top_p" in sp,
            "ucretsiz": m["id"].endswith(":free"),
        })
    df = pd.DataFrame(rows).sort_values("input_$/1M")
    print(f"{len(df)} model bulundu.")
    out = "veri/model_katalogu.xlsx"
df.to_excel(out, index=False)
print("Kaydedildi:", out)
