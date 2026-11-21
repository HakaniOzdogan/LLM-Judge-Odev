r"""Model Karnesi'ni internetsiz açılan tek bir HTML dosyası olarak üretir: rapor/model_karnesi.html
Grafikler SVG olarak gömülür; dış kütüphane, yazı tipi veya bağlantı yoktur.
Veri: araclar/karne_verisi.py'nin ürettiği JSON dosyaları (bu betik onu geçici bir klasörde çalıştırır).
Çalıştır:  .venv\Scripts\python araclar\karne_html.py
"""
import html, json, math, os, subprocess, sys, tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(KOK, "rapor", "model_karnesi.html")
E = html.escape

tmp = tempfile.mkdtemp()
subprocess.run([sys.executable, os.path.join(KOK, "araclar", "karne_verisi.py"), tmp], check=True, capture_output=True)
oku = lambda ad: json.load(open(os.path.join(tmp, ad), encoding="utf-8"))["rows"]
M, AY, KAT, TAK, NOT = (oku(a) for a in ("modeller.json", "model_ayar.json", "model_kategori.json", "takildigi.json", "notlar.json"))
M.sort(key=lambda r: r["sira"])
BY = {r["model"]: r for r in M}


def tr(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


pct = lambda x, d=1: "%" + tr(x, d)
usd = lambda x, d=4: "$" + tr(x, d)
FAM = {"Qwen": "c-qwen", "Mistral": "c-mistral"}
kisa = lambda m: m.replace("-2512", "")


def tip(*lines):
    return E("\n".join(lines), quote=True)


def svg(w, h, label, body):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{E(label, quote=True)}" '
            f'preserveAspectRatio="xMinYMin meet">{body}</svg>')


# ---------- 1. sıralama
def siralama():
    D = sorted(M, key=lambda r: -r["dogruluk"])
    W, rh, L, R = 720, 36, 150, 64
    x = lambda v: L + (W - L - R) * v / 100
    b = []
    for t in (0, 25, 50, 75, 100):
        b.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="0" y2="{len(D) * rh}"/>'
                 f'<text class="ax" x="{x(t):.1f}" y="{len(D) * rh + 16}" text-anchor="middle">%{t}</text>')
    for i, r in enumerate(D):
        y = i * rh
        b.append(f'<text class="ink" x="{L - 10}" y="{y + rh / 2}" dy="0.35em" text-anchor="end">{E(r["model"])}</text>'
                 f'<rect class="{FAM[r["aile"]]}" x="{x(0):.1f}" y="{y + 8}" width="{x(r["dogruluk"]) - x(0):.1f}" height="{rh - 16}" rx="4"/>'
                 f'<text class="ink" x="{x(r["dogruluk"]) + 6:.1f}" y="{y + rh / 2}" dy="0.35em">{pct(r["dogruluk"])}</text>'
                 f'<rect class="hit" x="0" y="{y}" width="{W}" height="{rh}" data-tip="{tip(r["model"] + " · " + r["aile"] + ", " + r["kademe"].lower(), "Doğruluk: " + pct(r["dogruluk"]), "Tam doğru: " + pct(r["tam_dogru"]), "Tamamen yanlış: " + pct(r["sifir"]))}"/>')
    return svg(W, len(D) * rh + 24, "Doğruluk sıralaması: " + ", ".join(f'{r["model"]} {pct(r["dogruluk"])}' for r in D), "".join(b))


# ---------- 2. fiyat-doğruluk
def fiyat():
    W, H, ml, mr, mt, mb = 720, 340, 52, 24, 20, 48
    xs = [r["maliyet_1000_soru"] for r in M]
    lo, hi = min(xs) / 2, max(xs) * 2.2
    x = lambda v: ml + (W - ml - mr) * (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    ymin = math.floor((min(r["dogruluk"] for r in M) - 4) / 5) * 5
    y = lambda v: H - mb - (H - mb - mt) * (v - ymin) / (102 - ymin)
    b = []
    for t in range(ymin, 101, 5):
        b.append(f'<line class="grid" x1="{ml}" x2="{W - mr}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                 f'<text class="ax" x="{ml - 8}" y="{y(t):.1f}" dy="0.35em" text-anchor="end">%{t}</text>')
    for t in (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1):
        if lo <= t <= hi:
            b.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{mt}" y2="{H - mb}"/>'
                     f'<text class="ax" x="{x(t):.1f}" y="{H - mb + 17}" text-anchor="middle">${tr(t, 3).rstrip("0").rstrip(",")}</text>')
    b.append(f'<text class="ax" x="{(ml + W - mr) / 2}" y="{H - 8}" text-anchor="middle">1.000 soru maliyeti (log ölçek)</text>')
    for i, r in enumerate(sorted(M, key=lambda r: r["maliyet_1000_soru"])):
        cx, cy = x(r["maliyet_1000_soru"]), y(r["dogruluk"])
        ly = cy + (21 if i % 2 else -13)
        b.append(f'<circle class="{FAM[r["aile"]]} dot" cx="{cx:.1f}" cy="{cy:.1f}" r="7"/>'
                 f'<text class="ink" x="{cx:.1f}" y="{ly:.1f}" text-anchor="middle">{E(kisa(r["model"]))}</text>'
                 f'<circle class="hit" cx="{cx:.1f}" cy="{cy:.1f}" r="18" data-tip="{tip(r["model"], "Doğruluk: " + pct(r["dogruluk"]), "1.000 soru: " + usd(r["maliyet_1000_soru"]), "1.000 doğru cevap: " + usd(r["maliyet_1000_dogru"]), "1 milyon soru: $" + tr(r["maliyet_1m_soru"]))}"/>')
    return svg(W, H, "Fiyat ve doğruluk: " + "; ".join(f'{r["model"]} {usd(r["maliyet_1000_soru"])}, {pct(r["dogruluk"])}' for r in M), "".join(b))


# ---------- 3. ısı haritası
def isi():
    cats = sorted({r["kategori"] for r in KAT})
    val = {(r["model"], r["kategori"]): r["dogruluk"] for r in KAT}
    a = lambda v: round(6 + 58 * max(0, min(1, (v - 65) / 35)))
    cell = lambda v, mn=False: (f'<td style="background:color-mix(in srgb, var(--qwen) {a(v)}%, transparent)"'
                                f'{" class=mn" if mn else ""}>{pct(v)}</td>')
    h = ['<table class="heat"><thead><tr><th class="l">Model</th>', *[f"<th>{E(c)}</th>" for c in cats],
         '<th class="gap"></th><th>Kolay</th><th>Orta</th><th>Zor</th></tr></thead><tbody>']
    for r in M:
        vs = [val[(r["model"], c)] for c in cats]
        mn = min(vs)
        h.append(f'<tr><th scope="row" class="l">{E(r["model"])}</th>'
                 + "".join(cell(v, v == mn and mn < 99.5) for v in vs)
                 + '<td class="gap"></td>' + "".join(cell(r[z]) for z in ("kolay", "orta", "zor")) + "</tr>")
    return "".join(h) + "</tbody></table>"


# ---------- 4. temperature küçük grafikleri
def mini(m):
    D = sorted([r for r in AY if r["model"] == m], key=lambda r: r["ayar_sira"])
    W, H, l, rr, t, bb = 240, 132, 16, 16, 18, 22
    xs = [l + 16 + (W - l - rr - 32) * i / (len(D) - 1) for i in range(len(D))]
    y = lambda v: H - bb - (H - bb - t) * (v - 75) / 25
    c = FAM[BY[m]["aile"]]
    kis = ["T=0", "T=0,7", "T=1", "T=1·p0,5"]
    b = [f'<line class="grid" x1="{l}" x2="{W - rr}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>' for v in (75, 100)]  # ölçek (%75–100) bölüm açıklamasında
    b.append(f'<polyline class="{c} line" points="{" ".join(f"{xs[i]:.1f},{y(r["dogruluk"]):.1f}" for i, r in enumerate(D))}"/>')
    for i, r in enumerate(D):
        lines = [m + " · " + r["ayar"], "Doğruluk: " + pct(r["dogruluk"])]
        if r["metin_degisen"] is not None:
            lines += [f"T=0'a göre metni değişen: {r['metin_degisen']} / 100", f"Puanı değişen: {r['puan_degisen']} / 100"]
        b.append(f'<circle class="{c} dot" cx="{xs[i]:.1f}" cy="{y(r["dogruluk"]):.1f}" r="4.5"/>'
                 f'<text class="ink" x="{xs[i]:.1f}" y="{y(r["dogruluk"]) - 9:.1f}" text-anchor="middle">{tr(r["dogruluk"])}</text>'
                 f'<text class="ax" x="{xs[i]:.1f}" y="{H - 6}" text-anchor="middle">{kis[i]}</text>'
                 f'<circle class="hit" cx="{xs[i]:.1f}" cy="{y(r["dogruluk"]):.1f}" r="16" data-tip="{tip(*lines)}"/>')
    return (f'<div class="mini chart"><h3><span class="sw {c}"></span>{E(m)}</h3>'
            + svg(W, H, m + " doğruluğu ayarlara göre: " + ", ".join(f'{r["ayar"]} {pct(r["dogruluk"])}' for r in D), "".join(b)) + "</div>")


# ---------- 5. metni değişen cevaplar
def degisim():
    S = [("T=1", "c-s3"), ("T=1 · top_p=0.5", "c-s4")]
    get = {(r["model"], r["ayar"]): r for r in AY}
    W, L, R, bh, g = 720, 150, 40, 12, 3
    rh = 2 * bh + g + 14
    mx = max(40, max(get[(r["model"], s)]["metin_degisen"] for r in M for s, _ in S))
    x = lambda v: L + (W - L - R) * v / mx
    b = []
    ticks = [t for t in range(0, mx + 1, 10)]
    for t in ticks:
        b.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="0" y2="{len(M) * rh}"/>'
                 f'<text class="ax" x="{x(t):.1f}" y="{len(M) * rh + 16}" text-anchor="middle">{t}</text>')
    for i, r in enumerate(M):
        y0 = i * rh + 7
        b.append(f'<text class="ink" x="{L - 10}" y="{y0 + bh + g / 2}" dy="0.35em" text-anchor="end">{E(r["model"])}</text>')
        for k, (s, c) in enumerate(S):
            v = get[(r["model"], s)]["metin_degisen"]
            yy = y0 + k * (bh + g)
            b.append(f'<rect class="{c}" x="{x(0):.1f}" y="{yy}" width="{x(v) - x(0):.1f}" height="{bh}" rx="3"/>'
                     f'<text class="ax" x="{x(v) + 5:.1f}" y="{yy + bh / 2}" dy="0.35em">{v}</text>')
        a, p = get[(r["model"], "T=1")], get[(r["model"], "T=1 · top_p=0.5")]
        b.append(f'<rect class="hit" x="0" y="{i * rh}" width="{W}" height="{rh}" data-tip="{tip(r["model"], f"T=1: metni değişen {a["metin_degisen"]}, puanı değişen {a["puan_degisen"]}", f"T=1 · top_p=0,5: metni değişen {p["metin_degisen"]}, puanı değişen {p["puan_degisen"]}")}"/>')
    return svg(W, len(M) * rh + 24, "T=0'a göre metni değişen cevap sayısı, T=1 ve T=1 top_p=0.5", "".join(b))


# ---------- 6. model kartları
def katbar(m):
    D = sorted([r for r in KAT if r["model"] == m], key=lambda r: -r["dogruluk"])
    W, rh, L, R = 380, 26, 112, 56
    x = lambda v: L + (W - L - R) * (max(50, v) - 50) / 50
    c = FAM[BY[m]["aile"]]
    b = []
    for t in (50, 75, 100):
        b.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="0" y2="{len(D) * rh}"/>'
                 f'<text class="ax" x="{x(t):.1f}" y="{len(D) * rh + 14}" text-anchor="middle">%{t}</text>')
    for i, r in enumerate(D):
        y = i * rh + rh / 2
        b.append(f'<text class="ink" x="{L - 10}" y="{y}" dy="0.35em" text-anchor="end">{E(r["kategori"])}</text>'
                 f'<line class="{c} stem" x1="{x(50):.1f}" x2="{x(r["dogruluk"]):.1f}" y1="{y}" y2="{y}"/>'
                 f'<circle class="{c} dot2" cx="{x(r["dogruluk"]):.1f}" cy="{y}" r="5.5"/>'
                 f'<text class="ax" x="{x(r["dogruluk"]) + 10:.1f}" y="{y}" dy="0.35em">{pct(r["dogruluk"])}</text>')
    return svg(W, len(D) * rh + 20, m + " kategorilere göre doğruluk: " + ", ".join(f'{r["kategori"]} {pct(r["dogruluk"])}' for r in D), "".join(b))


def kart(r):
    m = r["model"]
    c = FAM[r["aile"]]
    stats = [("Doğruluk (4 ayar)", pct(r["dogruluk"])), ("Doğruluk (T=0)", pct(r["dogruluk_t0"])),
             ("Tamamen yanlış", pct(r["sifir"])), ("Zor sorularda", pct(r["zor"])),
             ("Ort. cevap süresi", tr(r["sure_sn"], 2) + " sn"), ("1.000 doğru cevap", usd(r["maliyet_1000_dogru"]))]
    notes = lambda tur: "".join(f"<li>{E(n['metin'])}</li>" for n in sorted((n for n in NOT if n["model"] == m and n["tur"] == tur), key=lambda n: n["sira"]))
    qs = [q for q in TAK if q["model"] == m][:5]
    rows = "".join(f'<tr><td>{E(q["soru"])}</td><td>{E(q["ana_cevap"])}</td><td>{E(q["model_cevabi"])}</td>'
                   f'<td class="num">{q["en_dusuk_puan"]}</td><td class="num">{q["yanlis_ayar"]}</td></tr>' for q in qs)
    return f'''
<article class="card" id="m-{m.replace('.', '-')}">
  <header><h3>{E(m)}</h3>
    <span class="chip"><span class="sw {c}"></span>{r["aile"]} · {r["kademe"]} kademe · 1M token: giriş {usd(r["giris_fiyat"], 3)} / çıkış {usd(r["cikis_fiyat"], 3)}</span></header>
  <dl class="stats">{"".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in stats)}</dl>
  <div class="pc">
    <div><h4><span class="plus" aria-hidden="true">+</span>Artıları</h4><ul>{notes("arti")}</ul></div>
    <div><h4><span class="minus" aria-hidden="true">−</span>Eksileri</h4><ul>{notes("eksi")}</ul></div>
  </div>
  <div class="two">
    <div class="block"><p class="sub2">Kategorilere göre doğruluk</p><div class="chart">{katbar(m)}</div></div>
    <div class="block"><p class="sub2">En çok takıldığı sorular <span class="muted">(tam puan alamadığı {r["takildigi_soru"]} sorunun ilk {len(qs)} tanesi)</span></p>
      <div class="scroll"><table class="qs"><thead><tr><th>Soru</th><th>Doğru cevap</th><th>Modelin en kötü cevabı</th><th class="num">Puan</th><th class="num">Kaç ayarda (4)</th></tr></thead>
      <tbody>{rows}</tbody></table></div></div>
  </div>
</article>'''


best = max(M, key=lambda r: r["dogruluk"])
worst = min(M, key=lambda r: r["dogruluk"])
val = min((r for r in M if r["dogruluk"] >= best["dogruluk"] - 2), key=lambda r: r["maliyet_1000_dogru"])
ozet = (f"{best['model']} en doğru model ({pct(best['dogruluk'])}). Fiyat/performansta öne çıkan {val['model']}: doğruluğu "
        f"{pct(val['dogruluk'])}, 1.000 doğru cevap maliyeti {usd(val['maliyet_1000_dogru'])} (en doğru modelde "
        f"{usd(best['maliyet_1000_dogru'])}). En zayıf model {worst['model']} ({pct(worst['dogruluk'])}).")
legend = '<ul class="legend"><li><span class="sw c-qwen"></span>Qwen ailesi</li><li><span class="sw c-mistral"></span>Mistral ailesi</li></ul>'

CSS = r'''
:root { --bg:#f7f8fa; --panel:#ffffff; --fg:#17191d; --muted:#5b6170; --line:#e1e4ea; --grid:#e8eaef; --axis:#6a7080;
  --qwen:#2a78d6; --mistral:#eb6834; --s3:#1baf7a; --s4:#eda100; --ok:#1d7f4e; --bad:#c2372d; --tipbg:#ffffff; --shadow:0 6px 24px rgba(20,24,32,.14);
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; --serif: Georgia, "Times New Roman", serif; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141518; --panel:#1c1e22; --fg:#eceef2; --muted:#a3a9b6; --line:#2e3138; --grid:#2a2d33; --axis:#9aa0ad;
  --qwen:#3987e5; --mistral:#d95926; --s3:#199e70; --s4:#c98500; --ok:#4cc38a; --bad:#ff7b72; --tipbg:#24272c; --shadow:0 6px 24px rgba(0,0,0,.5); color-scheme: dark; } }
:root[data-theme="dark"] { --bg:#141518; --panel:#1c1e22; --fg:#eceef2; --muted:#a3a9b6; --line:#2e3138; --grid:#2a2d33; --axis:#9aa0ad;
  --qwen:#3987e5; --mistral:#d95926; --s3:#199e70; --s4:#c98500; --ok:#4cc38a; --bad:#ff7b72; --tipbg:#24272c; --shadow:0 6px 24px rgba(0,0,0,.5); color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.55 var(--sans); }
main { max-width: 1040px; margin: 0 auto; padding: 32px max(16px, env(safe-area-inset-right, 0px)) 64px max(16px, env(safe-area-inset-left, 0px)); display: grid; gap: 44px; }
h1 { font-family: var(--serif); font-weight: 400; font-size: 2.4rem; line-height: 1.15; margin: 0; text-wrap: balance; }
h2 { font-size: 1.3rem; font-weight: 600; margin: 0; text-wrap: balance; }
.lede { font-size: 1.15rem; line-height: 1.45; margin: 12px 0 0; max-width: 66ch; }
.sub, .note { color: var(--muted); font-size: .88rem; margin: 0; max-width: 74ch; }
.sub { margin-top: 10px; }
section { display: grid; gap: 14px; min-width: 0; }
.legend { display: flex; flex-wrap: wrap; gap: 16px; list-style: none; margin: 10px 0 0; padding: 0; font-size: .85rem; color: var(--muted); }
.legend li { display: flex; align-items: center; gap: 6px; }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px; flex: none; }
.sw.c-qwen { background: var(--qwen); } .sw.c-mistral { background: var(--mistral); } .sw.c-s3 { background: var(--s3); } .sw.c-s4 { background: var(--s4); }
.chart { position: relative; min-width: 0; }
.chart svg { display: block; overflow: visible; }
svg text { font-family: var(--sans); font-size: 12px; font-variant-numeric: tabular-nums; }
svg .ax { fill: var(--axis); } svg .ink { fill: var(--fg); }
svg .grid { stroke: var(--grid); stroke-width: 1; }
svg rect.c-qwen, svg circle.c-qwen { fill: var(--qwen); } svg rect.c-mistral, svg circle.c-mistral { fill: var(--mistral); }
svg rect.c-s3 { fill: var(--s3); } svg rect.c-s4 { fill: var(--s4); }
svg .dot { stroke: var(--bg); stroke-width: 2; } svg .dot2 { stroke: var(--panel); stroke-width: 2; }
svg polyline.line { fill: none; stroke-width: 2; } svg polyline.c-qwen { stroke: var(--qwen); } svg polyline.c-mistral { stroke: var(--mistral); }
svg line.stem { stroke-width: 2; opacity: .45; } svg line.stem.c-qwen { stroke: var(--qwen); } svg line.stem.c-mistral { stroke: var(--mistral); }
svg .hit { fill: transparent; }
.tip { position: absolute; z-index: 5; pointer-events: none; background: var(--tipbg); border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 8px; padding: 6px 10px; font-size: .8rem; white-space: pre; line-height: 1.5; }
.tip::first-line { font-weight: 600; }
.scroll { overflow-x: auto; min-width: 0; }
.heat { border-collapse: separate; border-spacing: 3px; width: 100%; font-size: .82rem; font-variant-numeric: tabular-nums; }
.heat th { font-weight: 600; color: var(--muted); padding: 4px 6px; white-space: nowrap; }
.heat th.l { text-align: left; color: var(--fg); }
.heat td { text-align: center; padding: 9px 6px; border-radius: 5px; min-width: 60px; }
.heat td.mn { font-weight: 700; outline: 1.5px solid var(--muted); outline-offset: -1.5px; }
.heat .gap { width: 10px; min-width: 10px; padding: 0; background: none; }
.multi { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.mini { border: 1px solid var(--line); border-radius: 10px; padding: 12px; background: var(--panel); }
.mini h3 { margin: 0 0 4px; font-size: .95rem; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.cards { display: grid; gap: 22px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 22px; display: grid; gap: 20px; min-width: 0; }
.card header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; }
.card h3 { margin: 0; font-size: 1.25rem; font-weight: 600; }
.chip { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 6px; color: var(--muted); font-size: .85rem; font-variant-numeric: tabular-nums; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 14px; margin: 0; }
.stats div { display: grid; gap: 2px; align-content: start; }
.stats dt { color: var(--muted); font-size: .8rem; }
.stats dd { margin: 0; font-family: var(--serif); font-size: 1.45rem; font-variant-numeric: tabular-nums; }
.pc { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 22px; }
.pc h4 { margin: 0 0 6px; font-size: 1rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.pc ul { margin: 0; padding-left: 1.15em; display: grid; gap: 6px; max-width: 62ch; }
.plus, .minus { display: inline-grid; place-items: center; width: 19px; height: 19px; border-radius: 50%; color: var(--panel); font-weight: 700; line-height: 1; }
.plus { background: var(--ok); } .minus { background: var(--bad); }
.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 22px; }
.block { display: grid; gap: 8px; align-content: start; min-width: 0; }
.sub2 { margin: 0; font-weight: 600; }
.muted { color: var(--muted); font-weight: 400; font-size: .85rem; }
.qs { width: 100%; border-collapse: collapse; font-size: .82rem; }
.qs th { text-align: left; color: var(--muted); font-weight: 600; padding: 6px 8px; border-bottom: 1px solid var(--line); }
.qs td { padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
.qs .num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
footer { color: var(--muted); font-size: .82rem; border-top: 1px solid var(--line); padding-top: 16px; }
@media (max-width: 520px) { h1 { font-size: 1.9rem; } .card { padding: 16px; } }
@media print { .tip { display: none; } .card { break-inside: avoid; } }
'''

JS = r'''
document.querySelectorAll(".chart").forEach(function (box) {
  var t = document.createElement("div"); t.className = "tip"; t.hidden = true; box.appendChild(t);
  box.addEventListener("pointermove", function (ev) {
    var h = ev.target.closest ? ev.target.closest("[data-tip]") : null;
    if (!h || !box.contains(h)) { t.hidden = true; return; }
    t.textContent = h.getAttribute("data-tip"); t.hidden = false;
    var r = box.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
    t.style.left = Math.max(0, Math.min(x + 12, box.clientWidth - t.offsetWidth)) + "px";
    t.style.top = Math.max(0, y - t.offsetHeight - 10) + "px";
  });
  box.addEventListener("pointerleave", function () { t.hidden = true; });
});
'''

HTML = f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Model Karnesi</title><style>{CSS}</style></head>
<body><main>
<header>
  <h1>Model Karnesi</h1>
  <p class="lede">{E(ozet)}</p>
  <p class="sub">Qwen ve Mistral ailelerinden ucuz, orta ve pahalı kademede 6 model, 100 Türkçe bilgi sorusu ve 4 temperature/top_p ayarı: toplam 2.400 cevap. Her cevabı hakem model gpt-4.1-mini (temperature 0) referans cevaba göre 0–100 arasında puanladı; doğruluk bu puanların ortalamasıdır. Grafiklerin üzerine gelince ayrıntılar görünür.</p>
  {legend}
</header>

<section id="siralama"><h2>Doğruluk sıralaması</h2>
  <p class="note">Dört ayarın ortalaması.</p>
  <div class="chart">{siralama()}</div></section>

<section id="fiyat"><h2>Fiyat ve doğruluk</h2>
  <p class="note">Yatay eksen 1.000 soru için ödenen ücret, log ölçekte. Sol üst köşe en verimli bölge. Orta ve pahalı kademedeki dört model üst bantta toplanıyor; aralarındaki doğruluk farkları istatistiksel olarak anlamlı değil, fiyatları ise birkaç kat değişiyor.</p>
  {legend}
  <div class="chart">{fiyat()}</div></section>

<section id="kategori"><h2>Kategori ve zorluğa göre doğruluk</h2>
  <p class="note">Koyu hücre yüksek doğruluk demek. Çerçeveli hücre, o modelin en zayıf kategorisi. Modellerin takıldığı yer Türkiye'ye özgü edebiyat ve spor soruları.</p>
  <div class="scroll">{isi()}</div></section>

<section id="temperature"><h2>temperature ve top_p etkisi</h2>
  <p class="note">Her kutu bir modelin dört ayardaki doğruluğunu gösterir (ölçek %75–100). Ucuz modellerin çizgisi T=1'de aşağı kırılıyor, pahalı modellerin çizgisi düz kalıyor.</p>
  <div class="multi">{"".join(mini(r["model"]) for r in M)}</div>
  <p class="sub2">T=0'daki cevaba göre metni değişen cevap sayısı (100 soruda)</p>
  <ul class="legend"><li><span class="sw c-s3"></span>T=1, top_p=1</li><li><span class="sw c-s4"></span>T=1, top_p=0,5</li></ul>
  <div class="chart">{degisim()}</div>
  <p class="note">top_p=0,5 düşük olasılıklı kelimeleri elediği için, aynı temperature'da cevapların çok daha azı değişiyor. Üzerine gelince kaç cevabın puanının da değiştiği görünür.</p></section>

<section id="modeller"><h2>Model model artılar ve eksiler</h2>
  <p class="note">Her kart bir modelin ana rakamlarını, güçlü ve zayıf yanlarını, kategorilere göre doğruluğunu ve en çok takıldığı soruları gösterir.</p>
  <div class="cards">{"".join(kart(r) for r in M)}</div></section>

<footer>Kaynak: <code>sonuclar/sonuclar.xlsx</code> (20.11.2026 deneyi). Bu dosya <code>araclar/karne_html.py</code> ile üretildi; ayrıntılı yöntem ve yorumlar <code>rapor/RAPOR.md</code> içinde. Veri seti taslaktır (Ana Cevaplar kaynakla tek tek doğrulanmadı); her ayar tek tekrarla çalıştırıldı.</footer>
</main><script>{JS}</script></body></html>
'''
open(CIKTI, "w", encoding="utf-8").write(HTML)
print("Kaydedildi:", CIKTI, f"({len(HTML) // 1024} KB)")
