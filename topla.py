r"""Adım 3: veri setindeki soruları ayarlar.py'deki modellere sorar; ham cevapları
sonuclar/ham_cevaplar.csv dosyasına HER ÇAĞRIDAN SONRA yazar (checkpoint).
Yarıda kesilirse tekrar çalıştır: başarıyla cevaplanmış satırlar atlanır, hatalılar yeniden denenir.

Çalıştır:  .venv\Scripts\python topla.py          (tüm sorular)
           .venv\Scripts\python topla.py --n 5    (pilot: ilk 5 soru)
"""
import argparse, csv, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, APIStatusError
from tqdm import tqdm

import ayarlar as A

KOK = os.path.dirname(os.path.abspath(__file__))
HAM = os.path.join(KOK, "sonuclar", "ham_cevaplar.csv")
ANAHTAR = ["soru_no", "model", "temperature", "top_p", "tekrar"]
ALANLAR = ANAHTAR + ["aile", "kademe", "cevap", "giris_token", "cikis_token", "maliyet_usd",
                     "sure_sn", "saglayici", "bitis", "deneme", "hata"]
KALICI = {400, 401, 403, 404}   # tekrar denemek anlamsız (istek/anahtar/model hatalı)
OLUMCUL = {401, 402}            # anahtar geçersiz / kredi bitti → tüm çalışmayı durdur


class Olumcul(Exception):
    pass


def veri_seti():
    for ad in ("dataset.xlsx", "dataset_taslak.xlsx"):
        yol = os.path.join(KOK, "veri", ad)
        if os.path.exists(yol):
            return pd.read_excel(yol), ad
    sys.exit("HATA: veri/dataset.xlsx bulunamadı.")


def anahtar(no, model, T, p, k):
    return (int(no), model, round(float(T), 3), round(float(p), 3), int(k))


def sor(client, m, soru, T, p):
    bos = dict(cevap="", giris_token=0, cikis_token=0, maliyet_usd=0.0, sure_sn=0.0, saglayici="", bitis="")
    son_hata = ""
    for deneme in range(1, A.DENEME_SAYISI + 1):
        t0 = time.perf_counter()
        try:
            r = client.chat.completions.create(
                model=m["id"], temperature=T, top_p=p, max_tokens=A.MAX_TOKENS, timeout=A.TIMEOUT,
                messages=[{"role": "system", "content": A.SISTEM_PROMPT}, {"role": "user", "content": soru}],
                extra_body=A.extra_body(m))
            metin = (r.choices[0].message.content or "").strip()
            bitis = r.choices[0].finish_reason
            if metin:
                u = r.usage
                return dict(cevap=metin, giris_token=u.prompt_tokens, cikis_token=u.completion_tokens,
                            maliyet_usd=round(A.maliyet(m, u.prompt_tokens, u.completion_tokens), 8),
                            sure_sn=round(time.perf_counter() - t0, 2), saglayici=getattr(r, "provider", "") or "",
                            bitis=bitis, deneme=deneme, hata="")
            son_hata = f"boş cevap (finish_reason={bitis})"
        except APIStatusError as e:
            son_hata = f"{e.status_code}: {str(e)[:250]}"
            if e.status_code in OLUMCUL:
                raise Olumcul(son_hata)
            if e.status_code in KALICI:
                return {**bos, "deneme": deneme, "hata": son_hata}
        except Exception as e:  # timeout, bağlantı hatası vb.
            son_hata = f"{type(e).__name__}: {str(e)[:250]}"
        if deneme < A.DENEME_SAYISI:
            time.sleep(2 ** deneme)  # üstel geri çekilme: 2, 4, 8 sn
    return {**bos, "deneme": A.DENEME_SAYISI, "hata": son_hata}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, help="sadece ilk N soru (pilot)")
    args = ap.parse_args()

    load_dotenv(os.path.join(KOK, ".env"))
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key or "BURAYA" in key:
        sys.exit("HATA: .env içinde OPENROUTER_API_KEY yok.")
    client = OpenAI(base_url=A.OPENROUTER_URL, api_key=key, max_retries=0)  # tekrar denemeyi kendimiz yönetiyoruz

    df, ad = veri_seti()
    if args.n:
        df = df.head(args.n)

    yapildi = set()
    if os.path.exists(HAM):
        h = pd.read_csv(HAM)
        for r in h[h["hata"].isna()].itertuples():
            yapildi.add(anahtar(r.soru_no, r.model, r.temperature, r.top_p, r.tekrar))

    isler = [(q, m, T, p, k)
             for q in df.to_dict("records") for m in A.MODELLER for T, p in A.DENEYLER
             for k in range(1, A.TEKRAR + 1)
             if anahtar(q["No"], m["id"], T, p, k) not in yapildi]
    print(f"Veri seti: {ad} ({len(df)} soru) · {len(A.MODELLER)} model · {len(A.DENEYLER)} ayar · "
          f"{A.TEKRAR} tekrar → {len(isler)} çağrı yapılacak ({len(yapildi)} zaten var)")
    if not isler:
        return

    os.makedirs(os.path.dirname(HAM), exist_ok=True)
    yeni = not os.path.exists(HAM)
    kilit = threading.Lock()
    hata_sayisi, toplam = 0, 0.0
    with open(HAM, "a", newline="", encoding="utf-8") as f, ThreadPoolExecutor(A.ESZAMANLI) as ex:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        if yeni:
            w.writeheader()
        gorevler = {ex.submit(sor, client, m, q["Soru"], T, p): (q, m, T, p, k) for q, m, T, p, k in isler}
        try:
            for g in tqdm(as_completed(gorevler), total=len(gorevler), unit="çağrı"):
                q, m, T, p, k = gorevler[g]
                sonuc = g.result()
                with kilit:
                    w.writerow(dict(soru_no=q["No"], model=m["id"], temperature=T, top_p=p, tekrar=k,
                                    aile=m["aile"], kademe=m["kademe"], **sonuc))
                    f.flush()
                hata_sayisi += bool(sonuc["hata"])
                toplam += sonuc["maliyet_usd"]
        except Olumcul as e:
            ex.shutdown(cancel_futures=True)
            sys.exit(f"\nDURDURULDU ({e}). O ana kadarki cevaplar kaydedildi; sorunu çözüp tekrar çalıştır.")
    print(f"Bitti. Hatalı çağrı: {hata_sayisi} · bu çalıştırmanın maliyeti ≈ ${toplam:.4f} · {HAM}")
    if hata_sayisi:
        print("Hatalı satırlar bir sonraki çalıştırmada yeniden denenir.")


if __name__ == "__main__":
    main()
