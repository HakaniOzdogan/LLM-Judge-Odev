r"""Adım 4: topla.py'nin ham cevaplarını hakem modele (ayarlar.HAKEM, temperature=0) puanlatır,
puanları sonuclar/hakem_puanlari.csv'ye her çağrıdan sonra yazar ve sonuclar/sonuclar.xlsx'i üretir.
Yarıda kesilirse tekrar çalıştır: puanlanmış satırlar atlanır.

Çalıştır:  .venv\Scripts\python hakem.py
           .venv\Scripts\python hakem.py --sadece-excel   (API çağrısı yapmadan Excel'i yeniden üret)
"""
import argparse, csv, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, APIStatusError
from openpyxl.styles import Alignment, Font, PatternFill
from tqdm import tqdm

import ayarlar as A
from topla import ANAHTAR, HAM, KOK, OLUMCUL, Olumcul, veri_seti

PUAN = os.path.join(KOK, "sonuclar", "hakem_puanlari.csv")
EXCEL = os.path.join(KOK, "sonuclar", "sonuclar.xlsx")
PUAN_ALANLAR = ANAHTAR + ["skor", "gerekce", "hakem_giris", "hakem_cikis", "hakem_maliyet", "hata"]


def ayristir(metin):
    """Hakem cevabından skoru çıkarır. ```json sarmalı veya önündeki metne dayanıklı."""
    m = re.search(r"\{.*\}", metin or "", re.S)
    d = json.loads(m.group(0))
    skor = int(round(float(d["skor"])))
    if not 0 <= skor <= 100:
        raise ValueError(f"skor aralık dışı: {skor}")
    return skor, str(d.get("gerekce", "")).strip()


def kullanici_mesaji(soru, referans, not_, cevap):
    parca = f"[SORU]\n{soru}\n\n[REFERANS CEVAP]\n{referans}\n\n"
    if isinstance(not_, str) and not_.strip():
        parca += f"[DEĞERLENDİRME NOTU]\n{not_.strip()}\n\n"
    return parca + f"[DEĞERLENDİRİLEN CEVAP]\n{cevap}"


def puanla(client, mesaj):
    son_hata = ""
    for deneme in range(1, A.DENEME_SAYISI + 1):
        try:
            r = client.chat.completions.create(
                model=A.HAKEM["id"], temperature=A.HAKEM_TEMPERATURE, max_tokens=300, timeout=A.TIMEOUT,
                messages=[{"role": "system", "content": A.HAKEM_PROMPT}, {"role": "user", "content": mesaj}],
                response_format={"type": "json_object"}, extra_body=A.extra_body(A.HAKEM))
            u = r.usage
            try:
                skor, gerekce = ayristir(r.choices[0].message.content)
            except Exception as e:
                son_hata = f"JSON ayrıştırılamadı: {e}"  # tekrar dene; olmazsa skor boş kalır (tahmin edilmez)
            else:
                return dict(skor=skor, gerekce=gerekce, hakem_giris=u.prompt_tokens, hakem_cikis=u.completion_tokens,
                            hakem_maliyet=round(A.maliyet(A.HAKEM, u.prompt_tokens, u.completion_tokens), 8), hata="")
        except APIStatusError as e:
            son_hata = f"{e.status_code}: {str(e)[:250]}"
            if e.status_code in OLUMCUL:
                raise Olumcul(son_hata)
        except Exception as e:
            son_hata = f"{type(e).__name__}: {str(e)[:250]}"
        if deneme < A.DENEME_SAYISI:
            time.sleep(2 ** deneme)
    return dict(skor=None, gerekce="", hakem_giris=0, hakem_cikis=0, hakem_maliyet=0.0, hata=son_hata)


def ham_cevaplar():
    """Her (soru, model, ayar, tekrar) için tek satır: varsa başarılı olan, yoksa son hatalı deneme."""
    h = pd.read_csv(HAM)
    h["_ok"] = h["hata"].isna()
    return h.sort_values("_ok", kind="stable").drop_duplicates(ANAHTAR, keep="last").drop(columns="_ok")


def hakemlik(client):
    h = ham_cevaplar()
    veri, _ = veri_seti()
    h = h.merge(veri[["No", "Soru", "Ana Cevap", "Hakem Notu"]], left_on="soru_no", right_on="No", how="left")
    puanli = set()
    if os.path.exists(PUAN):
        p = pd.read_csv(PUAN)
        puanli = {tuple(x) for x in p[p["hata"].isna()][ANAHTAR].itertuples(index=False)}
    isler = [r for r in h[h["hata"].isna()].to_dict("records") if tuple(r[k] for k in ANAHTAR) not in puanli]
    print(f"Hakem: {A.HAKEM['id']} · {len(isler)} cevap puanlanacak ({len(puanli)} zaten puanlı)")
    if not isler:
        return
    yeni = not os.path.exists(PUAN)
    kilit = threading.Lock()
    with open(PUAN, "a", newline="", encoding="utf-8") as f, ThreadPoolExecutor(A.ESZAMANLI) as ex:
        w = csv.DictWriter(f, fieldnames=PUAN_ALANLAR)
        if yeni:
            w.writeheader()
        gorevler = {ex.submit(puanla, client, kullanici_mesaji(r["Soru"], r["Ana Cevap"], r["Hakem Notu"], r["cevap"])): r
                    for r in isler}
        try:
            for g in tqdm(as_completed(gorevler), total=len(gorevler), unit="puan"):
                r = gorevler[g]
                with kilit:
                    w.writerow({**{k: r[k] for k in ANAHTAR}, **g.result()})
                    f.flush()
        except Olumcul as e:
            ex.shutdown(cancel_futures=True)
            sys.exit(f"\nDURDURULDU ({e}). Puanlar kaydedildi; sorunu çözüp tekrar çalıştır.")


def ayar_etiketi(T, p):
    return f"T={T:g}" + ("" if p == 1 else f" p={p:g}")


def bicimle(ws, genislik=18):
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2F5BD3")
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for kol in ws.columns:
        ws.column_dimensions[kol[0].column_letter].width = genislik
    ws.freeze_panes = "B2"


def excel():
    h = ham_cevaplar()
    veri, _ = veri_seti()
    if os.path.exists(PUAN):
        p = pd.read_csv(PUAN)
        p["_ok"] = p["hata"].isna()
        p = p.sort_values("_ok", kind="stable").drop_duplicates(ANAHTAR, keep="last").drop(columns="_ok")
        h = h.merge(p.rename(columns={"hata": "hakem_hata"}), on=ANAHTAR, how="left")
    else:
        h[["skor", "gerekce", "hakem_maliyet", "hakem_hata"]] = None
    h = h.merge(veri[["No", "Kategori", "Zorluk", "Tür", "Soru", "Ana Cevap"]], left_on="soru_no", right_on="No", how="left")
    h["ayar"] = [ayar_etiketi(T, p) for T, p in zip(h["temperature"], h["top_p"])]
    h["kisa_ad"] = h["model"].str.split("/").str[1]
    sira_m = [m["id"].split("/")[1] for m in A.MODELLER]
    sira_a = [ayar_etiketi(T, p) for T, p in A.DENEYLER]

    # 1) Rehberdeki geniş tablo: her soru bir satır; her model×ayar için Cevap + Doğruluk (1. tekrar)
    g = h[h["tekrar"] == 1].copy()
    g["cevap_goster"] = g["cevap"].where(g["hata"].isna(), "HATA: " + g["hata"].astype(str))
    genis = veri[["No", "Soru", "Ana Cevap"]].copy()
    for mk in sira_m:
        for a in sira_a:
            s = g[(g["kisa_ad"] == mk) & (g["ayar"] == a)].set_index("soru_no")
            if s.empty:
                continue
            genis[f"{mk} | {a} | Cevap"] = genis["No"].map(s["cevap_goster"])
            genis[f"{mk} | {a} | Doğruluk %"] = genis["No"].map(s["skor"])
    genis = genis[genis["No"].isin(h["soru_no"])]

    # 1b) Teslim sayfası: rehberdeki birebir biçim — her model için "Cevabı" + "Doğruluk" (%), ilk deney ayarı (T=0)
    a0 = sira_a[0]
    teslim = veri[["Soru", "Ana Cevap"]].copy()
    for i, mk in enumerate(sira_m, 1):
        s = g[(g["kisa_ad"] == mk) & (g["ayar"] == a0)].set_index("soru_no")
        teslim[f"Model {i} ({mk}) Cevabı"] = veri["No"].map(s["cevap_goster"])
        teslim[f"Model {i} Doğruluk"] = veri["No"].map(s["skor"]).map(lambda x: "" if pd.isna(x) else f"%{x:.0f}")
    teslim = teslim[veri["No"].isin(h["soru_no"])]

    # 2) Özet: model × ayar
    ozet = (h.groupby(["aile", "kademe", "kisa_ad", "ayar"], sort=False)
             .agg(ortalama_dogruluk=("skor", "mean"),
                  tam_dogru_orani=("skor", lambda s: (s == 100).mean() * 100),
                  puanlanan=("skor", "count"), hatali_cagri=("hata", lambda s: s.notna().sum()),
                  ort_sure_sn=("sure_sn", "mean"), ort_cikis_token=("cikis_token", "mean"),
                  toplam_maliyet_usd=("maliyet_usd", "sum"))
             .reset_index())
    ozet["dogru_basina_maliyet_usd"] = ozet["toplam_maliyet_usd"] / (ozet["ortalama_dogruluk"] / 100 * ozet["puanlanan"])
    ozet = ozet.round({"ortalama_dogruluk": 1, "tam_dogru_orani": 1, "ort_sure_sn": 2, "ort_cikis_token": 1,
                       "toplam_maliyet_usd": 6, "dogru_basina_maliyet_usd": 8})
    ozet = ozet.sort_values(["kisa_ad", "ayar"], key=lambda s: s.map(
        {v: i for i, v in enumerate(sira_m if s.name == "kisa_ad" else sira_a)})).reset_index(drop=True)
    tablo = h.pivot_table(index="kisa_ad", columns="ayar", values="skor", aggfunc="mean").reindex(index=sira_m, columns=sira_a).round(1)
    kategori = h.pivot_table(index="kisa_ad", columns="Kategori", values="skor", aggfunc="mean").reindex(index=sira_m).round(1)
    zorluk = h.pivot_table(index="kisa_ad", columns="Zorluk", values="skor", aggfunc="mean").reindex(index=sira_m).round(1)

    with pd.ExcelWriter(EXCEL, engine="openpyxl") as xw:
        teslim.to_excel(xw, sheet_name=f"Teslim ({a0})", index=False)
        bicimle(xw.sheets[f"Teslim ({a0})"], 24)
        xw.sheets[f"Teslim ({a0})"].column_dimensions["A"].width = 45
        xw.sheets[f"Teslim ({a0})"].freeze_panes = "C2"
        genis.to_excel(xw, sheet_name="Sonuçlar", index=False)
        bicimle(xw.sheets["Sonuçlar"], 22)
        xw.sheets["Sonuçlar"].column_dimensions["B"].width = 45
        xw.sheets["Sonuçlar"].freeze_panes = "D2"
        ozet.to_excel(xw, sheet_name="Özet", index=False)
        bicimle(xw.sheets["Özet"], 15)
        r0 = len(ozet) + 3
        for baslik, t in (("Ortalama doğruluk (%) — model × ayar", tablo),
                          ("Ortalama doğruluk (%) — model × kategori", kategori),
                          ("Ortalama doğruluk (%) — model × zorluk", zorluk)):
            xw.sheets["Özet"].cell(row=r0, column=1, value=baslik).font = Font(bold=True)
            t.to_excel(xw, sheet_name="Özet", startrow=r0)
            r0 += len(t) + 4
        if A.TEKRAR > 1:
            k = h[h["hata"].isna()].groupby(["kisa_ad", "ayar", "soru_no"]).agg(
                skor_std=("skor", "std"), farkli_cevap=("cevap", "nunique"))
            kar = k.groupby(["kisa_ad", "ayar"]).agg(
                ort_skor_std=("skor_std", "mean"),
                tum_tekrarlar_ayni_orani=("farkli_cevap", lambda s: (s == 1).mean() * 100)).round(2).reset_index()
            kar.to_excel(xw, sheet_name="Kararlılık", index=False)
            bicimle(xw.sheets["Kararlılık"], 20)
        ham = h[["soru_no", "Kategori", "Zorluk", "Tür", "Soru", "Ana Cevap", "aile", "kademe", "model", "temperature",
                 "top_p", "tekrar", "cevap", "skor", "gerekce", "giris_token", "cikis_token", "maliyet_usd", "sure_sn",
                 "saglayici", "bitis", "deneme", "hata", "hakem_maliyet", "hakem_hata"]]
        ham.sort_values(["soru_no", "model", "temperature", "top_p", "tekrar"]).to_excel(xw, sheet_name="Ham Veri", index=False)
        bicimle(xw.sheets["Ham Veri"], 16)
    cevap_m, hakem_m = h["maliyet_usd"].sum(), pd.to_numeric(h["hakem_maliyet"], errors="coerce").sum()
    print(f"Excel: {EXCEL}\nMaliyet: cevaplar ${cevap_m:.4f} + hakem ${hakem_m:.4f} = ${cevap_m + hakem_m:.4f}")
    print("\nOrtalama doğruluk (%), model × ayar:\n" + tablo.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadece-excel", action="store_true")
    args = ap.parse_args()
    if not os.path.exists(HAM):
        sys.exit("HATA: önce topla.py çalıştırılmalı.")
    if not args.sadece_excel:
        load_dotenv(os.path.join(KOK, ".env"))
        hakemlik(OpenAI(base_url=A.OPENROUTER_URL, api_key=os.getenv("OPENROUTER_API_KEY"), max_retries=0))
    excel()


assert ayristir('```json\n{"skor": 80, "gerekce": "kısmi"}\n```') == (80, "kısmi")
assert ayristir('Puan: {"skor": "100", "gerekce": ""}')[0] == 100

if __name__ == "__main__":
    main()
