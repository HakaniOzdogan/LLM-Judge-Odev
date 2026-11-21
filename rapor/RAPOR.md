# LLM Değerlendirme (LLM-as-a-Judge) ve A/B Testi — Gerekçeli Model Raporu

> **Durum:** Taslak. Sayısal veriler 20.11.2026 tarihli tam deneyden (`sonuclar/sonuclar.xlsx`) alınmıştır.
> ✍️ işaretli yerler yorum içindir; doldurulacak.
> ⚠️ Deney, henüz kaynakla doğrulanmamış **taslak veri setiyle** (`veri/dataset_taslak.xlsx`) çalıştırıldı. Doğrulama sonrası Ana Cevap'ı değişen sorular olursa yalnızca hakem adımı yeniden çalıştırılmalıdır (bkz. §9).

---

## 1. Özet

İki model ailesinden (Qwen, Mistral) ucuz / orta / pahalı kademede **6 model**, 100 soruluk Türkçe bilgi seti üzerinde **4 farklı temperature / top_p ayarıyla** test edildi (2.400 cevap). Her cevap, test edilen ailelerin dışından seçilen bir hakem model (`openai/gpt-4.1-mini`, temperature = 0) tarafından referans cevaba göre 0–100 arasında puanlandı (2.400 puan).

| | |
|---|---|
| Toplam çağrı | 2.400 cevap + 2.400 hakem |
| Kalıcı hata | 0 (16 geçici 429 hatası otomatik yeniden denemeyle giderildi) |
| Toplam maliyet | Cevaplar **$0.117** + hakem **$0.472** = **$0.588** |
| En yüksek doğruluk | qwen3.7-max %99.9 · mistral-medium-3.5 %99.4 |
| En düşük doğruluk | ministral-8b %82.0 · qwen3.7-flash %91.2 |
| En verimli (1.000 doğru cevap başına maliyet) | qwen3.7-flash $0.0025 · ministral-8b $0.0091 · qwen3.7-plus $0.0229 |

---

## 2. Veri Seti

`veri/dataset_taslak.xlsx` — 100 soru, her biri tek ve zamandan bağımsız bir doğru cevaba sahip; web araması gerektirmez.

| Kategori | Kolay | Orta | Zor | Toplam |
|---|---|---|---|---|
| Tarih | 5 | 9 | 4 | 18 |
| Bilim | 6 | 8 | 4 | 18 |
| Coğrafya | 5 | 10 | 2 | 17 |
| Edebiyat-Sanat | 5 | 9 | 3 | 17 |
| Spor | 5 | 7 | 3 | 15 |
| Genel Kültür | 3 | 9 | 3 | 15 |
| **Toplam** | **29** | **52** | **19** | **100** |

- **Soru türleri:** 43 tek cevaplı, 43 sayısal/tarih, 14 çok parçalı (kısmi puan gerektiren: ör. Türkiye'nin 8 kara komşusu, Mimar Sinan'ın üç eseri).
- **Bilinçli tuzaklar:** sık karıştırılan cevaplar (Avustralya → Kanberra, Brezilya → Brasília), referans tanımına bağlı sorular (Türkiye sınırları içinde doğup denize dökülen en uzun nehir → Kızılırmak), sayısal yuvarlama (Everest 8.849 m).
- **Hakem Notu sütunu:** kabul edilebilir varyantları ve parça sayısını belirtir; hakem prompt'una eklenir.
- ✍️ **Doğrulama:** her Ana Cevap'ın kaynağı `Kaynak` sütununa yazılacak.

---

## 3. Model Seçimi ve Gerekçesi

### 3.1 Seçilen modeller

| Aile | Kademe | Model id | Sağlayıcı | Giriş / Çıkış ($/1M token) | Düşünme özelliği |
|---|---|---|---|---|---|
| Qwen | Ucuz | `qwen/qwen3.7-flash` | Alibaba | 0.030 / 0.130 | Var → kapatıldı |
| Qwen | Orta | `qwen/qwen3.7-plus` | Alibaba | 0.320 / 1.280 | Var → kapatıldı |
| Qwen | Pahalı | `qwen/qwen3.7-max` | Alibaba | 1.475 / 4.425 | Var → kapatıldı |
| Mistral | Ucuz | `mistralai/ministral-8b-2512` | Mistral | 0.150 / 0.150 | Yok |
| Mistral | Orta | `mistralai/mistral-large-2512` | Mistral | 0.500 / 1.500 | Yok |
| Mistral | Pahalı | `mistralai/mistral-medium-3-5` | Mistral | 1.500 / 7.500 | Var → kapatıldı |

Çıkış fiyatına göre aile içi fark: Qwen **34 kat** (0.13 → 4.43), Mistral **50 kat** (0.15 → 7.50).

### 3.2 Seçim ölçütleri

1. **temperature ve top_p desteği (zorunlu).** OpenRouter kataloğundaki 477 modelin 122'si temperature parametresini desteklemiyordu; bu modeller ödevin parametre analizi için elendi. Destek, model düzeyinde değil **sağlayıcı düzeyinde** kontrol edildi (ör. Kimi K3.1 Pro'nun Amazon Bedrock sağlayıcısı temperature desteklemiyordu).
2. **Düşünme (reasoning) modunun kapatılabilmesi.** İlk aday Qwen3.8 Flash ile yapılan denemede düşünme varsayılan olarak açıktı: faturalanan çıkış tokenlerinin %90'ından fazlası görünmeyen düşünme metniydi ve `max_tokens = 300` ile T = 1.0'da **3 denemenin 3'ünde cevap boş döndü** (düşünme tüm token hakkını tüketti). Düşünme kapatılınca cevap başına çıkış 4–8 tokene, süre ~1 saniyeye indi. Modeller arası adil karşılaştırma için deneyde **6 modelin hepsinde düşünme kapalıdır** (özelliği olmayan 3 modelde zaten yok).
3. **Aile içinde tek eksen: fiyat/boyut kademesi.** Her aileden ucuz, orta ve pahalı birer model alınarak "aile mi, kademe mi daha belirleyici?" sorusu test edilebilir hâle getirildi. Qwen'de üç model de aynı nesilden (3.7) seçildi; böylece nesil farkı karışmadan yalnızca kademe değişir.
4. **Farklı aileler.** Çin (Alibaba) ve Avrupa (Mistral) menşeli iki aile.
5. **Sağlayıcı sabitliği ve tekrarlanabilirlik.** Seçilen 6 modelin her biri tek bir sağlayıcıdan (modeli geliştiren şirketin kendisi) sunuluyor; deney boyunca sağlayıcı değişmez.

### 3.3 Değerlendirilip elenen adaylar

| Aday | Neden elendi |
|---|---|
| **Google Gemini 4 Neon** (ve tüm Gemini 4 serisi) | Düşünme **zorunlu**; kapatma isteği `400: Reasoning is mandatory` hatası verdi. Google'ın 24 modelinden yalnızca 11'inde (Gemma ve Gemini 2.5/3.1 Flash-Lite serileri) düşünme kapatılabildi. Düşünmesi kapalı diğer modellerle adil kıyaslanamayacağı için çıkarıldı. |
| **Kimi ailesi** (K2 / K2.6 / K3.1 Pro) | İlk planda üçüncü aileydi. Aile içi fiyat aralığı yalnızca **7 kat** (en ucuz modelin çıkışı bile $2.30); ailede küçük model yok, bu yüzden kademe etkisini ayırt etmek zor. K2.6'nın 16, K3.1 Pro'nun 28 sağlayıcısı var; 4 test çağrısına 4 farklı sağlayıcı cevap verdi, sabitleme zorunlu. Ayrıca orijinal ağırlıklar 4 bit (aşağıda §8.3). Deney 2 aileye indirildiğinde çıkarıldı. |
| **Qwen3.8 Flash** (ilk aday) | Uygun bir modeldi; Qwen ailesinde tek nesilden (3.7) ucuz/orta/pahalı üçlüsü kurulabilmesi için 3.7 serisi tercih edildi. |

### 3.4 Sağlayıcı seçimi

| Model | Sağlayıcı | Neden |
|---|---|---|
| Qwen 3.7 serisi | Alibaba | Tek sağlayıcı (modelin geliştiricisi); uptime %100; seed destekli |
| Mistral serisi | Mistral | Tek sağlayıcı (modelin geliştiricisi); uptime %100; seed destekli |

Her çağrıda sağlayıcı şu ayarlarla sabitlendi (`ayarlar.py → extra_body`):

```python
"provider": {"order": ["<sağlayıcı>"], "allow_fallbacks": False, "require_parameters": True}
```

`require_parameters`, gönderilen temperature / top_p değerlerini uygulamayan bir sağlayıcıya isteğin düşmesini engeller. Deneydeki 2.400 cevabın tamamında cevabı beklenen sağlayıcının verdiği kaydedildi (`Ham Veri → saglayici`).

> ✍️ Bu bölüm birlikte yürütülen seçim sürecinin kaydıdır; kendi ifadelerinle düzenle.

---

## 4. Deney Düzeni

```
dataset.xlsx ──► topla.py ──► ham_cevaplar.csv ──► hakem.py ──► hakem_puanlari.csv ──► sonuclar.xlsx
                (6 model × 4 ayar)                 (gpt-4.1-mini, T=0)
```

| Sabit tutulan | Değer |
|---|---|
| Sistem prompt'u (tüm modeller) | "Soruları kısa ve net cevapla. Açıklama yapma." |
| `max_tokens` | 300 |
| Düşünme | Kapalı (özelliği olan modellerde `reasoning.enabled = false`) |
| Sağlayıcı | Model başına sabit, yedeğe geçiş kapalı |
| Hakem ve hakem prompt'u | Tüm cevaplar için aynı |

**Değişken (deney ayarları):**

| Ayar | temperature | top_p | Amaç |
|---|---|---|---|
| T=0 | 0.0 | 1.0 | Referans (en olası token) |
| T=0.7 | 0.7 | 1.0 | Orta rastgelelik |
| T=1 | 1.0 | 1.0 | Yüksek rastgelelik |
| T=1 p=0.5 | 1.0 | 0.5 | T sabitken top_p'nin etkisi |

100 soru × 6 model × 4 ayar × 1 tekrar = **2.400 cevap**.

**Hata yönetimi ve dayanıklılık:**
- Geçici hatalar (429, 5xx, timeout, boş cevap): 2 → 4 → 8 saniye bekleyerek en fazla 4 deneme (üstel geri çekilme).
- Kalıcı hatalar (400/403/404): tekrar denenmez, hata kaydedilir. 401 (geçersiz anahtar) ve 402 (kredi bitti) tüm çalışmayı durdurur.
- Her çağrıdan sonra CSV'ye yazılır (checkpoint). Yarıda kesilen çalışma aynı komutla devam eder; başarılı satırlar atlanır, hatalılar yeniden denenir.
- 8 eşzamanlı çağrı; 6 modelin istekleri karışık dağıtılır.
- **Yaşanan olay:** Tam deneyde Mistral sunucusu `mistral-large-2512` için 16 çağrıda 4 denemenin sonunda da **429 (çok fazla istek)** döndürdü. Betik bu satırları hatalı olarak kaydetti; ikinci çalıştırmada 16'sı da başarıyla alındı. Sonuçta kalıcı hata yok.
- Bir cevap (`ministral-8b`, soru #28, T=0.7) `max_tokens` sınırında kesildi (`finish_reason = length`).

---

## 5. Hakem Model (LLM-as-a-Judge)

### 5.1 Hakem seçimi

Hakem, test edilen ailelerin (Qwen, Mistral) **dışından** seçildi; böylece kendi ailesini kayırma riski ortadan kalktı. 9 aday, doğru puanı önceden bilinen **15 tuzaklı vaka** ile ikişer kez test edildi (`araclar/hakem_karsilastirma.py`). Vakalar: anahtar kelime içeren ama yanlış cevap, kararsız cevap ("A ya da B"), farklı dil, sayı yuvarlama, 4 parçadan 2–3'ü doğru liste, doğru cevap + yanlış ek bilgi, uzunluk tuzağı, hakemin kendi bilgisi yerine referansı kullanmasını sınayan vaka.

| Aday | İsabet /30 | Tutarlılık /15 | JSON hatası | 2.700 çağrı tahmini $ | Süre |
|---|---|---|---|---|---|
| **openai/gpt-4.1-mini** | **30** | **15** | 0 | **0.51** | 1.5 s |
| google/gemini-2.5-flash | 30 | 15 | 0 | 0.56 | 1.1 s |
| anthropic/claude-haiku-4.5 | 30 | 15 | 0 | 2.42 | 1.9 s |
| deepseek/deepseek-v4-pro | 30 | 14 | 0 | 2.44 | 4.7 s |
| google/gemini-3.8-flash | 30 | 14 | 0 | 2.54 | 2.8 s |
| anthropic/claude-sonnet-4.6 | 30 | 13 | 0 | 6.22 | 2.4 s |
| x-ai/grok-4.7 | 30 | 15 | 0 | 12.71 | 3.6 s |
| z-ai/glm-5.2 | 29 | 13 | 1 | 1.38 | 2.3 s |
| openai/gpt-4.1 | 28 | 14 | 0 | 2.56 | 1.5 s |

**Seçilen: `openai/gpt-4.1-mini`** — tam isabet, tam tutarlılık, en düşük maliyet. Düşünme özelliği olmadığı için temperature = 0 doğrudan uygulanır ve gizli düşünme tokeni maliyeti oluşmaz. Sağlayıcı OpenAI'ye sabitlendi.

Not: Testte neredeyse tüm adaylar tam isabet aldı (tavan etkisi), bu yüzden ayırt edici ölçütler tutarlılık, maliyet ve hız oldu. Dikkat çekici bir sonuç: büyük model `gpt-4.1`, "Yaklaşık 8.000 metre" cevabına (referans 8.849 m) 50 puan vererek mini sürümünden daha düşük isabet aldı.

### 5.2 Hakem prompt'u ve puan cetveli

Prompt `ayarlar.py → HAKEM_PROMPT` içindedir. Özeti:
- Yalnızca **referans cevaba** göre değerlendir; kendi bilgin referansla çelişse bile referansı doğru kabul et.
- Uzunluk, dil ve üslup puanı etkilemez; sayılarda makul yuvarlama doğru sayılır.
- **100** = anlamca tam örtüşme · **50–90** = çok parçalı cevapta doğru parça oranına göre · doğru kısmın yanında yanlış ek bilgi varsa puan düşer · **0** = yanlış, çelişkili, kararsız veya cevap yok.
- Çıktı: `{"skor": <0-100>, "gerekce": "<1 cümle>"}` (`response_format = json_object`). Ayrıştırma hatasında yeniden denenir; skor asla tahmin edilmez.

### 5.3 Hakemin puan dağılımı

| Skor | 0 | 33 | 50 | 67 | 75 | 80 | 88 | 90 | 100 |
|---|---|---|---|---|---|---|---|---|---|
| Cevap sayısı | 118 | 2 | 3 | 2 | 2 | 1 | 5 | 15 | 2.252 |

2.400 puandan yalnızca 30'u kısmi (0 < skor < 100); hakem pratikte büyük ölçüde doğru/yanlış kararı verdi. JSON hatası: 0.

### 5.4 Hakem davranışına dair gözlemler

- **Parantez içi ek bilginin eksik sayılması:** Referans "Mariana Çukuru (Challenger Derinliği)" iken yalnızca "Mariana Çukuru" diyen cevaplara 100 yerine **90** verildi. Parantez içi açıklama zorunlu bir parça gibi ele alındı.
- **Yanlış ek öğelere görece hoşgörü:** Türkiye'nin kara komşuları sorusunda 8 doğru ülkenin yanına 1–2 yanlış ülke (Lübnan, Ukrayna, İsrail, KKTC) ekleyen `ministral-8b` cevapları **75–88** aldı.
- **Fazlalık metnin görmezden gelinmesi:** Bkz. §8.4 — doğru cevabın ardından alakasız 250 token üreten bir cevap 90 aldı.

✍️ **Meta-değerlendirme (yapılacak):** Rastgele 20 cevap elle puanlanıp hakemin puanlarıyla karşılaştırılacak; uyum oranı buraya yazılacak.

---

## 6. Sonuçlar

### 6.1 Model × ayar — ortalama doğruluk (%)

| Model | T=0 | T=0.7 | T=1 | T=1 p=0.5 | **Ortalama** |
|---|---|---|---|---|---|
| qwen3.7-flash | 91.0 | 93.0 | 88.1 | 92.7 | **91.2** |
| qwen3.7-plus | 98.9 | 98.9 | 97.2 | 97.6 | **98.2** |
| qwen3.7-max | 99.9 | 100.0 | 99.9 | 99.9 | **99.9** |
| ministral-8b | 82.2 | 82.7 | 80.0 | 83.3 | **82.0** |
| mistral-large | 97.9 | 97.9 | 98.0 | 98.9 | **98.2** |
| mistral-medium-3.5 | 100.0 | 99.9 | 99.0 | 98.9 | **99.4** |

### 6.2 Model genel performansı (4 ayarın tamamı, 400 cevap / model)

| Model | Doğruluk % | Tam doğru % (skor = 100) | Sıfır % | Ort. süre (s) | Ort. çıkış token | Toplam maliyet ($) | 1.000 soru başına ($) | 1.000 doğru cevap başına ($) |
|---|---|---|---|---|---|---|---|---|
| qwen3.7-flash | 91.2 | 90.5 | 8.5 | 0.91 | 6.8 | 0.00092 | 0.0023 | **0.0025** |
| qwen3.7-plus | 98.2 | 97.0 | 1.5 | 1.34 | 5.8 | 0.00898 | 0.0225 | 0.0229 |
| qwen3.7-max | **99.9** | 99.3 | 0.0 | 1.53 | 6.3 | 0.03893 | 0.0973 | 0.0974 |
| ministral-8b | 82.0 | 79.8 | 17.3 | **0.40** | 11.0 | 0.00300 | 0.0075 | 0.0091 |
| mistral-large | 98.2 | 97.5 | 1.8 | 0.77 | 8.7 | 0.01298 | 0.0325 | 0.0331 |
| mistral-medium-3.5 | 99.4 | 99.0 | 0.5 | 0.50 | 7.1 | 0.05181 | 0.1295 | 0.1303 |

### 6.3 Aile × kademe (%)

| Aile | Ucuz | Orta | Pahalı | **Aile ort.** |
|---|---|---|---|---|
| Qwen | 91.2 | 98.2 | 99.9 | **96.4** |
| Mistral | 82.0 | 98.2 | 99.4 | **93.2** |
| **Kademe ort.** | **86.6** | **98.2** | **99.7** | |

- Kademe ortalamaları arasındaki aralık: **13.1 puan** (86.6 → 99.7).
- Aile ortalamaları arasındaki fark: **3.2 puan** (93.2 – 96.4); bu farkın tamamına yakını ucuz kademeden geliyor (orta ve pahalıda aileler 98.2 / 99.4–99.9 ile neredeyse eşit).

✍️ Yorum: aile mi, kademe mi daha belirleyici?

### 6.4 Zorluğa göre (%)

| Model | Kolay (29) | Orta (52) | Zor (19) |
|---|---|---|---|
| qwen3.7-flash | 98.3 | 91.8 | 78.8 |
| qwen3.7-plus | 100.0 | 98.4 | 94.7 |
| qwen3.7-max | 100.0 | 99.9 | 100.0 |
| ministral-8b | 90.5 | 82.7 | 67.2 |
| mistral-large | 100.0 | 98.4 | 94.7 |
| mistral-medium-3.5 | 99.1 | 99.5 | 99.8 |

### 6.5 Kategoriye göre (%)

| Model | Bilim | Coğrafya | Edebiyat-Sanat | Genel Kültür | Spor | Tarih |
|---|---|---|---|---|---|---|
| qwen3.7-flash | 94.4 | 93.9 | **82.4** | 93.3 | 86.5 | 95.8 |
| qwen3.7-plus | 100.0 | 97.7 | 96.1 | 100.0 | 94.8 | 100.0 |
| qwen3.7-max | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 100.0 |
| ministral-8b | 92.4 | 88.7 | **67.2** | 87.7 | **71.7** | 83.3 |
| mistral-large | 100.0 | 99.9 | 100.0 | 93.3 | 94.7 | 100.0 |
| mistral-medium-3.5 | 98.6 | 99.8 | 98.5 | 100.0 | 99.8 | 100.0 |

### 6.6 Soru türüne göre (%)

| Model | Sayısal/Tarih | Tek cevap | Çok parçalı |
|---|---|---|---|
| qwen3.7-flash | 93.5 | 87.2 | 96.2 |
| qwen3.7-plus | 99.9 | 96.4 | 98.1 |
| qwen3.7-max | 99.8 | 100.0 | 100.0 |
| ministral-8b | 81.2 | 80.2 | 90.1 |
| mistral-large | 97.6 | 98.2 | 100.0 |
| mistral-medium-3.5 | 99.9 | 98.8 | 99.8 |

### 6.7 En zor 10 soru (tüm model ve ayarların ortalaması)

| # | Soru | Ana Cevap | Ort. % | Yanlış yapan (4 ayardan kaçında) |
|---|---|---|---|---|
| 100 | Ankara hangi tarihte başkent ilan edildi? | 13 Ekim 1923 | 54 | ministral-8b 4, mistral-large 4, qwen-flash 4 |
| 60 | 'Saatleri Ayarlama Enstitüsü'nün yazarı | Ahmet Hamdi Tanpınar | 58 | ministral-8b 4, qwen-flash 4, qwen-plus 2 |
| 49 | Türkiye'nin ilk kadın savaş pilotu | Sabiha Gökçen | 62 | ministral-8b 4, qwen-flash 4, mistral-medium 1 |
| 66 | 'Tutunamayanlar'ın yazarı | Oğuz Atay | 67 | ministral-8b 4, qwen-flash 4 |
| 83 | Hakan Şükür'ün Güney Kore golü kaçıncı saniye | 11. saniye | 67 | ministral-8b 4, qwen-flash 4 |
| 85 | Hidayet Türkoğlu'nun MIP ödülü aldığı takım | Orlando Magic | 67 | qwen-flash 4, qwen-plus 3, ministral-8b 1 |
| 28 | Yüzölçümü en büyük il | Konya | 71 | ministral-8b 4, qwen-flash 3 |
| 76 | Türkiye 2002 Dünya Kupası sıralaması | Üçüncü | 71 | ministral-8b 4, mistral-large 3 |
| 57 | 'Kürk Mantolu Madonna'nın yazarı | Sabahattin Ali | 75 | ministral-8b 4, qwen-flash 1, mistral-medium 1 |
| 15 | Amasya Genelgesi tarihi | 22 Haziran 1919 | 75 | ministral-8b 4, qwen-flash 2 |

Hiçbir soruda 6 modelin 3'ü veya fazlası T=0'da birlikte yanlış (skor < 50) yapmadı. Zorlanılan soruların çoğu **Türkiye'ye özgü** edebiyat, spor ve tarih bilgisi.

### 6.8 Farkların istatistiksel anlamlılığı (T=0, eşleştirilmiş bootstrap, 5.000 örnek, %95 güven aralığı)

Tüm modeller aynı 100 soruyu cevapladığı için farklar soru bazında eşleştirilerek hesaplandı. **\*** = güven aralığı 0'ı içermiyor (fark anlamlı).

| Karşılaştırma | Fark (puan) | %95 GA | |
|---|---|---|---|
| qwen-flash − qwen-plus | −7.9 | [−13.9, −2.9] | \* |
| qwen-flash − qwen-max | −8.9 | [−15.0, −3.8] | \* |
| qwen-flash − ministral-8b | +8.8 | [2.8, 15.3] | \* |
| qwen-flash − mistral-large | −6.9 | [−12.8, −1.8] | \* |
| qwen-flash − mistral-medium | −9.0 | [−15.0, −4.0] | \* |
| qwen-plus − qwen-max | −1.0 | [−3.2, 0.2] | |
| qwen-plus − ministral-8b | +16.8 | [9.5, 24.6] | \* |
| qwen-plus − mistral-large | +1.0 | [−2.1, 4.7] | |
| qwen-plus − mistral-medium | −1.1 | [−3.2, 0.0] | |
| qwen-max − ministral-8b | +17.8 | [10.8, 25.5] | \* |
| qwen-max − mistral-large | +2.0 | [0.0, 5.0] | |
| qwen-max − mistral-medium | −0.1 | [−0.3, 0.0] | |
| ministral-8b − mistral-large | −15.8 | [−23.1, −8.8] | \* |
| ministral-8b − mistral-medium | −17.9 | [−25.6, −10.6] | \* |
| mistral-large − mistral-medium | −2.1 | [−5.1, 0.0] | |

Anlamlı farkların hepsi **ucuz kademedeki iki modeli** içeriyor. Orta ve pahalı kademedeki 4 model arasındaki farklar bu veri setiyle ayırt edilemiyor.

✍️ Yorum ve model kararı: §10.

---

## 7. temperature / top_p Analizi — Veriler

### 7.1 Doğruluğa etkisi (T=0'a göre fark, puan)

| Model | T=0 (referans) | T=0.7 | T=1 | T=1 p=0.5 |
|---|---|---|---|---|
| qwen3.7-flash | 91.0 | +2.0 | −2.9 | +1.7 |
| qwen3.7-plus | 98.9 | 0.0 | −1.7 | −1.3 |
| qwen3.7-max | 99.9 | +0.1 | 0.0 | 0.0 |
| ministral-8b | 82.2 | +0.5 | −2.2 | +1.1 |
| mistral-large | 97.9 | 0.0 | +0.1 | +1.0 |
| mistral-medium-3.5 | 100.0 | −0.1 | −1.0 | −1.1 |

### 7.2 Cevap kararlılığı: T=0'daki cevaba göre değişen soru sayısı (100 soruda)

"Metin" = cevabın yazımı değişti; "skor" = hakemin puanı değişti (doğruluk etkilendi).

| Model | T=0.7 metin / skor | T=1 metin / skor | T=1 p=0.5 metin / skor |
|---|---|---|---|
| qwen3.7-flash | 21 / 2 | **38 / 8** | 14 / 2 |
| qwen3.7-plus | 5 / 2 | 12 / 6 | 3 / 2 |
| qwen3.7-max | 5 / 1 | 11 / 0 | 3 / 0 |
| ministral-8b | 26 / 7 | **33 / 8** | 11 / 2 |
| mistral-large | 13 / 2 | 10 / 1 | 5 / 1 |
| mistral-medium-3.5 | 32 / 1 | 31 / 1 | 5 / 2 |

### 7.3 top_p'nin etkisi (T = 1 sabitken top_p = 1.0 → 0.5)

| Model | Doğruluk T=1 → T=1 p=0.5 | Metni değişen soru (T=0'a göre) T=1 → T=1 p=0.5 |
|---|---|---|
| qwen3.7-flash | 88.1 → 92.7 | 38 → 14 |
| qwen3.7-plus | 97.2 → 97.6 | 12 → 3 |
| qwen3.7-max | 99.9 → 99.9 | 11 → 3 |
| ministral-8b | 80.0 → 83.3 | 33 → 11 |
| mistral-large | 98.0 → 98.9 | 10 → 5 |
| mistral-medium-3.5 | 99.0 → 98.9 | 31 → 5 |

### 7.4 T=1'de doğru cevabın yanlışa döndüğü örnekler

| Model | Soru | T=0 cevabı (puan) | T=1 cevabı (puan) |
|---|---|---|---|
| ministral-8b | #17 Preveze: yıl ve komutan | 1538, Barbaros Hayreddin Paşa (100) | 1687, Koca Mustafa Paşa (0) |
| ministral-8b | #42 Yetişkin iskeletindeki kemik sayısı | 206 kemik (100) | 306–310 adet (0) |
| ministral-8b | #52 Aziz Sancar: dal ve yıl | Kimya, 2015 (100) | Kimya, 2009 (50) |
| ministral-8b | #63 'Çalıkuşu'nun yazarı | Reşat Nuri Güntekin (100) | Mehmet Rauf (0) |
| mistral-medium-3.5 | #57 'Kürk Mantolu Madonna'nın yazarı | Sabahattin Ali (100) | Sabatay Sevi (0) |
| qwen3.7-flash | #10 Sakarya Meydan Muharebesi yılı | 1921 (100) | 1949 (0) |
| qwen3.7-flash | #20 Türkiye'nin en büyük gölü | Van Gölü (100) | Tuz Gölü (0) |

### 7.5 Yorum

✍️ Yapılacak. Bakılabilecek sorular:
- temperature arttıkça doğruluk ve kararlılık nasıl değişti? Etki hangi modellerde büyük, hangilerinde ihmal edilebilir?
- Model büyüklüğü/kademesi ile temperature hassasiyeti arasında bir ilişki var mı?
- top_p = 0.5, T = 1'in etkisini nasıl değiştirdi? (Tanım gereği top_p düşük olasılıklı tokenleri eler.)
- Cevap metninin değişmesi ile doğruluğun değişmesi arasındaki fark ne söylüyor?
- Bu tür bilgi soruları için hangi ayar uygun?

Sınırlılık: Her ayar tek tekrarla çalıştırıldı; T > 0'daki farklar kısmen şans eseri olabilir (100 soruda 1 puan ≈ 1 soru). Kararlılığı daha güvenilir ölçmek için `ayarlar.py → TEKRAR = 3` ile yeniden çalıştırılabilir.

---

## 8. Ek Bulgular (ön testler)

### 8.1 Düşünme modu

- OpenRouter'da 155 model, düşünme kapatma isteğiyle (`reasoning.enabled = false`) test edildi (`veri/dusunme_testi.txt`).
- Google'ın 24 metin modelinden 13'ünde düşünme kapatılamıyor (Gemini 4 serisinin tamamı, Gemini 3.5–3.8 Flash, tüm Pro modelleri).
- Düşünme özelliği **olmayan** bir modele (ör. `ministral-8b`, `mistral-large`) düşünme parametresi gönderilince `require_parameters` ayarı nedeniyle istek hiçbir sağlayıcıya ulaşamıyor ve `404 No endpoints found` hatası dönüyor. Bu yüzden parametre yalnızca düşünme özelliği olan modellere gönderildi.

### 8.2 seed parametresi

Sağlayıcılar `seed` parametresini kabul ediyor, ancak aynı seed ile aynı çıktıyı garanti etmiyor. T = 1.0'da aynı seed (42) ile 3 çağrı yapıldı (`araclar/seed_testi.py`):

| Model | Aynı seed ile 3 çağrıda farklı cevap sayısı |
|---|---|
| qwen3.7-flash / plus / max | 3 / 3 / 3 (etkisiz) |
| ministral-8b | 2 |
| mistral-large | 2 |
| mistral-medium-3.5 | 1 (3 çağrıda tutarlı) |

Kontrol grubunda (farklı seed'ler 1, 2, 3) bütün modeller 3 farklı cevap verdi; yani modeller gerçekten dalgalanıyordu. Sonuç: OpenRouter üzerinden T > 0'da birebir tekrarlanabilirlik sağlanamıyor; deneyde seed kullanılmadı. (Not: test çağrıları eşzamanlı gönderildi; sağlayıcı tarafında aynı GPU grubunda işlenmeleri sonucu etkilemiş olabilir.)

### 8.3 "bf16" etiketi ve modellerin orijinal formatı (Kimi ailesi)

Hugging Face'teki resmi model kartlarına göre:

| Model | Orijinal ağırlık formatı |
|---|---|
| Kimi K2 | fp8 (block-fp8), 1T toplam / 32B aktif parametre |
| Kimi K2.6 | **INT4** ("native INT4", 4 bite uyarlanmış eğitim), 1T / 32B |
| Kimi K3.1 Pro | **MXFP4** ağırlık / MXFP8 aktivasyon (quantization-aware training), ~2.8T |

Bazı sağlayıcıların K2.6 ve K3.1 Pro için sunduğu "bf16" seçeneği, orijinali zaten 4 bit olan ağırlıkları 16 bitte saklamak anlamına geliyor; kalite avantajı sağlamıyor. Bulgu: quantization etiketi tek başına kalite göstergesi değildir, modelin orijinal formatına bakmak gerekir.

### 8.4 Model davranışına dair gözlemler

- **Bitiş dizisinin kaçırılması:** `mistral-large` (soru #32, T = 0.7), doğru cevabı verdikten sonra durmadı; `+++++ questions/1693371377405.md` başlıklı, eğitim verisinden kalma gibi görünen ilgisiz bir soru-cevap listesi üretti (262 çıkış tokeni; aynı sorunun diğer ayarlarında 14 token). Hakem bu cevaba 90 verdi.
- **Yüksek temperature'da dil bozulması:** Ön testte `mistral-medium-3.5`, T = 1.0'da "Türk portugiesi devleti" gibi yabancı kelimeler ve cümle içinde Ermeni harfi üretti.
- **Biçim farkı:** `ministral-8b` cevaplarının %14'ünde Markdown biçimlendirmesi (`**Yıl:** 1538`) kullandı; diğer modellerde bu oran %0–1. Sistem prompt'u "kısa ve net" olmasına rağmen ortalama çıkışı en uzun model (11 token) oldu.
- **Uzun cevap:** Qwen modelleri genellikle tek kelime/sayı ile, Kimi modelleri (ön testte) tam cümleyle cevap verdi.

---

## 9. Sınırlılıklar

- **Veri seti doğrulanmadı.** Deney taslak veri setiyle yapıldı. Bir Ana Cevap düzeltilirse cevaplar geçerliliğini korur; yalnızca `sonuclar/hakem_puanlari.csv` silinip `hakem.py` yeniden çalıştırılmalıdır (~$0.47). Soru metni değişirse o soru için `topla.py` da yeniden çalıştırılmalıdır.
- **Tavan etkisi.** Orta ve pahalı kademedeki 4 model %98–100 aldı; aralarındaki farklar bu veri setiyle anlamlı değil (§6.8). Ayırt etmek için daha zor sorular gerekir.
- **Tek tekrar.** T > 0 ayarlarında her soru bir kez soruldu; kararlılık ölçümü T=0 cevabıyla karşılaştırmaya dayanıyor.
- **Tek hakem.** Puanlar tek bir hakem modele bağlı; §5.4'teki eğilimler (parantez içi bilgiyi zorunlu sayma, yanlış ek öğelere hoşgörü) bazı puanları etkilemiş olabilir. Elle meta-değerlendirme henüz yapılmadı.
- **Türkçe.** Sorular Türkçe ve önemli kısmı Türkiye'ye özgü; sonuçlar İngilizce veya genel bilgi sorularına doğrudan genellenemez.
- **Sağlayıcı bilgisi.** Alibaba ve Mistral quantization formatını açıklamıyor ("unknown").

---

## 10. Karar ve Öneri

✍️ Yapılacak. Bakılabilecek sorular:
- Bu proje için hangi model + ayar uygun? Doğruluk mu, maliyet mi, hız mı öncelikli?
- §6.2'deki "1.000 doğru cevap başına maliyet" ve §6.8'deki anlamlılık sonuçları bu kararı nasıl destekliyor?
- Hangi koşulda karar değişir (ör. bütçe 10 kat artarsa, cevap süresi kritikse, sorular İngilizce olursa)?

---

## Ek A — Dosyalar ve tekrar üretim

| Dosya | İçerik |
|---|---|
| `ayarlar.py` | Modeller, sağlayıcılar, deney ayarları, hakem ve hakem prompt'u (tek ayar dosyası) |
| `topla.py` | Adım 3: cevap toplama (checkpoint, yeniden deneme) |
| `hakem.py` | Adım 4: hakem puanlaması ve `sonuclar.xlsx` |
| `veri/dataset_taslak.xlsx` | 100 soru (doğrulama sonrası `dataset.xlsx`) |
| `sonuclar/ham_cevaplar.csv` · `hakem_puanlari.csv` · `sonuclar.xlsx` | Ham ve işlenmiş sonuçlar |
| `araclar/hakem_karsilastirma.py` | Hakem seçim testi (§5.1) |
| `araclar/seed_testi.py` | seed testi (§8.2) |
| `araclar/model_katalogu.py` | OpenRouter model ve sağlayıcı kataloğu |
| `veri/dusunme_testi.txt` | Düşünme kapatma testi sonuçları (§8.1) |

Tekrar üretmek için:
```
.venv\Scripts\python topla.py
.venv\Scripts\python hakem.py
```
veya Docker ile: `docker compose up --build`
