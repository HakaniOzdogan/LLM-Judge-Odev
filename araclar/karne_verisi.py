r"""Model Karnesi sayfasının veri dosyalarını üretir (JSON, her biri {rows, meta}).
Girdi: sonuclar/sonuclar.xlsx (Ham Veri). Çıktı klasörü: argüman olarak verilir.
Çalıştır:  .venv\Scripts\python araclar\karne_verisi.py <çıktı_klasörü>
"""
import json, os, sys
import pandas as pd

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import ayarlar as A

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
KOD = open(os.path.abspath(__file__), encoding="utf-8").read()
META = [{"label": "karne_verisi.py", "value": KOD, "type": "code", "lang": "python"},
        {"label": "Girdi", "value": "sonuclar/sonuclar.xlsx → Ham Veri (2.400 cevap, hakem: gpt-4.1-mini)"}]

h = pd.read_excel(os.path.join(KOK, "sonuclar", "sonuclar.xlsx"), "Ham Veri")
h["m"] = h["model"].str.split("/").str[1]
SIRA = [m["id"].split("/")[1] for m in A.MODELLER]
BILGI = {m["id"].split("/")[1]: m for m in A.MODELLER}
KADEME = {"ucuz": "Ucuz", "orta": "Orta", "pahali": "Pahalı"}
AYAR = [(0.0, 1.0, "T=0"), (0.7, 1.0, "T=0.7"), (1.0, 1.0, "T=1"), (1.0, 0.5, "T=1 · top_p=0.5")]
r1 = lambda x: round(float(x), 1)


def yaz(ad, rows):
    with open(os.path.join(out, ad), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "meta": META}, f, ensure_ascii=False)
    print(ad, len(rows), "satır")


def sec(mk, T, p):
    return h[(h["m"] == mk) & (h["temperature"] == T) & (h["top_p"] == p)].set_index("soru_no")


# 1) modeller
modeller = []
for i, mk in enumerate(SIRA):
    d, b = h[h["m"] == mk], BILGI[mk]
    t0, t1 = sec(mk, 0.0, 1.0), sec(mk, 1.0, 1.0)
    z = d.groupby("Zorluk")["skor"].mean()
    mal = d["maliyet_usd"].sum()
    dog = d["skor"].mean()
    modeller.append({
        "model": mk, "aile": b["aile"], "kademe": KADEME[b["kademe"]], "sira": i,
        "giris_fiyat": b["giris"], "cikis_fiyat": b["cikis"],
        "dogruluk": r1(dog), "dogruluk_t0": r1(t0["skor"].mean()),
        "tam_dogru": r1((d["skor"] == 100).mean() * 100), "sifir": r1((d["skor"] == 0).mean() * 100),
        "kolay": r1(z["Kolay"]), "orta": r1(z["Orta"]), "zor": r1(z["Zor"]),
        "sure_sn": round(d["sure_sn"].mean(), 2), "cikis_token": r1(d["cikis_token"].mean()),
        "maliyet_1000_soru": round(mal / len(d) * 1000, 4),
        "maliyet_1000_dogru": round(mal / (dog / 100 * len(d)) * 1000, 4),
        "maliyet_1m_soru": round(mal / len(d) * 1e6, 1),
        "takildigi_soru": int(d[d["skor"] < 100]["soru_no"].nunique()),
        "t1_metin_degisen": int((t0["cevap"] != t1["cevap"].reindex(t0.index)).sum()),
        "t1_puan_degisen": int((t0["skor"] != t1["skor"].reindex(t0.index)).sum()),
    })
yaz("modeller.json", modeller)

# 2) model × ayar
ayar_rows = []
for mk in SIRA:
    t0 = sec(mk, 0.0, 1.0)
    for j, (T, p, et) in enumerate(AYAR):
        s = sec(mk, T, p)
        ayar_rows.append({"model": mk, "ayar": et, "ayar_sira": j, "dogruluk": r1(s["skor"].mean()),
                          "metin_degisen": None if j == 0 else int((t0["cevap"] != s["cevap"].reindex(t0.index)).sum()),
                          "puan_degisen": None if j == 0 else int((t0["skor"] != s["skor"].reindex(t0.index)).sum())})
yaz("model_ayar.json", ayar_rows)

# 3) model × kategori
kat = h.groupby(["m", "Kategori"])["skor"].mean()
yaz("model_kategori.json", [{"model": mk, "kategori": k, "dogruluk": r1(kat[(mk, k)])}
                             for mk in SIRA for k in sorted(h["Kategori"].unique())])

# 4) takıldığı sorular (en çok ayarda tam puan alamadığı önce)
tak = []
for mk in SIRA:
    d = h[(h["m"] == mk) & (h["skor"] < 100)]
    for no, g in d.groupby("soru_no"):
        k = g.loc[g["skor"].idxmin()]
        tak.append({"model": mk, "soru_no": int(no), "kategori": k["Kategori"], "zorluk": k["Zorluk"],
                    "soru": k["Soru"], "ana_cevap": str(k["Ana Cevap"]),
                    "model_cevabi": " ".join(str(k["cevap"]).replace("**", "").split())[:160],
                    "en_dusuk_puan": int(k["skor"]), "yanlis_ayar": int(len(g))})
tak.sort(key=lambda r: (SIRA.index(r["model"]), -r["yanlis_ayar"], r["en_dusuk_puan"], r["soru_no"]))
yaz("takildigi.json", tak)

# 5) artı / eksi notları — rakamlar yukarıdaki tablolardan
M = {r["model"]: r for r in modeller}
K = {(r["model"], r["kategori"]): r["dogruluk"] for r in
     [{"model": mk, "kategori": k, "dogruluk": r1(kat[(mk, k)])} for mk in SIRA for k in h["Kategori"].unique()]}
md = h.assign(md=h["cevap"].astype(str).str.contains(r"\*\*", regex=True)).groupby("m")["md"].mean()
kat_t = h.groupby(["m", "Tür"])["skor"].mean()
kat_ = lambda mk, c: f"%{K[(mk, c)]:.0f}"
kac = lambda a, b: f"{M[a]['maliyet_1000_dogru'] / M[b]['maliyet_1000_dogru']:.1f}"
N = {
    "qwen3.7-flash": (
        [f"En ucuz model: 1.000 doğru cevap ${M['qwen3.7-flash']['maliyet_1000_dogru']:.4f}; qwen3.7-plus'tan {kac('qwen3.7-plus', 'qwen3.7-flash')} kat ucuz.",
         f"Aynı fiyat sınıfındaki ministral-8b'den {M['qwen3.7-flash']['dogruluk'] - M['ministral-8b-2512']['dogruluk']:.1f} puan daha doğru.",
         f"Kolay sorularda (%{M['qwen3.7-flash']['kolay']:.0f}), Tarih ({kat_('qwen3.7-flash', 'Tarih')}) ve Bilimde ({kat_('qwen3.7-flash', 'Bilim')}) güvenilir."],
        [f"Zor sorularda doğruluk %{M['qwen3.7-flash']['zor']:.0f}.",
         f"Edebiyat-Sanat ({kat_('qwen3.7-flash', 'Edebiyat-Sanat')}) ve Spor ({kat_('qwen3.7-flash', 'Spor')}) zayıf: Tanpınar, Oğuz Atay, Hakan Şükür ve Hidayet Türkoğlu sorularında takıldı.",
         f"temperature'a en hassas model: T=1'de metni değişen cevap {M['qwen3.7-flash']['t1_metin_degisen']}, puanı değişen {M['qwen3.7-flash']['t1_puan_degisen']} (Van Gölü yerine 'Tuz Gölü')."]),
    "qwen3.7-plus": (
        [f"En iyi fiyat/performans: %{M['qwen3.7-plus']['dogruluk']:.1f} doğruluk; en doğru modelle farkı istatistiksel olarak anlamlı değil.",
         f"qwen3.7-max'tan {kac('qwen3.7-max', 'qwen3.7-plus')}, mistral-medium-3.5'ten {kac('mistral-medium-3-5', 'qwen3.7-plus')} kat ucuz.",
         f"Kısa ve net: ortalama {M['qwen3.7-plus']['cikis_token']:.1f} token ile en kısa cevaplar."],
        [f"En zayıf alanları Spor ({kat_('qwen3.7-plus', 'Spor')}) ve Edebiyat-Sanat ({kat_('qwen3.7-plus', 'Edebiyat-Sanat')}); Hidayet Türkoğlu sorusunu 4 ayarın 3'ünde bilemedi.",
         f"Mistral modellerinden yavaş: ortalama {M['qwen3.7-plus']['sure_sn']:.2f} sn.",
         f"T=1'de puanı değişen soru sayısı {M['qwen3.7-plus']['t1_puan_degisen']}; T=0 ile kullanılmalı."]),
    "qwen3.7-max": (
        [f"En doğru model: %{M['qwen3.7-max']['dogruluk']:.1f}; zor sorularda %{M['qwen3.7-max']['zor']:.0f}.",
         f"Hiçbir cevapta sıfır puan yok (%{M['qwen3.7-max']['sifir']:.0f}).",
         f"temperature'dan etkilenmiyor: T=1'de puanı değişen soru sayısı {M['qwen3.7-max']['t1_puan_degisen']}."],
        [f"qwen3.7-plus'tan {kac('qwen3.7-max', 'qwen3.7-plus')} kat pahalı; doğruluk kazancı {M['qwen3.7-max']['dogruluk'] - M['qwen3.7-plus']['dogruluk']:.1f} puan ve anlamlı değil.",
         f"En yavaş model: ortalama {M['qwen3.7-max']['sure_sn']:.2f} sn."]),
    "ministral-8b-2512": (
        [f"En hızlı model: ortalama {M['ministral-8b-2512']['sure_sn']:.2f} sn.",
         f"Çok ucuz: 1.000 soru ${M['ministral-8b-2512']['maliyet_1000_soru']:.4f}."],
        [f"En düşük doğruluk: %{M['ministral-8b-2512']['dogruluk']:.1f}; tamamen yanlış cevap oranı %{M['ministral-8b-2512']['sifir']:.1f}.",
         f"Edebiyat-Sanat {kat_('ministral-8b-2512', 'Edebiyat-Sanat')}, Spor {kat_('ministral-8b-2512', 'Spor')}, zor sorular %{M['ministral-8b-2512']['zor']:.0f}.",
         f"Gereksiz Markdown kullandığı cevap oranı %{md['ministral-8b-2512'] * 100:.0f}; en uzun cevaplar ({M['ministral-8b-2512']['cikis_token']:.0f} token).",
         "T=1'de bilgi değiştiriyor: 206 kemik → '306–310', Çalıkuşu'nun yazarı → 'Mehmet Rauf'."]),
    "mistral-large-2512": (
        [f"Doğruluk %{M['mistral-large-2512']['dogruluk']:.1f}: qwen3.7-plus ile aynı.",
         f"Hızlı: ortalama {M['mistral-large-2512']['sure_sn']:.2f} sn, qwen3.7-plus'tan {M['qwen3.7-plus']['sure_sn'] / M['mistral-large-2512']['sure_sn']:.1f} kat hızlı.",
         f"Çok parçalı sorularda %{kat_t[('mistral-large-2512', 'Çok parçalı')]:.0f}."],
        [f"qwen3.7-plus'tan {kac('mistral-large-2512', 'qwen3.7-plus')} kat pahalı.",
         "'Ankara hangi tarihte başkent ilan edildi?' sorusuna 4 ayarda da '29 Ekim 1923' dedi; Cumhuriyet'in ilanıyla karıştırdı.",
         "T=0.7'de bir cevaptan sonra durmayıp eğitim verisinden kalma gibi görünen ilgisiz metin üretti.",
         "Mistral sunucusunda yoğun istekte 16 kez hız limitine (429) takıldı."]),
    "mistral-medium-3-5": (
        [f"T=0'da %{M['mistral-medium-3-5']['dogruluk_t0']:.0f}, genel ortalaması %{M['mistral-medium-3-5']['dogruluk']:.1f}.",
         f"Yüksek doğruluklu modellerin en hızlısı: ortalama {M['mistral-medium-3-5']['sure_sn']:.2f} sn.",
         f"Metni değişse de bilgisi sabit: T=1'de metni değişen cevap {M['mistral-medium-3-5']['t1_metin_degisen']}, puanı değişen yalnızca {M['mistral-medium-3-5']['t1_puan_degisen']}."],
        [f"En pahalı model: 1.000 doğru cevap ${M['mistral-medium-3-5']['maliyet_1000_dogru']:.3f}, qwen3.7-plus'ın {kac('mistral-medium-3-5', 'qwen3.7-plus')} katı.",
         "T=1'de 'Kürk Mantolu Madonna'nın yazarına 'Sabatay Sevi' dedi; ön testte yüksek temperature'da Türkçesi bozuldu."]),
}
yaz("notlar.json", [{"model": mk, "tur": tur, "sira": j, "metin": t}
                    for mk in SIRA for tur, liste in zip(("arti", "eksi"), N[mk]) for j, t in enumerate(liste)])
