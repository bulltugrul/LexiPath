# LexiPath — Data Mining Midterm Projesi

Açıklanabilir İngilizce kelime öğretimi: **Denetimli cevap tahmini (LR12)**, **Denetimsiz performans örüntüsü (K-Means, k=4)** ve **hedefe özgü öğretim döngüsü**.



---

## 1. Sunum Bilgisayarında Hızlı Kurulum ve Çalıştırma (Windows)

Projeyi klonladıktan sonra sunum yapılacak bilgisayarda:

1. **`Kurulum.cmd`** dosyasına çift tıklayın (veya terminalde çalıştırın).
   - Otomatik olarak `.venv` sanal ortamını oluşturur ve `requirements-lock.txt` bağımlılıklarını kurar.
2. **`Baslat.cmd`** dosyasına çift tıklayın.
   - Arka planda yerel sunucuyu başlatır ve tarayıcıda `http://127.0.0.1:8765` adresini açar.
   - **48 kelimelik ana uygulama:** `http://127.0.0.1:8765/`
   - **4 kelimelik öğretim döngüsü pilotu:** `http://127.0.0.1:8765/pilot`

### Sunumda Hazır "Ayşe" Sentetik Örneğini Açmak İçin
Sunum sırasında sıfırdan 16+16 soru çözmekle vakit kaybetmemek için, rapordaki **Grup 3** atamasını ve öğretim ekranlarını içeren sentetik öğrenciyi doğrudan ana veritabanına şu komutla ekleyebilirsiniz:

```powershell
.\.venv\Scripts\python.exe src\demo_scenario.py --db data\prototype\PROTOTYPE_students.sqlite3
```
Komutun çıktısında verilen `/pilot?run=...` adresini `http://127.0.0.1:8765/pilot?run=...` olarak açtığınızda doğrudan **8 metin + 8 dinleyerek yazma kaydı tamamlanmış, Grup 3 atanmış ve çalışma önerisi üretilmiş** ekran gelir.

### Testleri Çalıştırmak İçin
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s src -p "test_*.py"
```
*(56 birim ve entegrasyon testinin tamamı ~3 saniyede geçer.)*

---

## 2. Ekip İçin Sunuma Hazırlık ve Okuma Sırası (27 Kasım, 14:40 — B-Yunus Emre)

Sunumda her grup üyesi projenin tamamından sorumludur. Lütfen şu sırayla inceleyin:

1. **[team_notes/SUNUM_PROVASI.txt](team_notes/SUNUM_PROVASI.txt)** — 7 dakikalık anlatım akışı, hocanın sorabileceği soruların net cevapları ve canlı kod değişikliği noktaları.
2. **[team_notes/DIYAGRAM_SAVUNMASI.txt](team_notes/DIYAGRAM_SAVUNMASI.txt)** — 1 dakikada ML blok diyagramı savunması (neden LR denetimli, neden K-Means denetimsiz) ve beklenen 3 kritik soru.
3. **[output/pdf/LexiPath_Midterm_Raporu.pdf](output/pdf/LexiPath_Midterm_Raporu.pdf)** (Türkçe, 33 sayfa) ve **[output/pdf/LexiPath_Midterm_Report_EN.pdf](output/pdf/LexiPath_Midterm_Report_EN.pdf)** (İngilizce, 33 sayfa).
4. **[notebooks/LexiPath_Experiments.ipynb](notebooks/LexiPath_Experiments.ipynb)** — Çalıştırılmış 7 hücreli deney ve grafik üretim defteri (VS Code veya Jupyter ile açılabilir).

---

## 3. Sunumda İstenebilecek Canlı Kod Değişiklikleri (Hızlı Harita)

| İstenebilecek Değişiklik | Dosya ve Satır / Konum | Açıklama |
|---|---|---|
| **Pilot bekleme süresini (24 saat) kısaltma** | `src/pilot.py` → `DELAY_SECONDS = 24*60*60` (satır 14) | Örneğin `10` (10 saniye) yapılırsa gecikmeli kontrol 10 sn sonra canlıda açılır. |
| **Destekli denemedeki hata açıklamasını değiştirme** | `src/pilot.py` → `support_explanation()` | Yazma, tanıma ve dinleme için üretilen geri bildirim metinleri. |
| **Çalışma önerisi (`pattern_guidance`) metnini veya kuralını değiştirme** | `src/learning_evidence.py` → `pattern_guidance()` | Son 6 metin ve 6 dinleme oranına göre öneri üreten fonksiyon. |
| **Ana uygulamada tur soru dağılımı (3 metin + 3 dinleme veya 4 tekrar + 2 yeni)** | `src/tutor_engine.py` → `prepare_question()` (satır 167–168) | `mode = TEXT if position % 2 == 0 else LISTEN` ve `requested = ['review', 'review', 'new', ...]` |
| **K-Means profil penceresi eşiği (`WINDOW = 6`)** | `src/profiles.py` → `WINDOW = 6` (satır 7) | Not: Tam küme merkezlerini yeniden eğitmek gerekirse `prepare_profiles.py` ardından `train_kmeans.py` çalıştırılır. |
