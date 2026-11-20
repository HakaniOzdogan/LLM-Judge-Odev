# LLM-as-a-Judge ve A/B Testi Ödevi

## Kurulum (bir kez)
```
python -m venv .venv            # (zaten kurulu)
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env          # sonra .env içine OpenRouter anahtarını yaz
```

## Deneyi çalıştırma
1. Ayarları gözden geçir: `ayarlar.py` (modeller, sağlayıcılar, temperature/top_p deneyleri, tekrar sayısı, hakem)
2. Pilot (ilk 5 soru): `.venv\Scripts\python topla.py --n 5` → `.venv\Scripts\python hakem.py`
3. Tam deney: `.venv\Scripts\python topla.py` → `.venv\Scripts\python hakem.py`

İki betik de her çağrıdan sonra kayıt alır; yarıda kesilirse aynı komutla kaldığı yerden devam eder.
`hakem.py --sadece-excel` API çağrısı yapmadan Excel'i yeniden üretir.

| Dosya | İçerik |
|---|---|
| `sonuclar/ham_cevaplar.csv` | Her model çağrısı: cevap, token, maliyet, süre, sağlayıcı, hata |
| `sonuclar/hakem_puanlari.csv` | Her cevabın hakem puanı ve gerekçesi |
| `sonuclar/sonuclar.xlsx` | **Sonuçlar** (rehberdeki geniş tablo), **Özet** (model × ayar / kategori / zorluk), **Kararlılık** (tekrar > 1 ise), **Ham Veri** |

## Klasörler
| Klasör | İçerik |
|---|---|
| `veri/` | `dataset.xlsx` (100 soru), `model_katalogu.xlsx` |
| `sonuclar/` | `sonuclar.xlsx` (betiğin çıktısı) |
| `rapor/` | Gerekçeli model raporu |
| `araclar/` | `baglanti_testi.py`, `model_katalogu.py`, `seed_testi.py`, `hakem_karsilastirma.py` |

## Araçlar
- `.venv\Scripts\python araclar\baglanti_testi.py [model_id]` — anahtar ve bağlantı kontrolü
- `.venv\Scripts\python araclar\model_katalogu.py` — tüm modeller: fiyat / bağlam / temperature-top_p desteği
- `.venv\Scripts\python araclar\model_katalogu.py <model_id>` — o modelin sağlayıcıları (provider), quantization, fiyat

## Docker (bonus)
`docker compose up --build`
