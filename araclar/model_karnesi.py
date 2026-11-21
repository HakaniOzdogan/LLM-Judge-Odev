r"""Deney sonuçlarından model karşılaştırma Excel'i üretir: sonuclar/model_karsilastirma.xlsx
Sayfalar: Karne · Fiyat-Performans (grafikli) · Kategori ve Zorluk · Takıldığı Sorular · Ortak Zor Sorular · Bulgular
Çalıştır:  .venv\Scripts\python araclar\model_karnesi.py      (önce topla.py + hakem.py)
"""
import os, sys
import pandas as pd
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Font, PatternFill

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import ayarlar as A

sys.stdout.reconfigure(encoding="utf-8")
GIRDI = os.path.join(KOK, "sonuclar", "sonuclar.xlsx")
CIKTI = os.path.join(KOK, "sonuclar", "model_karsilastirma.xlsx")
RENK = {"Qwen": "2A78D6", "Mistral": "EB6834"}            # dataviz paleti: kategorik slot 1 ve 2
SEKIL = {"ucuz": "circle", "orta": "triangle", "pahali": "diamond"}
KADEME = {"ucuz": "Ucuz", "orta": "Orta", "pahali": "Pahalı"}

# Deney sonuçlarına dayanan nitel değerlendirme (rakamlar aşağıda hesaplanıp tabloya yazılır)
YORUM = {
    "qwen3.7-flash": ("Fiyatına göre güçlü: en ucuz model olmasına rağmen %91. Yazar adlarında ve Türkiye'ye özgü spor "
                      "bilgilerinde takılıyor. temperature'a en hassas model: T=1'de cevapların %38'inin metni değişti.",
                      "Düşük bütçeli toplu işler, hataların sonradan kontrol edildiği senaryolar. T=0 veya top_p ≤ 0.5 ile."),
    "qwen3.7-plus": ("En iyi fiyat/performans: en yüksek doğruluklu modellerle istatistiksel olarak eşit, onlardan 1.5–6 kat "
                     "ucuz. Hidayet Türkoğlu ve Tanpınar sorularında zaman zaman takıldı. En kısa cevaplar.",
                     "ÖNERİLEN genel model (T=0, top_p=1)."),
    "qwen3.7-max": ("En doğru model; hiç sıfır puanı yok, zor sorularda %100. temperature'dan neredeyse hiç etkilenmiyor. "
                    "Ancak plus'a göre 4.3 kat pahalı ve kazancı ~1–2 puan.",
                    "Tek bir yanlışın bile kabul edilemediği işler."),
    "ministral-8b-2512": ("En zayıf model: her 6 cevaptan biri tamamen yanlış. Türk edebiyatı ve sporda belirgin şekilde zayıf; "
                          "cevaplarda Markdown kullanıyor; T=1'de bilgileri değiştiriyor (206 kemik → '306–310').",
                          "Önerilmez: aynı fiyat sınıfında qwen3.7-flash hem daha ucuz hem 9 puan daha doğru."),
    "mistral-large-2512": ("Doğrulukta plus ile birebir aynı, ondan daha hızlı ama 1.4 kat pahalı. 'Ankara başkent tarihi' "
                           "sorusunu 4 ayarda da yanlış bildi. Bir cevapta durmayıp ilgisiz metin üretti; 16 kez hız limitine takıldı.",
                           "Hız önemliyse qwen3.7-plus'a alternatif."),
    "mistral-medium-3-5": ("En hızlı ve en doğru ikinci model (T=0'da %100), ama en pahalısı. Yüksek temperature'da metni çok "
                           "değişiyor (31 soru) ama bilgisi değişmiyor (1 soru).",
                           "Hız ve doğruluğun birlikte kritik olduğu canlı uygulamalar."),
}


def baslik(ws, genislik=None, satir=1):
    for c in ws[satir]:
        if c.value is None:
            continue
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1C5CAB")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for kol, w in (genislik or {}).items():
        ws.column_dimensions[kol].width = w


def sar(ws, kolonlar):
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=c.column_letter in kolonlar, vertical="top")


def main():
    h = pd.read_excel(GIRDI, "Ham Veri")
    h["m"] = h["model"].str.split("/").str[1]
    sira = [m["id"].split("/")[1] for m in A.MODELLER]
    bilgi = {m["id"].split("/")[1]: m for m in A.MODELLER}
    t0 = h[h["temperature"] == 0]

    # T=0'a göre T=1'de puanı değişen soru sayısı
    b = t0.set_index(["m", "soru_no"])
    o = h[(h["temperature"] == 1) & (h["top_p"] == 1)].set_index(["m", "soru_no"])
    degisen = ((b["cevap"] != o["cevap"].reindex(b.index)) & True).groupby("m").sum()
    skor_degisen = (b["skor"] != o["skor"].reindex(b.index)).groupby("m").sum()

    kat = h.pivot_table(index="m", columns="Kategori", values="skor", aggfunc="mean")
    zor = h.pivot_table(index="m", columns="Zorluk", values="skor", aggfunc="mean")[["Kolay", "Orta", "Zor"]]
    satirlar = []
    for mk in sira:
        d, m = h[h["m"] == mk], bilgi[mk]
        dog = d["skor"].mean()
        n = len(d)
        maliyet = d["maliyet_usd"].sum()
        zayif = kat.loc[mk].idxmin()
        satirlar.append({
            "Model": mk, "Aile": m["aile"], "Kademe": KADEME[m["kademe"]],
            "Giriş $/1M token": m["giris"], "Çıkış $/1M token": m["cikis"],
            "Doğruluk % (4 ayar ort.)": dog, "Doğruluk % (T=0)": t0[t0["m"] == mk]["skor"].mean(),
            "Tam doğru %": (d["skor"] == 100).mean() * 100, "Tamamen yanlış %": (d["skor"] == 0).mean() * 100,
            "Kolay %": zor.loc[mk, "Kolay"], "Orta %": zor.loc[mk, "Orta"], "Zor %": zor.loc[mk, "Zor"],
            "En zayıf kategori": f"{zayif} (%{kat.loc[mk, zayif]:.1f})",
            "Ort. süre (sn)": d["sure_sn"].mean(), "Ort. çıkış token": d["cikis_token"].mean(),
            "1.000 soru $": maliyet / n * 1000, "1.000 doğru cevap $": maliyet / (dog / 100 * n) * 1000,
            "1 milyon soru $": maliyet / n * 1e6,
            "T=1'de metni değişen (100'de)": int(degisen[mk]), "T=1'de puanı değişen (100'de)": int(skor_degisen[mk]),
            "Değerlendirme": YORUM[mk][0], "Önerilen kullanım": YORUM[mk][1],
        })
    karne = pd.DataFrame(satirlar)
    karne["Doğruluk sırası"] = karne["Doğruluk % (4 ayar ort.)"].rank(ascending=False, method="min").astype(int)
    karne["Doğru cevap başına ucuzluk sırası"] = karne["1.000 doğru cevap $"].rank(method="min").astype(int)

    # Fiyat-performans: yalnızca grafik ve sıralama için sade tablo
    fp = karne[["Model", "Aile", "Kademe", "1.000 soru $", "Doğruluk % (4 ayar ort.)", "1.000 doğru cevap $",
                "Ort. süre (sn)"]].copy()
    qmax = karne.loc[karne["Doğruluk % (4 ayar ort.)"].idxmax()]
    fp["En doğru modele göre ucuzluk (kat)"] = qmax["1.000 doğru cevap $"] / fp["1.000 doğru cevap $"]
    fp["En doğru modele göre doğruluk farkı (puan)"] = fp["Doğruluk % (4 ayar ort.)"] - qmax["Doğruluk % (4 ayar ort.)"]

    # Takıldığı sorular: herhangi bir ayarda tam puan alamadığı her soru
    tak = (h[h["skor"] < 100].groupby(["m", "soru_no"])
           .agg(yanlis_ayar=("skor", "size"), en_dusuk=("skor", "min")).reset_index())
    t0i = t0.set_index(["m", "soru_no"])
    kotu = h.loc[h[h["skor"] < 100].groupby(["m", "soru_no"])["skor"].idxmin()].set_index(["m", "soru_no"])
    soru = h.drop_duplicates("soru_no").set_index("soru_no")
    tak_rows = []
    for r in tak.itertuples():
        k = (r.m, r.soru_no)
        tak_rows.append({
            "Model": r.m, "Soru No": r.soru_no, "Kategori": soru.loc[r.soru_no, "Kategori"],
            "Zorluk": soru.loc[r.soru_no, "Zorluk"], "Soru": soru.loc[r.soru_no, "Soru"],
            "Ana Cevap": soru.loc[r.soru_no, "Ana Cevap"],
            "Kaç ayarda tam puan alamadı (4'te)": r.yanlis_ayar,
            "T=0 cevabı": t0i.loc[k, "cevap"] if k in t0i.index else "", "T=0 puanı": t0i.loc[k, "skor"] if k in t0i.index else None,
            "En kötü cevap": kotu.loc[k, "cevap"], "En kötü puan": r.en_dusuk,
            "Ayar (en kötü)": f"T={kotu.loc[k, 'temperature']:g} p={kotu.loc[k, 'top_p']:g}",
            "Hakem gerekçesi": kotu.loc[k, "gerekce"],
        })
    tak = pd.DataFrame(tak_rows)
    tak["_s"] = tak["Model"].map({v: i for i, v in enumerate(sira)})
    tak = tak.sort_values(["_s", "Kaç ayarda tam puan alamadı (4'te)", "Soru No"], ascending=[True, False, True]).drop(columns="_s")

    ortak = (h.groupby("soru_no").agg(ort=("skor", "mean")).reset_index().sort_values("ort").head(15))
    ortak_rows = []
    for r in ortak.itertuples():
        y = h[(h["soru_no"] == r.soru_no) & (h["skor"] < 100)].groupby("m").size()
        ortak_rows.append({"Soru No": r.soru_no, "Kategori": soru.loc[r.soru_no, "Kategori"], "Zorluk": soru.loc[r.soru_no, "Zorluk"],
                           "Soru": soru.loc[r.soru_no, "Soru"], "Ana Cevap": soru.loc[r.soru_no, "Ana Cevap"],
                           "Ortalama puan (24 cevap)": r.ort,
                           "Takılan modeller (kaç ayarda)": ", ".join(f"{mk} ({n})" for mk, n in y.reindex(sira).dropna().astype(int).items())})
    ortak = pd.DataFrame(ortak_rows)

    bulgular = [
        ("Genel tablo", "6 model, 100 soru, 4 ayar: 2.400 cevap. Toplam maliyet $0.59 (cevaplar $0.12 + hakem $0.47). Kalıcı hata yok."),
        ("En doğru", f"qwen3.7-max %{karne.loc[karne.Model=='qwen3.7-max','Doğruluk % (4 ayar ort.)'].iloc[0]:.1f} ve mistral-medium-3.5 %{karne.loc[karne.Model=='mistral-medium-3-5','Doğruluk % (4 ayar ort.)'].iloc[0]:.1f}. qwen3.7-max hiçbir soruda sıfır almadı."),
        ("En iyi fiyat/performans", "qwen3.7-plus: %98.2 doğruluk, 1.000 doğru cevap başına $0.023. En doğru modelle (max) farkı 1.8 puan ve istatistiksel olarak anlamlı değil, ama 4.3 kat ucuz."),
        ("En zayıf", "ministral-8b %82: her 6 cevaptan biri tamamen yanlış (%17.3). Edebiyat-Sanat %67, Spor %72, zor sorular %67."),
        ("Aile mi, kademe mi?", "Kademe belirleyici: ucuz %86.6 → orta %98.2 → pahalı %99.7 (13.1 puan aralık). Aile farkı yalnızca 3.2 puan ve tamamen ucuz kademeden geliyor; orta kademede iki aile eşit (98.2 / 98.2)."),
        ("Getirisi azalan adım", "Ucuz → orta geçişi +11.6 puan getiriyor. Orta → pahalı geçişi yalnızca +1.5 puan getirirken maliyeti ~4 kat artırıyor."),
        ("Modeller nerede takılıyor?", "Türkiye'ye özgü edebiyat (Tanpınar, Oğuz Atay, Sabahattin Ali), spor (Hakan Şükür'ün golü, Hidayet Türkoğlu, 2002 Dünya Kupası) ve kesin tarih soruları (Ankara'nın başkent oluşu, Amasya Genelgesi). Bilim ve evrensel sorularda tüm modeller %88+."),
        ("Ortak zor soru", "#100 'Ankara hangi tarihte başkent ilan edildi?' (13 Ekim 1923): ortalama %54; mistral-large 4 ayarın 4'ünde '29 Ekim 1923' dedi (Cumhuriyet'in ilanıyla karıştırdı), qwen-flash 4'ünde '23 Ekim 1923', ministral-8b ise '1923' (kısmi) veya '20 Ekim 1923'."),
        ("temperature", "Doğruluğu en fazla ~3 puan düşürdü ama ucuz modellerde cevapların %33–38'inin metnini değiştirdi. Pahalı modeller neredeyse etkilenmedi. top_p=0.5 bu dalgalanmayı büyük ölçüde geri aldı."),
        ("Hız", "En hızlılar Mistral modelleri: ministral-8b 0.40 sn, mistral-medium 0.50 sn, mistral-large 0.77 sn. Qwen modelleri 0.9–1.5 sn."),
        ("Davranış notları", "ministral-8b cevapların %14'ünde Markdown kullandı. mistral-large bir cevapta durmayıp eğitim verisinden kalma gibi görünen ilgisiz metin üretti. Mistral sunucusu yoğun istekte 429 (hız limiti) verdi."),
        ("Öneri", "Genel kullanım: qwen3.7-plus (T=0). Hata kabul edilemezse: qwen3.7-max. Hız kritikse: mistral-medium-3.5 / mistral-large. Bütçe çok kısıtlıysa: qwen3.7-flash. ministral-8b önerilmez."),
        ("Dikkat", "Veri seti taslaktır (Ana Cevaplar kaynakla tek tek doğrulanmadı). Her ayar tek tekrarla çalıştırıldı; 1–2 puanlık farklar şans eseri olabilir."),
    ]

    with pd.ExcelWriter(CIKTI, engine="openpyxl") as xw:
        # --- Karne
        karne.to_excel(xw, sheet_name="Karne", index=False)
        ws = xw.sheets["Karne"]
        baslik(ws, {"A": 20, "B": 9, "C": 9, "M": 24, "U": 60, "V": 40})
        for kol in "DEFGHIJKLNOPQRSTWX":
            ws.column_dimensions[kol].width = 12
        sar(ws, {"M", "U", "V"})
        ws.row_dimensions[1].height = 45
        fmt = {"D": "0.000", "E": "0.000", "F": "0.0", "G": "0.0", "H": "0.0", "I": "0.0", "J": "0.0", "K": "0.0",
               "L": "0.0", "N": "0.00", "O": "0.0", "P": "$0.0000", "Q": "$0.0000", "R": "$0.00"}
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if c.column_letter in fmt:
                    c.number_format = fmt[c.column_letter]
        son = len(karne) + 1
        for kol in "FGHJKL":
            ws.conditional_formatting.add(f"{kol}2:{kol}{son}", ColorScaleRule(start_type="num", start_value=80, start_color="CDE2FB",
                                                                               end_type="num", end_value=100, end_color="5598E7"))
        ws.conditional_formatting.add(f"Q2:Q{son}", DataBarRule(start_type="min", end_type="max", color="EB6834"))
        ws.freeze_panes = "B2"

        # --- Fiyat-Performans + grafik
        fp.to_excel(xw, sheet_name="Fiyat-Performans", index=False)
        ws = xw.sheets["Fiyat-Performans"]
        baslik(ws, {"A": 20, "B": 9, "C": 9, "D": 13, "E": 13, "F": 15, "G": 11, "H": 16, "I": 18})
        ws.row_dimensions[1].height = 45
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.number_format = {"D": "$0.0000", "E": "0.0", "F": "$0.0000", "G": "0.00", "H": "0.0\"x\"", "I": "+0.0;-0.0;0.0"}.get(c.column_letter, "General")
        ch = ScatterChart()
        ch.title = "Fiyat – doğruluk (sol üst = daha verimli)"
        ch.style = 13
        ch.x_axis.title = "1.000 soru maliyeti ($, log ölçek)"
        ch.y_axis.title = "Doğruluk (%)"
        ch.x_axis.scaling.logBase = 10
        ch.y_axis.scaling.min, ch.y_axis.scaling.max = 80, 100
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.majorGridlines = None
        ch.height, ch.width = 10, 18
        for i, r in enumerate(fp.itertuples(), start=2):
            s = Series(Reference(ws, min_col=5, min_row=i), Reference(ws, min_col=4, min_row=i),
                       title=f"{r.Model} ({r.Aile}, {r.Kademe.lower()})")
            renk = RENK[r.Aile]
            s.marker.symbol = SEKIL[{v: k for k, v in KADEME.items()}[r.Kademe]]
            s.marker.size = 11
            s.marker.graphicalProperties.solidFill = renk
            s.marker.graphicalProperties.line.solidFill = "FFFFFF"
            s.graphicalProperties.line.noFill = True
            ch.series.append(s)
        ws.add_chart(ch, "A10")
        ws["K10"] = "Nasıl okunur?"
        ws["K10"].font = Font(bold=True)
        for j, t in enumerate(["Renk = aile (mavi Qwen, turuncu Mistral)",
                               "Şekil = kademe (daire ucuz, üçgen orta, elmas pahalı)",
                               "Sağa gittikçe pahalı (log ölçek: her çizgi 10 kat), yukarı gittikçe doğru.",
                               "Orta ve pahalı modeller %98–100 bandında üst üste biniyor:",
                               "aralarındaki fark istatistiksel olarak anlamlı değil, fiyat farkı 1.5–6 kat."], start=11):
            ws[f"K{j}"] = t

        # --- Kategori ve Zorluk ısı haritası
        kz = kat.reindex(sira).round(1)
        kz.insert(0, "Genel", karne.set_index("Model")["Doğruluk % (4 ayar ort.)"].round(1))
        kz = kz.join(zor.reindex(sira).round(1))
        kz.index.name = "Model"
        kz.to_excel(xw, sheet_name="Kategori ve Zorluk")
        ws = xw.sheets["Kategori ve Zorluk"]
        baslik(ws, {"A": 20, **{c: 13 for c in "BCDEFGHIJK"}})
        ws.conditional_formatting.add(f"B2:K{len(kz) + 1}", ColorScaleRule(start_type="num", start_value=65, start_color="CDE2FB",
                                                                           end_type="num", end_value=100, end_color="5598E7"))
        ws[f"A{len(kz) + 3}"] = "Değerler ortalama doğruluk (%), 4 ayarın ortalaması. Koyu = yüksek doğruluk."

        # --- Takıldığı sorular
        tak.to_excel(xw, sheet_name="Takıldığı Sorular", index=False)
        ws = xw.sheets["Takıldığı Sorular"]
        baslik(ws, {"A": 19, "B": 7, "C": 13, "D": 8, "E": 45, "F": 28, "G": 11, "H": 30, "I": 8, "J": 35, "K": 8, "L": 11, "M": 50})
        ws.row_dimensions[1].height = 45
        sar(ws, {"E", "F", "H", "J", "M"})
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions

        # --- Ortak zor sorular
        ortak.to_excel(xw, sheet_name="Ortak Zor Sorular", index=False)
        ws = xw.sheets["Ortak Zor Sorular"]
        baslik(ws, {"A": 7, "B": 13, "C": 8, "D": 50, "E": 28, "F": 12, "G": 55})
        sar(ws, {"D", "E", "G"})
        for row in ws.iter_rows(min_row=2):
            row[5].number_format = "0.0"

        # --- Bulgular
        pd.DataFrame(bulgular, columns=["Konu", "Bulgu"]).to_excel(xw, sheet_name="Bulgular", index=False)
        ws = xw.sheets["Bulgular"]
        baslik(ws, {"A": 26, "B": 120})
        sar(ws, {"B"})
        for row in ws.iter_rows(min_row=2):
            row[0].font = Font(bold=True)

        xw.book.move_sheet("Bulgular", offset=-5)  # ilk sayfa olsun
    print(f"Kaydedildi: {CIKTI}")
    print(karne[["Model", "Doğruluk % (4 ayar ort.)", "Tamamen yanlış %", "1.000 doğru cevap $", "Doğruluk sırası",
                 "Doğru cevap başına ucuzluk sırası", "En zayıf kategori"]].round(4).to_string(index=False))
    print(f"\nTakıldığı soru satırı: {len(tak)} | model başına: {tak['Model'].value_counts().reindex(sira).to_dict()}")


if __name__ == "__main__":
    main()
