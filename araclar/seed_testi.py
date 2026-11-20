r"""Seed gerçekten çalışıyor mu? Her model için T=1.0'da:
  A) aynı seed (42) ile 3 çağrı  → cevaplar aynı olmalı
  B) farklı seed (1,2,3) ile 3 çağrı → kontrol: model gerçekten dalgalanıyor mu?
B'de bile cevaplar aynıysa soru fazla kolaydır; o zaman A'nın aynı çıkması seed'i kanıtlamaz.
Ayrıca her çağrıda gerçekten sabitlenen sağlayıcının cevap verdiğini kontrol eder.
Çalıştır:  .venv\Scripts\python araclar\seed_testi.py
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ayarlar import MODELLER, OPENROUTER_URL, SISTEM_PROMPT, MAX_TOKENS, extra_body

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
client = OpenAI(base_url=OPENROUTER_URL, api_key=os.getenv("OPENROUTER_API_KEY"))
SORU = "Osmanlı İmparatorluğu'nu tek bir cümleyle anlat."  # açık uçlu: T=1'de çeşitlilik görülsün


def cagir(m, seed):
    try:
        r = client.chat.completions.create(
            model=m["id"], temperature=1.0, top_p=1.0, seed=seed, max_tokens=MAX_TOKENS, timeout=90,
            messages=[{"role": "system", "content": SISTEM_PROMPT}, {"role": "user", "content": SORU}],
            extra_body=extra_body(m))
        return (r.choices[0].message.content or "").strip(), getattr(r, "provider", None)
    except Exception as e:
        return f"HATA: {str(e)[:120]}", None


def test(m):
    with ThreadPoolExecutor(6) as ex:
        a = list(ex.map(lambda s: cagir(m, s), [42, 42, 42]))
        b = list(ex.map(lambda s: cagir(m, s), [1, 2, 3]))
    return m, a, b


with ThreadPoolExecutor(9) as ex:
    sonuclar = list(ex.map(test, MODELLER))

for m, a, b in sonuclar:
    ayni_a = len({x[0] for x in a})
    ayni_b = len({x[0] for x in b})
    saglayicilar = {x[1] for x in a + b}
    hata = any(x[0].startswith("HATA") for x in a + b)
    if hata:
        sonuc = "HATA"
    elif ayni_b == 1:
        sonuc = "BELİRSİZ (farklı seed'lerde de aynı cevap)"
    elif ayni_a == 1:
        sonuc = "SEED ÇALIŞIYOR"
    else:
        sonuc = "SEED ÇALIŞMIYOR"
    print(f"\n{m['aile']:<8}{m['kademe']:<7}{m['id']:<32} → {sonuc}")
    print(f"   sağlayıcı: beklenen={m['saglayici']}  gelen={saglayicilar}")
    print(f"   aynı seed: {ayni_a} farklı cevap / 3   |   farklı seed: {ayni_b} farklı cevap / 3")
    for etiket, grup in (("seed=42", a), ("seed=1,2,3", b)):
        for txt, _ in grup:
            print(f"     {etiket:<11}{txt[:110]!r}")
