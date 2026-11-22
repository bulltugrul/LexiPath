"""Son ürünü, kod parçalarını ve kayıtlı deneyleri açıklayan teslim PDF'si."""
from pathlib import Path
import json,ast,textwrap,html
from PIL import Image as PILImage,ImageDraw,ImageFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/pdf';ASSETS=ROOT/'outputs/report_assets'
OUT.mkdir(parents=True,exist_ok=True);ASSETS.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial','C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB','C:/Windows/Fonts/arialbd.ttf'))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyTR',fontName='Arial',fontSize=10.2,leading=15,spaceAfter=9,textColor=colors.HexColor('#203B4D')))
styles.add(ParagraphStyle(name='TitleTR',fontName='ArialB',fontSize=24,leading=30,spaceAfter=20,textColor=colors.HexColor('#087E86')))
styles.add(ParagraphStyle(name='HeadTR',fontName='ArialB',fontSize=16,leading=21,spaceAfter=14,textColor=colors.HexColor('#17394A')))
styles.add(ParagraphStyle(name='SmallTR',fontName='Arial',fontSize=8.2,leading=12,spaceAfter=6,textColor=colors.HexColor('#486070')))
story=[];sections=[]
def p(s,style='BodyTR'):story.append(Paragraph(html.escape(s).replace('\n','<br/>'),styles[style]))
def head(title):
 if story:story.append(PageBreak())
 sections.append(title);p(title,'HeadTR')
def image(path,maxh=390):
 path=ROOT/path
 im=PILImage.open(path);w,h=im.size;scale=min(505/w,maxh/h)
 story.append(Image(str(path),width=w*scale,height=h*scale));story.append(Spacer(1,10))
def table(rows,widths=None):
 body=[[Paragraph(html.escape(str(v)).replace('\n','<br/>'),styles['SmallTR']) for v in row] for row in rows]
 t=Table(body,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7F2F3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#087E86')),('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#D7E2E8')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t);story.append(Spacer(1,12))
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
members=[('Eren Hasan Katırcıoğlu','240201037'),('Mehmet Ertuğrul Ünal','240201010'),('Hasan Yunus Zengin','240201038'),('Ömer Gökalp','240201053'),('Mustafa Kemal Bozkurt','240201018')]
story.append(Spacer(1,35));p('LEXIPATH','TitleTR');p('Data Mining - Midterm Projesi','HeadTR')
p('Açıklanabilir İngilizce kelime öğretimi: denetimli cevap tahmini, denetimsiz performans örüntüsü ve hedefe özgü öğretim döngüsü.')
story.append(Spacer(1,25));table([['Grup üyesi','Öğrenci numarası']]+members,[340,160])
p('Üsküdar University | 22 Kasım 2026')
p('Teslim kapsamı: Python uygulaması, 48 kelimelik alıştırma ortamı, dört kelimelik öğretim pilotu, eğitilmiş LR12 ve K-Means, açıklamalı deney çıktıları ve çalıştırma paketi.')
p('Rapor ekranlarındaki Ayşe sentetik gösterim öğrencisidir. Gerçek 24 saatlik hatırlama sonucu beklenmektedir; senaryo ve testler gerçek öğrenme kazanımı deneyi olarak sunulmamıştır.','SmallTR')
head('1. Problem, kapsam ve gereksinim karşılıkları')
p('Amaç, öğrencinin yalnız doğru/yanlış sayısını göstermek değil; hangi kelime-hedefte desteğe ihtiyaç duyulduğunu belirlemek, ilgili desteği sunmak ve yardımsız kontrolle sonucu izlemektir. Karmaşıklığı sınırlamak için iki öğrenen model kullanılır; diğer mekanizmalar açık kurallarla yürütülür.')
table([['Beklenen işlev','Uygulamadaki karşılık'],['Gereksinim ve ayrıntılı senaryo','Bu bölüm ve Bölüm 2; ana alıştırma ile pilotun amaçları ayrıdır.'],['Her ML kutusunun görevi ve veri şeması','LR12: denetimli ikili tahmin; K-Means: denetimsiz iki boyutlu kümeleme. Bölüm 3-5.'],['Metin, ses ve görsel etkileşim','Yazma, dinleyerek yazma, yazı-resim/ses-resim, görsel öğretim ve konu kartları.'],['Konu başarısı ve zaman takibi','Konu/biçim/aşama doğru-toplam, kelime/tur sayıları; pilotta geçerli hedef kanıtı ve zamanlar.'],['Öğrenme örüntüsünün öğretime yardımı','Kaynak grup merkezi ve bireysel oranların gerekçeli çalışma önerisi; yorum kuralı ayrı.'],['Python, kod ve çıktı açıklaması','Bölüm 11-14 ve açıklamalı kod görselleri; tam kaynak ZIP içinde.'],['Tek arşiv ve grup bilgileri','Beş üye kapakta; kod, rapor, modeller, varlıklar ve kurulum yönergesi ZIP içinde.']],[190,310])
p('48 kelimelik ana uygulama konu tercihi, model destekli soru seçimi ve görsel tekrar sunar. Dört kelimelik pilot, ihtiyaçtan öğretime ve sonraki kontrole uzanan daha ayrıntılı kanıt döngüsünü gösterir. İki modül aynı projede farklı amaçlara hizmet eder: geniş havuzda alıştırma ve küçük kapsamda ayrıntılı öğretim. Her modül kendi öğrenci geçmişini tutar.')
head('2. Ayrıntılı öğrenci senaryosu: Ayşe')
steps=[('Başlangıç','Ayşe ana uygulamada hayvan, yiyecek ve günlük yaşam kartlarını seçer. Bu kartlarla öğrencinin içerik tercihleri alınır. Pilotun kapsamı cat, dog, apple, book olarak sabittir.'),('Ölçüm','Pilot 4 yardımsız yazma, 4 ortak dinleyerek yazma, 4 yazı-resim ve 4 ses-resim görevi sorar. Yazma önce gelir. Doğru cevap ve model olasılığı açıklanmaz.'),('İhtiyaç','Ayşe cat için ca yazar ve cat ses-resim eşleştirmesinde yanılır. Yazma ve ses-resim ihtiyaçları ayrı kaydedilir. Birden fazla yazma adayı varsa LR düşük doğru tahminiyle sıralar.'),('Öğretim','Yazmada kelime, resim, anlam, ses ve c+a+t örneği gösterilir. Destekli ca yanıtında eksik t açıklanır, aynı hedef yeniden denenir. İkinci destekli yanlış yalnız o hedefi duraklatır.'),('Kontrol','Doğru destekli cevap bağımsız başarı sayılmaz. Diğer kelimelerle aralık sonrası ipuçları kaldırılır. Ses-resim ve yazma farklı hedefler olarak tekrar ölçülür.'),('Ortak model verisi','Yardımsız kontrol sonundaki dört dinleyerek yazma yanıtı ayrı ortak kayıttır. Metin ve dinleyerek yazma gerçek sonuçları iki modelin geçmişini günceller.'),('Örüntü ve öneri','Gösterimde son altı metin 6/6, dinleyerek yazma 3/6 olur. Model Grup 3 atar; oran farkı nedeniyle ek dinleyerek yazma çalışması önerilir.'),('Gecikmeli kanıt','Son kontrol bloğundan 24 saat sonra hedeflerin gecikmeli kontrolü açılır. Aynı oturumdaki başarıdan kalıcı öğrenme sonucu çıkarılmaz. Yeniden öğretim yalnız ilgili hedefin sürümünü yeniler.')]
for a,b in steps:p(a+': '+b)
head('3. ML görevlerinin blok diyagramı')
image(Path('outputs/diagrams/ml_blok_diyagrami.png'),430)
p('Şekil 1. Yalnız iki kutu öğrenen görevlere karşılık gelir. Solda girdilerin, sağda çıktıların kısa özeti vardır; ayrıntılı veri alanları Bölüm 5-6 tablolarındadır. Cevap doğrulama, öğretim, zaman ve öneri açıklaması uygulama kurallarıdır; üçüncü bir öğrenen model gibi çizilmemiştir.')
table([['Eğitimdeki fark','LR - denetimli','K-Means - denetimsiz'],['Verilen veri','x: geçmiş özellikleri; y: o hedefin 0/1 sonucu','X: geçmişten çıkarılmış iki oran'],['Öğrenme amacı','Bilinen y etiketine göre tahmin hatasını azaltmak','Beklenen grup etiketi olmadan yakın profilleri kümelemek'],['Yeni kayıtta çıktı','Sonraki cevabın doğru olma olasılığı','En yakın kaynak merkeze göre geçici grup']],[130,185,185])
p('Görsel bağlantı: ana ortamda LR yanlış kayıtlı kelimelerden görsel tekrar adayını seçer; pilotta gerçek kontrol hatası ilgili resimli öğretimi açar. Görsel seçim ve destekli sonuçlar ayrı tutulur, ardından uygun yardımsız yazma/dinleyerek yazma sonuçları model geçmişine girer. Metin ve ses yanıtlarıyla görsel öğretim aynı senaryoda ilişkilendirilir.')
head('4. Öğretim akışı ve kararların sahibi')
image(Path('outputs/diagrams/ogrenci_akisi.png'),410)
table([['Karar','Bilgi ve uygulama'],['Öğretim ihtiyacı','Gerçek yanlış cevap + kelime/hedef; düşük LR olasılığı tek başına teşhis değildir.'],['Öncelik','Uygun yazma adaylarının LR p_correct sırası.'],['Destekli deneme','İlk yanlış açıklamalı tekrar; ikinci yanlış yalnız hedefte duraklatma.'],['Öğrenme kanıtı','Yardımsız/gecikmeli gerçek sonuç çifti; hedef sürümü ve zamanı.']],[155,345])
head('5. Denetimli blok: LR12 girdi ve çıktısı')
fields=[('target_word','string','Hedef İngilizce sözcük'),('format','string','reverse_translate veya listen'),('prior_target_count','integer','Önceki tüm hedef sayısı'),('prior_accuracy_smoothed','float','Genel (doğru+1)/(sayı+2)'),('prior_word_count','integer','Bu kelimenin önceki hedef sayısı'),('prior_word_accuracy_smoothed','float','Kelimeye ait düzeltilmiş oran'),('prior_format_target_count','integer','Bu biçimde önceki hedef sayısı'),('prior_format_accuracy_smoothed','float','Biçime ait düzeltilmiş oran'),('prior_word_format_count','integer','Kelime ve biçimin önceki sayısı'),('prior_word_format_accuracy_smoothed','float','Kelime-biçim düzeltilmiş oran'),('prior_recent_target_count','integer','Son 10 tamamlanmış alıştırmadaki hedef sayısı'),('prior_recent_accuracy_smoothed','float','Aynı son pencerenin düzeltilmiş oranı')]
table([['Alan','Tür','Anlam']]+fields,[226,55,219])
p('Çıktı: p_correct, 0 ile 1 arasında doğru cevap tahmini. p_error=1-p_correct raporda türetilebilir. Yerel kayıtta features_before, model_version ve history_after ile cevap öncesi/sonrası izlenebilir. Öğrenci kimliği, o anki sonuç, o anki süre ve konu etiketi model özelliği değildir.')
p('OneHotEncoder kelime/biçimi, StandardScaler sayısal alanları dönüştürür; LogisticRegression sınıf 1 olasılığını üretir. Dönüşümler yalnız TRAIN ile öğrenilir. Aynı kaynak alıştırmadaki bütün kelimeler aynı cevap öncesi geçmişi kullanır; tamamı bittikten sonra geçmiş güncellenir.')
head('6. Denetimsiz blok: profil, eğitim ve çıktı')
table([['Alan','Tür / kural'],['text_target_accuracy','Son altı uygun metin hedefinde doğru sayısı / 6'],['listen_target_accuracy','Son altı gerçek dinleyerek-yazma hedefinde doğru sayısı / 6'],['Yeterlilik','İki biçimde en az altışar gözlem; eksik veri sıfır başarıya çevrilmez.'],['Ön işleme','TRAIN profillerine fit edilmiş StandardScaler'],['Çıktı','status, features, group.number, reference_center, reference_students']],[195,305])
p('Kaynak çok kelimeli alıştırmadan tek hedef, sonuca bakmadan seçilir: ilk alfabetik NOUN/PROPN; yoksa ilk alfabetik kelime. Bu kural yalnız K-Means profiline uygulanır. LR kaynak eğitiminde bütün kelime hedefleri kullanılır.')
p('K-Means öğrenciye ait beklenen grup etiketi almaz; iki oranın benzerliğinden merkezler öğrenir. Girdi oranlarının gerçek doğru/yanlışlardan hesaplanması bunu denetimli sınıflandırma yapmaz. Canlı çalışmada ağırlıklar/merkezler yeniden eğitilmez; uygun profil en yakın mevcut merkeze atanır.')
p('Öneri katmanı: bireysel metin oranı daha yüksekse dinleyerek yazmaya ek çalışma önerilir; tersi durumda metinden yazma önerilir. Oranlar eşitse fark uydurulmaz. Kaynak küme merkezi profili bağlama oturtur, bireysel önerinin yönünü öğrencinin kendi gözlemi belirler. Bu açıklama katmanı, öğrencinin kendi gözlemlerine dayalı bir çalışma önerisi sunar.')
head('7. Veri kaynağı ve yerel görevlere aktarım')
prep=load('data/prepared/slam200/preparation_report.json')
table([['Bölüm','Öğrenci','Alıştırma','Kelime hedefi']]+[[k.upper(),v['learners'],v['exercises'],v['targets']] for k,v in prep['summary'].items()],[110,100,140,150])
p('Duolingo SLAM 2018 en_es, İspanyolca bilen İngilizce öğrencilerinin kayıtlarıdır. Kaynak etiket 0=doğru, 1=hata; projede correct=1-source_error kullanılır. Aynı 200 öğrencinin resmi zaman bölümleri korunur. Bu, yeni öğrenci genelleme deneyi değildir.')
p('Yerel soru havuzu 48 kelimedir; hayvanlar 14, yiyecek/içecek 16, günlük yaşam 18. Sonradan eklenen kelimelerin TRAIN sözlüğü ve iki biçim desteği denetlenmiştir. Kaynak metin görevi çok kelimeli, yerel görev Türkçe ipuçlu tek kelimedir; kaynak listen görevini yerel tek kelime dinleyerek yazma görevine bağlamak da görev aktarımıdır.')
p('Süreler yalnız log alanıdır. Kaynak alıştırma süresi ile tek kelimelik yerel süre eşdeğer olmadığından tahmin girdisi yapılmamıştır. Yerel sesler Microsoft Zira ile hazırlanmış İngilizce WAV, resimler yerel nesne simgeleridir.')
p('Veri CC BY-NC 4.0 lisanslıdır; atıf ve lisans arşivdedir. Hazırlanmış alt küme yeniden üretim için paketlenir; ham arşiv ve erişim formunun kişisel bilgileri paketlenmez. Veri DOI: 10.7910/DVN/8SWHNO.')
head('8. LR karşılaştırmaları: basit yöntemden LR12’ye')
base=load('outputs/dev_baseline_comparison/comparison.json')['metrics'];exp=load('outputs/dev_feature_experiments/comparison.json')['metrics']
rows=[['DEV yöntemi','Log loss','AUC','Doğruluk']]
for label,m in [('Sabit TRAIN oranı',base['constant_train']),('Öğrenci geçmiş oranı',base['learner_history']),('Kelime-biçim TRAIN oranı',base['word_format_train']),('LR6',exp['original']),('LR12',exp['format_and_recent'])]:rows.append([label,f"{m['log_loss']:.4f}",f"{m['roc_auc_correct_positive']:.4f}",f"%{100*m['accuracy_at_0_5']:.2f}"])
table(rows,[230,90,90,90])
p('Log loss düşük olduğunda olasılık hatası azalır. AUC sıralama ölçüsüdür, doğruluk yüzdesi değildir. LR12 kaynak DEV’de denenmiş basit yöntemlerden daha iyi olasılık hatası vermiştir. 23.583 hedefin %81,45’i zaten doğrudur; yalnız %82,89 accuracy söylemek model katkısını abartabilir.')
p('LR12, 0,50 eşiğinde 4.375 gerçek hatanın 916’sını yakalar (%20,94), 575 doğru cevaba yanlış uyarı verir. Bu yüzden öğretime giriş p<0,5 gibi bir eşikle belirlenmez. Adayları olasılıkla sıralamak ayrı bir uygulama tercihidir; daha fazla öğrenme sağladığı henüz gösterilmemiştir.')
p('Seçim yalnız DEV ile yapılmıştır. İlk LR6 çalışmasının tarihsel TEST sonucu arşivde korunur; seçilen LR12 için yeni bir kör TEST başarı iddiası yoktur. DEV’de seçim yapılması ve aynı öğrencilerle ilerlenmesi değerlendirme sınırlarıdır.')
head('9. Kontrollü özellik deneyi ve olasılık uyumu')
image(Path('outputs/dev_feature_experiments/ozellik_karsilastirmasi.png'),335)
table([['Aday','Ham alan','DEV log loss'],['LR6',6,'0,41628'],['Biçim geçmişi eklendi',10,'0,40265'],['Yakın dönem eklendi',8,'0,41397'],['İkisi birlikte - seçilen',12,'0,40038']],[280,80,140])
p('Biçim geçmişinin katkısı daha büyüktür. Son 10 pencere, birlikte kullanılan adaya küçük ek kazanç sağlar. Her metrikte tek adayın üstün olduğu ileri sürülmez; örneğin 10 aralıklı kalibrasyon farkı biçim adayında 0,00446, LR12’de 0,00542’dir. Alt grup ve yeniden örnekleme hesapları seçim yapılan DEV üzerinde keşif amaçlıdır.')
head('10. K-Means 2, 3 ve 4 küme karşılaştırması')
image(Path('outputs/kmeans_first_run/secili_kume_profilleri.png'),340)
table([['k','Silhouette','Grup büyüklükleri'],[2,'0,38860','77 / 123'],[3,'0,45691','40 / 68 / 92'],[4,'0,47378','18 / 64 / 42 / 76']],[70,150,280])
p('200 TRAIN profili yalnız 29 farklı noktaya yerleşir; iki boyutun her birinde 0/6..6/6 olduğundan en çok 49 konum vardır. Aynı noktadaki öğrenciler çıkarılmamıştır. En az 5 kişilik geçerli kümeler arasında en yüksek silhouette ile k=4 seçilir. 0,47378 bir doğruluk yüzdesi değildir; k=3 farkı yaklaşık 0,0169’dur.')
p('Son altı cevap penceresi geçicidir: bir cevap değişince oran 16,7 yüzde puan oynar. Kaynak görev zorluğu ve tekrarlanan birkaç yerel kelime farklıdır; dört kalıcı insan tipi keşfedildiği iddia edilmez.')
head('11. Gerçek öğretim ekranı ve açıklamalı tekrar')
image(Path('outputs/final_scenario/teaching.jpg'),310)
image(Path('outputs/final_scenario/feedback.jpg'),270)
p('Şekil 3-4. Aynı sentetik Ayşe senaryosunda cat/yazma ihtiyacı, resim-ses-anlam-yazılış desteğiyle çalışılır. ca cevabına eksik t açıklaması verilir ve aynı hedefte tekrar açılır. Doğru yazılış görünürken verilen doğru, yalnız destekli başarıdır. Bu kayıtların native_history_used alanı false kalır.','SmallTR')
head('12. Çalışan ortak kontrol, profil ve öneri')
image(Path('outputs/pilot_common_control/listen_write.jpg'),285)
image(Path('outputs/final_scenario/profile_advice.jpg'),285)
p('Şekil 5-6. İpucusuz dinleyerek yazma ekranında ses oynatılmış ve gerçek cevap kaydedilmiştir. Sonraki profil ekranında toplam 8 metin + 8 uygun dinleme kaydı vardır; son altılarda [1,00; 0,50], Grup 3. Kaynak merkezi [0,9365; 0,5437], 42 kaynak öğrencidir. Önerinin yönü bireysel oran farkına dayanır.','SmallTR')
head('13. Konu/hedef başarısı ve gecikmeli kanıt')
image(Path('outputs/final_scenario/target_evidence.jpg'),345)
p('Operasyonel gösterge: belirli konu + hedef + aşamada doğru/toplam. Paydanın yanında temsil edilen kelime sayısı gösterilir. Ayşe’nin bağımsız kontrolleri doğru olsa da gecikmeli alan Bekliyor kalır. 0/2 iki kontrolde doğru sayısı, gecikmeli kontrolün henüz yapılmamasıyla birlikte okunmalıdır; %0 öğrenme diye yorumlanmaz.')
table([['Yardımsız','Gecikmeli','Sonraki durum'],['Doğru','Doğru','Gecikmeli kontrolde hatırladı'],['Doğru','Yanlış','Gecikmeli hatırlama başarısız; yeniden öğretim'],['Yanlış','Doğru','Ek bağımsız kontrol; otomatik yeniden öğretim yok'],['Yanlış','Yanlış','Yeniden öğretim']],[95,95,310])
p('Ek kontrol sonucu ayrı üçüncü gözlemdir. Yanlışsa ilgili hedef yeniden öğretime adaydır; doğruysa ek bağımsız kontrolde doğruladı olarak kaydedilir. Yeni öğretim eski gecikmeli doğruyu kendi kanıtı saymaz; başka hedeflerin geçerli sürümü ve bekleme süresi korunur.')
head('14. Ana ortam: konu, biçim ve tur özeti')
image(Path('outputs/final_scenario/topic_evidence.jpg'),355)
p('Ana ortam tanılama ile alıştırmayı ayrı gruplar. Örnekte hayvanlar/dinleyerek yazma alıştırması 0/2, yalnız 1 kelime ve 2 turdur; yorumun kapsamını bu sayılar belirler. Aynı tabloda yüksek oranlı ama az kelimeli hücreler de güçlü konu etiketi almaz.')
p('En az 2 alıştırma turunda 3 gözlemi olan kelimeler için son üç gerçek cevap ayrıca gösterilir. En az ikisi yanlışsa tekrar önceliği, üçü doğruysa tekrarlı doğru etiketi kullanılır. Bu açıklanmış bir uygulama kuralıdır; öğrenilmiş sınıf veya bilimsel yeterlilik eşiği değildir. Koşul oluşmazsa sayılar gösterilir, yorum ertelenir.')
p('Tur-zaman görünümü ilk/son zaman, biçim, doğru/toplam ve tur kimliğiyle izlenir. Kümülatif çizgi gözlenen doğruluğun geçmişidir; tek başına öğretimin nedensel etkisini göstermez. Model olasılığı, gözlenen oran ve öneri kuralı farklı alanlarda tutulur.')
head('15. Kayıt yapısı, kaynak kodun bölümleri')
table([['Bileşen','Sorumluluk / önemli girişler'],['features.py + experimental_features.py','Cevap öncesi 12 alan, tamamlanan alıştırmayla geçmiş güncelleme, son-10 pencere.'],['profiles.py','Son-altı pencereleri, kaynaktan etikete bakmadan hedef seçimi, yeterli profil kontrolü.'],['tutor_engine.py','Modelleri yükleme, geçmiş replay, LR puanı, ana soru seçimi, görsel tekrar, raporlama.'],['pilot.py','16 soruluk ölçüm, hedef öğretimi, destek geçişleri, ortak kontrol, sürüm/zaman ve dört karar.'],['learning_evidence.py','Konu/biçim/aşama özeti, tekrar kanıtı ve bireysel oranlara dayalı öneri.'],['tutor_store.py + app_server.py','SQLite transaction, kalıcı kayıt, HTTP API, opak ses/resim yolları, arayüz dosyaları.'],['web/static/*.js + *.html + style.css','Konu seçimi, soru/geri bildirim, profil/kanıt ekranları ve diyagram gösterimi.'],['Eğitim betikleri','Alt küme hazırlama, LR6, DEV baseline/özellik deneyleri, profil ve K-Means eğitimi.'],['launch_tutor.py + demo_scenario.py','Yerel başlatma ve kişisel kayıtlar dışında sentetik gösterim.']],[195,305])
p('records: id, stage, cycle, target_epoch, batch_id, word, skill, correct, submitted, at, assisted, native_history_used. Uygun yazmada model_before ve history_after bulunur. Ortak kontrol skill=listen_write, assessment_role=common_control olarak ayrılır. attempts yalnız uygun yerel metin/listen kayıtlarını taşır. Öğretim kanıtı yenilense bile geçmişteki gerçek cevaplar model geçmişinden silinmez.')
head('16. Doğrulama, sınırlamalar ve çalıştırma')
p('56 otomatik test geçti. Bunlar özellik sınırlarını, kaynak profil seçimini, model entegrasyonunu, geçişleri, dört karar durumunu, hedef kanıtlarının korunmasını, gerçek zaman kapısını, eski gönderim reddini, eski kayıt uyumunu ve yeni ortak kontrol/özetleri denetler. Tarayıcı görüntüleri ayrı sentetik veritabanından alındı. Ses oynatma, 4+0’dan 4+1’e native güncelleme, Grup 3 ve yeni konu/öneri ekranları gözlendi.')
p('Kaynak aktarımı: SLAM DEV’de genel geçmiş en az 128, ortanca 941 hedeftir; pilot sıfır geçmişle başlar. Dört sentetik doğru yazmadan sonra LR %96-98 tahmin üretebilir; bunun pilot kalibrasyonu gösterilmiş değildir. Modelde son tekrardan beri süre, öğretim türü veya hedef sürümü özellikleri yoktur. LR unutma modeli, küme de CEFR değildir.')
p('Gerçek öğrencide 24 saatlik kazanım sonucu henüz yoktur. Gecikmeli akış test saatli birim testlerinde denenmiş, gerçek ekranda zaman kapısı korunmuştur. Kontrollü bir öğrenme etkisi veya soru sıralama faydası deneyi yapılmamıştır.')
p('Kurulum: ZIP’i çıkarın; Windows/Python 3.13 üzerinde Kurulum.cmd, ardından Baslat.cmd. Elle: .venv/Scripts/python.exe src/app_server.py --port 8765. Ana ekran /, pilot /pilot yolundadır. Model eğitimi açılış için gerekmez. requirements-lock.txt sürümleri, veri lisansı, hazırlanmış alt küme ve yeniden üretim komutları CALISTIRMA.txt içindedir.')
p('Paket, ayrı bir klasörde boş veritabanıyla modele, kataloğa, sese, görsele ve pilot akışına erişim açısından kontrol edilir; ayrıntılar TESLIM_KONTROLU.json dosyasındadır. Kullanılan bağımlılıkların mevcut yerel ortamdan sağlanması ile internetten taze kurulumun doğrulanması ayrı belirtilir. Öğretmenin bağlantısına fiilî gönderim bu çalışmanın parçası olarak otomatik yapılmamıştır.')
head('17. Araştırma bağlamı ve kaynaklar')
p('Zhu, M., Qiu, L., Zhou, J. (2026). Prompt-tuning for improving knowledge tracing in intelligent tutoring. Data Mining and Knowledge Discovery, 40:36. DOI: 10.1007/s10618-026-01208-9. Hocanın paylaştığı 30 sayfalık makalenin ilk sayfasında PLKT, LKM ön eğitimi, PromEnc ve dört veri kümesindeki deneyler tanıtılır; bu özgün yöntem araştırmasıdır, survey olarak kullanılmamıştır.')
p('Makalenin rolü araştırma bağlamıdır: öğrenci geçmişinden gelecekteki performans tahmini. Bu midtermde PLKT, prompt-tuning veya derin model yeniden uygulanmış değildir. Uygulanan çözüm, midtermde istenen supervised/unsupervised işlev tasarımı için açıklanabilir LR ve K-Means’tir. Önceki ödevlerin fine-tuning, fusion veya duygu analizi teknikleri bu projeye zorunlu bileşen olarak taşınmamıştır.')
p('Settles, B., Brust, C., Gustafson, E., Hagiwara, M., Madnani, N. (2018). Second Language Acquisition Modeling. Duolingo SLAM veri atfı: DOI 10.7910/DVN/8SWHNO. https://sharedtask.duolingo.com/2018.html. Projede bu kaynak veri/protokol atfıdır; PLKT yerine yeniden uygulanmış yöntem gibi sunulmaz.')
p('Scikit-learn: LogisticRegression, ColumnTransformer, StandardScaler, OneHotEncoder, KMeans ve silhouette_score resmi API belgeleri. https://scikit-learn.org/stable/ (kullanılan yerel sürüm: 1.9.1).')
p('Flask resmi belgeleri: https://flask.palletsprojects.com/ . Yerel HTTP uygulaması. SQLite ve Python standart kütüphanesi kayıt/işlem yönetimi sağlar.')
p('Duolingo veri lisansı CC BY-NC 4.0 ve yayın CITING metni LICENSES klasöründe korunmuştur. Yerel resimler nesne simgeleridir; resimlerde görüntü tanıma yapılmamıştır. Rapor, kod, katalog ve sentetik örnek eğitim projesi kapsamında hazırlanmıştır.')

head('18. Slayt biçiminde deney sonuçları ve hata matrisi')
audit=load('outputs/dev_feature_experiments/training_audit.json')['fits']
table([['Eğitim denemesi','Solver iterasyonu','Fit süresi (s)']]+[[label,audit[key]['iterations'][0],f"{audit[key]['fit_seconds']:.3f}"] for key,label in [('format_history','LR10: biçim'),('recent_history','LR8: yakın dönem'),('format_and_recent','LR12: birlikte')]],[250,125,125])
image(Path('outputs/presentation_plots/lr12_confusion_tr.png'),300)
p('LR karşılaştırması Bölüm 9’da tek kez gösterilir. Buradaki tablo gerçek eğitim günlüklerinin iterasyon ve süre bilgilerini verir; süreler kullanılan bilgisayara aittir. LR’nin iterasyon başına kayıp geçmişi kaydedilmediği için beş epoch süren DistilBERT örneğine benzeyen yapay bir eğitim eğrisi çizilmemiştir. Hata matrisi sabit 0,50 eşiğindeki 916 yakalanan ve 3.459 kaçırılan hatayı açık gösterir.','SmallTR')
head('19. Basit yöntem katkısı ve küme seçimi grafikleri')
image(Path('outputs/presentation_plots/baseline_loss_tr.png'),270)
image(Path('outputs/presentation_plots/kmeans_selection_tr.png'),235)
p('Kaynak DEV’de LR12’nin log loss değeri basit oranlardan düşüktür. Küme seçimi grafiğinde k=4 en yüksek silhouette verir; inertia azalışı tek başına seçme ölçütü değildir. Bu şekiller notebooks/LexiPath_Experiments.ipynb içinde kodları ve gerçek hücre çıktılarıyla yeniden üretilebilir. Notebook kayıtlı sonuçları okur, model eğitmez veya TEST örneklerini açmaz.','SmallTR')
head('20. Ayrıntılı teknik mimari ve çalıştırılmış notebook')
image(Path('outputs/presentation_plots/technical_architecture_tr.png'),365)
p('Slaytlardaki veri-akışı anlatımından esinlenerek eğitim ve canlı kullanım ayrıldı. LR’de 12 ham sütun, kelime/biçim one-hot kodlaması ve sayısal ölçekleme sonrasında 1382 alana dönüşür; kaydedilmiş katsayı dizisi (1,1382) boyutundadır. K-Means 200×2 TRAIN profili kullanır; seçilen merkezler 4×2’dir. Bu iç dönüşümler önceki ML görev diyagramındaki iki görevin ayrıntılarıdır.')
p('Notebook; veri kapsamı, dört LR adayının değişiklikleri, kayıtlı solver iterasyonları/süreleri, DEV karşılaştırmaları, K-Means 2/3/4 seçimi ve sentetik öğrencinin merkezle karşılaştırmasını açıklar. Yedi kod hücresi proje Python ortamında çalıştırılıp standart çıktı ve grafikler notebook dosyasına gömülmüştür. Jupyter/VS Code’da aynı ortamla açılabilir. Gerçek epoch eğrisi, yeni TEST değerlendirmesi veya gerçek öğrenme kazanımı üretilmiş sayılmaz.')

# Kod görselleri: gerçek dosyadan alınan işlevsel kesitler; tam kaynak arşivdedir.
snippets=[
 ('features.py','features_before_answer','Temel geçmiş alanları','Genel ve kelime sayıları ile düzeltilmiş oranlar cevap öncesinde hazırlanır. Eksik geçmişteki 0,5 model tahmini değil girdi başlangıcıdır.'),
 ('experimental_features.py','experimental_features_before_answer','Biçim ve yakın dönem alanları','Biçim, kelime-biçim ve son 10 tamamlanmış alıştırma alanları aynı işlevle eğitimde ve canlı tahminde çıkarılır.'),
 ('experimental_features.py','observe_experimental_exercise','Geçmişin güncellenmesi','Önce tahminler üretilir, sonra tamamlanmış alıştırma genel/biçim/kelime sayaçlarını ve son-10 deque yapısını günceller.'),
 ('profiles.py','observe_for_profile','Denetimsiz profil kaydı','Kaynak alıştırmadan sonuçtan bağımsız bir hedef seçilir. Zaman sırası korunur; her alıştırma en fazla bir profile gözlem verir.'),
 ('tutor_engine.py','score','Eğitilmiş LR ile tahmin','Gerçek tamamlanmış geçmiş replay edilir, 12 sütunlu DataFrame model sözleşmesine uyar ve predict_proba sınıf 1 olasılığını verir.'),
 ('tutor_engine.py','start_session','Ana soru seçme politikası','Tanılama ile öğretim turları ayrıdır. LR puanı aday sırasına katkı verir; tur kompozisyonu, aralık ve tekrar sınırları açık kurallardır.'),
 ('tutor_engine.py','prepare_visual','Görsel tekrarın model bağlantısı','Yanlış kaydı olan ve görsel bankasında bulunan kelimeler uygun adaydır. Metin LR tahminiyle önceliklendirilir; görsel olasılık tahmini yapılmaz.'),
 ('pilot.py','prepare','Pilot görev planı','Yeni 16 soruluk plan ve ayrı ortak dinleyerek-yazma görevleri hazırlanır. Yazma hedefi duraklamış kelimenin ortak görevi atlanır. Eski planlar korunur.'),
 ('pilot.py','answer','Gerçek cevap ve model geçmişi','Yazı normalleştirilip tek hedefle karşılaştırılır. listen_write cevabı listen olarak, yazma cevabı reverse_translate olarak geçmişe girer; resimli cevaplar girmez.'),
 ('pilot.py','continue_support','Açıklamalı tekrar ve hedef geçişi','İlk yanlış aynı hedefi tekrar açar. Başarı veya duraklatma sonrası sıradaki hedefin öğretimine geçilir; destekli başarı bağımsız kanıt olmaz.'),
 ('pilot.py','decision','Dört kontrol kararı','Yalnız geçerli hedef sürümünün bağımsız, gecikmeli ve ek kontrol kayıtları okunur. Yanlış/doğru durumu ek kontrol ister; gecikmeli doğru tek başına başarıya çevrilmez.'),
 ('pilot.py','retry','Hedefe özgü yeniden öğretim','Yalnız reteach kararındaki hedefler yeni sürüme alınır. Diğer hedeflerin süre ve sonuçları korunur; eski ham kayıtlar silinmez.'),
 ('learning_evidence.py','pattern_guidance','Örüntünün çalışma önerisine dönüşümü','Bireysel iki oran karşılaştırılır; eşitse yön uydurulmaz. Kaynak merkezin rolü ve son-altı penceresinin sınırı açıklanır.'),
 ('learning_evidence.py','attempt_summary','Konu ve tur kanıtı','Konu, biçim ve tanılama/alıştırma ayrı tutulur. Doğru/toplam, kelime ve tur sayıları birlikte sunulur; yalnız tekrar kanıtı bulunan kelime yorumlanır.'),
 ('tutor_store.py','change','SQLite kalıcılığı','BEGIN IMMEDIATE ile işlem açılır, kayıt yüklenip güncellenir ve hata durumunda rollback olur. Aynı görevin tekrar gönderimi uygulama düzeyinde reddedilir.'),
 ('app_server.py','create_app','HTTP ve yerel uygulama','Modeller ve iki ayrı SQLite store bağlanır. Ana uygulama ve pilot farklı API yollarını kullanır; ses/resim anahtarları kelime adını açık URL içinde taşımaz.'),
 ('run_dev_feature_experiments.py','main','Kontrollü deney betiği','Yalnız TRAIN ile fit, DEV ile karşılaştırma yapılır. Eski model referans olarak korunur; TEST geliştirmeye açılmaz.'),
 ('train_kmeans.py','main','Küme sayısının seçimi','Yalnız TRAIN profilleriyle k=2,3,4 karşılaştırılır. Sabit tohum ve tekrar başlangıçlarıyla en yüksek geçerli silhouette seçilir.')]
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',19)
code_index=[]
for number,(filename,func,title,explanation) in enumerate(snippets,1):
 source=ROOT/'src'/filename;lines=source.read_text(encoding='utf-8').splitlines();tree=ast.parse('\n'.join(lines))
 nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==func]
 if not nodes:continue
 n=nodes[0];start=n.lineno;end=min(n.end_lineno,start+24)
 rendered=[]
 for i in range(start,end+1):
  pieces=textwrap.wrap(lines[i-1].expandtabs(4),width=100,replace_whitespace=False,drop_whitespace=False) or ['']
  rendered.extend([f'{i:4d}  '+pieces[0]]+['      '+x for x in pieces[1:]])
 im=PILImage.new('RGB',(1320,60+len(rendered)*25),'#F3F6F8');draw=ImageDraw.Draw(im)
 draw.text((18,12),f'src/{filename} | {func} | {start}-{end}',font=font,fill='#087E86')
 for i,line in enumerate(rendered):draw.text((15,52+i*25),line,font=font,fill='#17394A')
 asset=ASSETS/f'code_{number:02d}.png'
 if number in {1,2,4,5,7,9,11,12,13,15}:
  im.save(asset)
  head(f'Ek A{number:02d}. {title}');image(asset.relative_to(ROOT),390)
  p(explanation)
  p(f'Kaynak: src/{filename}, {start}-{end}. Uzun satırlar okunabilirlik için sarılmıştır. Tam işlev ve çağrı bağlamı Python dosyasında bulunur.','SmallTR')
 code_index.append({'file':filename,'function':func,'start':start,'end':end,'explanation':explanation})
(ASSETS/'code_index.json').write_text(json.dumps(code_index,ensure_ascii=False,indent=2),encoding='utf-8')
head('Ek A. Diğer işlevlerin açıklaması')
for i,(filename,func,title,explanation) in enumerate(snippets,1):
 if i not in {1,2,4,5,7,9,11,12,13,15}:p(f'{filename} / {func}: {explanation}')
head('Ek B. Kod ve çıktı dosyalarını okuma rehberi')
p('Uygulama kodu: tutor_engine ve pilot iş mantığı; learning_evidence gözlem/öneri; tutor_store kalıcılık; app_server API; launch_tutor başlatma. web/static/app.js ana ekran, pilot.js hedef döngüsü, style.css yerleşimdir. HTML dosyaları ekran köklerini bağlar.')
p('Eğitim: prepare_slam_subset resmi arşivden seed=42 ile 200 öğrenciyi koruyarak alt küme hazırlar. train_logistic ilk LR6 çalışmasıdır. compare_dev_baselines basit oranları karşılaştırır. run_dev_feature_experiments dört özellik adayını üretir. prepare_profiles ve train_kmeans profil/merkez zinciridir. render_final_diagrams görselleri yeniden üretir. demo_scenario gerçek öğrenciye karışmayan sentetik örnek üretir.')
p('logistic_first_run: tarihsel LR6 model/ölçüm/audit. dev_baseline_comparison: DEV oran yöntemleri, tahmin ve kalibrasyon hesapları. dev_feature_experiments: seçilen LR12 ve diğer adayların metrik/audit/grafikleri. kmeans_first_run: k karşılaştırması, merkezler, atamalar ve model. diagrams: iki son şekil. final_scenario: açıklanmış sentetik senaryo JSON ve ekranları. Çıktı klasör adları ve model dosyaları çalışma zamanı bağımlılığı olarak korunur.')
p('test_*.py dosyaları davranış doğrulamasıdır; öğrenci başarısı ölçümü değildir. Kaynak TEST kayıtları ilk deneyin yeniden üretimi için pakette bulunur; seçilen LR12 üzerinde yeni TEST performansı raporlanmaz. Tam işlev listesi KOD_HARITASI.txt içindedir.')
p('Her grup üyesi modelleri, alan şemalarını ve makul kod değişikliklerini açıklayabilmelidir. Sunum: 27 Kasım 2026, 14:40, B-Yunus Emre. Teslim, grup adına öğretmenin belirttiği bağlantıdan tek kişi tarafından yapılmalıdır; raporun oluşturulması gönderim anlamına gelmez.')

def footer(canvas,doc):
 canvas.setStrokeColor(colors.HexColor('#D7E2E8'));canvas.line(43,38,552,38)
 canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor('#486070'));canvas.drawString(43,25,'LexiPath | Data Mining Midterm | 22.11.2026');canvas.drawRightString(552,25,str(doc.page))
doc=SimpleDocTemplate(str(OUT/'LexiPath_Midterm_Raporu.pdf'),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=43,bottomMargin=48,title='LexiPath - Data Mining Midterm',author='Eren Hasan Katırcıoğlu; Mehmet Ertuğrul Ünal; Hasan Yunus Zengin; Ömer Gökalp; Mustafa Kemal Bozkurt')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT/'LexiPath_Midterm_Raporu.pdf')
