# LLM-as-a-Judge ve A/B Testi Ödevi

## Kurulum (bir kez)
```
python -m venv .venv            # (zaten kurulu)
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env          # sonra .env içine OpenRouter anahtarını yaz
```

## Klasörler
| Klasör | İçerik |
|---|---|
| `veri/` | `dataset.xlsx` (100 soru), `model_katalogu.xlsx` |
| `sonuclar/` | `sonuclar.xlsx` (betiğin çıktısı) |
| `rapor/` | Gerekçeli model raporu |
| `araclar/` | `baglanti_testi.py`, `model_katalogu.py` |

## Araçlar
- `.venv\Scripts\python araclar\baglanti_testi.py [model_id]` — anahtar ve bağlantı kontrolü
- `.venv\Scripts\python araclar\model_katalogu.py` — tüm modeller: fiyat / bağlam / temperature-top_p desteği
- `.venv\Scripts\python araclar\model_katalogu.py <model_id>` — o modelin sağlayıcıları (provider), quantization, fiyat

## Docker (bonus)
`docker compose up --build`
