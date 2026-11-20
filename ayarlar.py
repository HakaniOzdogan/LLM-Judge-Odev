"""Deneyin tek ayar dosyası: 6 model (2 aile × ucuz/orta/pahalı), hakem ve ortak API ayarları.
Model ve sağlayıcı seçimleri kullanıcıya aittir (gerekçeler rapor/ klasöründe).
Fiyatlar 2026-11-20 tarihinde OpenRouter'dan çekildi ($ / 1M token).
"""

OPENROUTER_URL = "https://openrouter.ai/api/v1"

# saglayici: OpenRouter'daki sağlayıcı adı; quant: o sağlayıcıda birden fazla quantization varsa hangisi
# dusunur: modelde düşünme (reasoning) özelliği var mı. False ise reasoning parametresi hiç gönderilmez
#          (require_parameters açıkken tanınmayan parametre 404 "No endpoints found" hatası verir).
MODELLER = [
    # aile        kademe    model id                          sağlayıcı      quant   giriş   çıkış
    dict(aile="Qwen",    kademe="ucuz",   id="qwen/qwen3.7-flash",          saglayici="Alibaba",   quant=None,   giris=0.030, cikis=0.130, dusunur=True),
    dict(aile="Qwen",    kademe="orta",   id="qwen/qwen3.7-plus",           saglayici="Alibaba",   quant=None,   giris=0.320, cikis=1.280, dusunur=True),
    dict(aile="Qwen",    kademe="pahali", id="qwen/qwen3.7-max",            saglayici="Alibaba",   quant=None,   giris=1.475, cikis=4.425, dusunur=True),
    dict(aile="Mistral", kademe="ucuz",   id="mistralai/ministral-8b-2512", saglayici="Mistral",   quant=None,   giris=0.150, cikis=0.150, dusunur=False),
    dict(aile="Mistral", kademe="orta",   id="mistralai/mistral-large-2512",saglayici="Mistral",   quant=None,   giris=0.500, cikis=1.500, dusunur=False),
    dict(aile="Mistral", kademe="pahali", id="mistralai/mistral-medium-3-5",saglayici="Mistral",   quant=None,   giris=1.500, cikis=7.500, dusunur=True),
]


# Hakem: test edilen ailelerin (Qwen, Mistral) dışından. Seçim gerekçesi: araclar/hakem_karsilastirma.py
# (15 tuzaklı vaka × 2 tur: isabet 30/30, tutarlılık 15/15, 2.700 çağrı ≈ $0.51). Düşünme özelliği yok → temperature=0 doğrudan uygulanır.
HAKEM = dict(aile="OpenAI", id="openai/gpt-4.1-mini", saglayici="OpenAI", quant=None, giris=0.40, cikis=1.60, dusunur=False)
HAKEM_TEMPERATURE = 0

HAKEM_PROMPT = """Sen tarafsız bir sınav değerlendiricisisin. Görevin, DEĞERLENDİRİLEN CEVAP'ın REFERANS CEVAP ile ne kadar örtüştüğünü puanlamak.

Kurallar:
- SADECE REFERANS CEVABA göre değerlendir. Kendi bilgin referansla çelişse bile referansı doğru kabul et.
- Anlam önemlidir: farklı ifade, dil, uzunluk veya üslup puanı ETKİLEMEZ.
- Sayılarda makul yuvarlama ve yazım farkı (8.849 / 8848,86) doğru sayılır.
- Puan cetveli:
  100 = referansla anlamca tam örtüşüyor.
  50-90 = referans birden fazla parça içeriyorsa ve cevap bir kısmını doğru veriyorsa, doğru parça oranına göre.
  Cevap doğru kısmın yanında açıkça YANLIŞ ek bilgi içeriyorsa puanı düşür.
  0 = yanlış, çelişkili, kararsız ("A ya da B") veya cevap yok.
- [DEĞERLENDİRME NOTU] verilmişse (kabul edilebilir varyantlar, parça sayısı) ona uy.
- Sadece şu JSON'u döndür: {"skor": <0-100 tam sayı>, "gerekce": "<en fazla 1 cümle>"}"""

SISTEM_PROMPT = "Soruları kısa ve net cevapla. Açıklama yapma."
MAX_TOKENS = 300

# --- Deney tasarımı — SENİN KARARIN (ödev kuralı: temperature/top_p analizi öğrenciye ait) ---
# (temperature, top_p) çiftleri. Şimdilik defterdeki örnek değerler; analizine göre değiştir.
# Kontrollü deney: önce top_p=1 sabitken T değişir, sonra T sabitken top_p değişir.
DENEYLER = [(0.0, 1.0), (0.7, 1.0), (1.0, 1.0), (1.0, 0.5)]
TEKRAR = 1          # aynı soru + aynı ayar kaç kez sorulsun (kararlılık ölçümü için 2-3 yap)

# --- Çalıştırma ---
ESZAMANLI = 8       # aynı anda kaç API çağrısı
DENEME_SAYISI = 4   # geçici hatada (429/5xx/timeout/boş cevap) en fazla kaç deneme; arada 2, 4, 8 sn beklenir
TIMEOUT = 90        # saniye


def extra_body(m):
    """Her çağrıya eklenen OpenRouter alanları: düşünme kapalı + sağlayıcı sabit."""
    provider = {
        "order": [m["saglayici"]],
        "allow_fallbacks": False,     # başka sağlayıcıya kaçma
        "require_parameters": True,   # temperature/top_p/seed'i uygulamayan sağlayıcıyı kullanma
    }
    if m["quant"]:
        provider["quantizations"] = [m["quant"]]
    body = {"provider": provider}
    if m["dusunur"]:
        body["reasoning"] = {"enabled": False}
    return body


def maliyet(m, giris_token, cikis_token):
    return giris_token / 1e6 * m["giris"] + cikis_token / 1e6 * m["cikis"]
