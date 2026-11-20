r"""Hakem adaylarını, doğru puanı önceden bilinen tuzaklı vakalarla karşılaştırır.
Ölçülenler: isabet (beklenen aralıkta mı), tutarlılık (aynı vaka 2 kez → aynı puan mı),
JSON hatası, 2.700 hakem çağrısının tahmini maliyeti, ortalama süre.
Çalıştır:  .venv\Scripts\python araclar\hakem_karsilastirma.py
"""
import json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ayarlar import HAKEM_PROMPT

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))

ADAYLAR = {  # id: (giriş $/1M, çıkış $/1M)
    "anthropic/claude-haiku-4.5": (1.0, 5.0),
    "anthropic/claude-sonnet-4.6": (3.0, 15.0),
    "openai/gpt-4.1-mini": (0.4, 1.6),
    "openai/gpt-4.1": (2.0, 8.0),
    "google/gemini-2.5-flash": (0.3, 2.5),
    "google/gemini-3.8-flash": (0.825, 4.125),
    "deepseek/deepseek-v4-pro": (0.9, 1.5),
    "x-ai/grok-4.7": (2.0, 6.0),
    "z-ai/glm-5.2": (0.62, 2.42),
}


# (soru, referans, değerlendirilen cevap, beklenen alt, beklenen üst, tuzak açıklaması)
VAKALAR = [
    ("Türkiye'nin başkenti neresidir?", "Ankara", "Türkiye Cumhuriyeti'nin başkenti Ankara'dır.", 100, 100, "doğru, uzun ifade"),
    ("Türkiye'nin başkenti neresidir?", "Ankara", "Başkent Ankara değil, İstanbul'dur.", 0, 10, "anahtar kelime var ama yanlış"),
    ("Türkiye'nin başkenti neresidir?", "Ankara", "Ankara ya da İstanbul olabilir.", 0, 20, "kararsız"),
    ("Türkiye'nin başkenti neresidir?", "Ankara", "The capital of Turkey is Ankara.", 100, 100, "farklı dil"),
    ("Everest Dağı'nın yüksekliği kaç metredir?", "8.849 metre", "8848,86 metre", 90, 100, "sayı yuvarlama"),
    ("Everest Dağı'nın yüksekliği kaç metredir?", "8.849 metre", "Yaklaşık 8.000 metre.", 0, 20, "kaba yanlış sayı"),
    ("Ümit Davala kariyerinde hangi kulüplerde oynadı?", "Galatasaray, Milan, Inter, Werder Bremen",
     "Galatasaray, Milan ve Inter'de oynadı.", 60, 85, "4 parçadan 3'ü"),
    ("Ümit Davala kariyerinde hangi kulüplerde oynadı?", "Galatasaray, Milan, Inter, Werder Bremen",
     "Milan ve Inter.", 35, 60, "4 parçadan 2'si"),
    ("Ümit Davala kariyerinde hangi kulüplerde oynadı?", "Galatasaray, Milan, Inter, Werder Bremen",
     "Galatasaray, Fenerbahçe ve Milan.", 20, 60, "2 doğru + 1 yanlış"),
    ("Nutuk'u kim yazmıştır?", "Mustafa Kemal Atatürk", "Atatürk", 100, 100, "kısa ama doğru"),
    ("İstanbul hangi yılda fethedildi?", "1453",
     "1453 yılında Fatih Sultan Mehmet fethetti; bu olayla Bizans'ın yeni başkenti Roma oldu.", 30, 80, "doğru + yanlış ek bilgi"),
    ("Suyun kimyasal formülü nedir?", "H2O", "H₂O", 100, 100, "yazım farkı"),
    ("Fransa'nın başkenti neresidir?", "Paris", "Bu konuda kesin bilgim yok.", 0, 0, "cevap yok"),
    ("Fransa'nın başkenti neresidir?", "Paris",
     "Fransa'nın başkenti, Seine Nehri kıyısında yer alan, Eyfel Kulesi ve Louvre Müzesi ile ünlü, ülkenin siyasi, "
     "ekonomik ve kültürel merkezi olan Paris şehridir. Paris aynı zamanda ülkenin en kalabalık şehridir.", 100, 100, "uzunluk tuzağı"),
    ("Türkiye sınırları içinde doğup denize dökülen en uzun nehir hangisidir?", "Kızılırmak", "Fırat", 0, 10,
     "referans yerine kendi bilgisini kullanma tuzağı"),
]


def parse(txt):
    m = re.search(r"\{.*\}", txt or "", re.S)  # ```json sarmalı / önündeki metin
    d = json.loads(m.group(0))
    return int(d["skor"])


def hakem(mid, v):
    soru, ref, cevap = v[:3]
    t = time.perf_counter()
    try:
        r = client.chat.completions.create(
            model=mid, temperature=0, max_tokens=2000, timeout=120,
            messages=[{"role": "system", "content": HAKEM_PROMPT},
                      {"role": "user", "content": f"[SORU]\n{soru}\n\n[REFERANS CEVAP]\n{ref}\n\n[DEĞERLENDİRİLEN CEVAP]\n{cevap}"}],
            response_format={"type": "json_object"})
        sn = time.perf_counter() - t
        try:
            skor = parse(r.choices[0].message.content)
        except Exception:
            skor = None
        return skor, r.usage.prompt_tokens, r.usage.completion_tokens, sn
    except Exception as e:
        return f"HATA {str(e)[:60]}", 0, 0, time.perf_counter() - t


def degerlendir(mid):
    with ThreadPoolExecutor(8) as ex:
        r1 = list(ex.map(lambda v: hakem(mid, v), VAKALAR))
        r2 = list(ex.map(lambda v: hakem(mid, v), VAKALAR))
    return mid, r1, r2


assert all(lo <= hi for *_, lo, hi, _ in VAKALAR) and parse('```json\n{"skor": 80, "gerekce": "x"}\n```') == 80

with ThreadPoolExecutor(len(ADAYLAR)) as ex:
    sonuclar = list(ex.map(degerlendir, ADAYLAR))

satirlar = []
for mid, r1, r2 in sonuclar:
    gi, ci = ADAYLAR[mid]
    hatalar = sum(not isinstance(x[0], int) for x in r1 + r2)
    isabet = sum(isinstance(x[0], int) and v[3] <= x[0] <= v[4] for v, x in zip(VAKALAR * 2, r1 + r2))
    tutarli = sum(a[0] == b[0] for a, b in zip(r1, r2))
    tin = sum(x[1] for x in r1 + r2) / len(r1 + r2); tout = sum(x[2] for x in r1 + r2) / len(r1 + r2)
    maliyet = 2700 * (tin / 1e6 * gi + tout / 1e6 * ci)
    sure = sum(x[3] for x in r1 + r2) / len(r1 + r2)
    satirlar.append((mid, isabet, tutarli, hatalar, tout, maliyet, sure, r1))

satirlar.sort(key=lambda s: (-s[1], s[5]))
print(f"{'aday':<30}{'isabet/30':>10}{'tutarlı/15':>11}{'hata':>6}{'çıkış tok':>10}{'2700 çağrı $':>13}{'süre':>7}")
for mid, isabet, tutarli, hatalar, tout, maliyet, sure, _ in satirlar:
    print(f"{mid:<30}{isabet:>10}{tutarli:>11}{hatalar:>6}{tout:>10.0f}{maliyet:>13.2f}{sure:>6.1f}s")

print("\nVaka bazında puanlar (1. tur)  [beklenen aralık]")
print(f"{'tuzak':<44}" + "".join(f"{s[0].split('/')[1][:11]:>12}" for s in satirlar))
for i, v in enumerate(VAKALAR):
    print(f"{(v[5] + f' [{v[3]}-{v[4]}]'):<44}" + "".join(
        f"{(str(s[7][i][0]) if isinstance(s[7][i][0], int) else 'X') + ('' if isinstance(s[7][i][0], int) and v[3] <= s[7][i][0] <= v[4] else '✗'):>12}"
        for s in satirlar))
