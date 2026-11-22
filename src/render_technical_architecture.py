"""Slaytlardan esinlenen, gerçek matris boyutlarıyla teknik veri akışı."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
OUT=Path(__file__).resolve().parents[1]/'outputs/presentation_plots';OUT.mkdir(exist_ok=True)
TR={'LexiPath | Training and inference architecture': 'LexiPath | Eğitim ve tahmin mimarisi', 'TRAIN fits transformations and models. DEV compares candidates. Runtime loads frozen fitted estimators.': 'Dönüşümler ve modeller TRAIN ile öğrenilir. Adaylar DEV ile karşılaştırılır. Uygulama sabit modelleri yükler.', 'SUPERVISED TASK | Logistic regression': 'DENETİMLİ GÖREV | Lojistik regresyon', 'UNSUPERVISED TASK | K-Means': 'DENETİMSİZ GÖREV | K-Means', 'Raw X: N × 12\nword + format\n10 numeric history fields': 'Ham X: N × 12\nkelime + biçim\n10 sayısal geçmiş alanı', 'OneHotEncoder + StandardScaler\nTRAIN-only fit\nEncoded X: N × 1382': 'OneHotEncoder + StandardScaler\nyalnız TRAIN ile öğrenme\nKodlanmış X: N × 1382', 'LogisticRegression\n1382 coefficients + intercept\ny = actual target correctness (0/1)': 'Lojistik regresyon\n1382 katsayı + sabit terim\ny = gerçek hedef sonucu (0/1)', 'LIVE: completed-history x → fixed transformations → sigmoid probability p_correct → writing-review priority': 'CANLI: geçmiş x → sabit dönüşümler → sigmoid olasılığı p_correct → yazma tekrar önceliği', 'TRAIN profiles: 200 × 2\nlast-six text correct rate\nlast-six listening-writing rate': 'TRAIN profilleri: 200 × 2\nson altı metin doğru oranı\nson altı dinleyerek yazma oranı', 'StandardScaler → KMeans\nk = 2, 3, 4; k-means++\nchoose highest valid silhouette': 'StandardScaler → KMeans\nk = 2, 3, 4; k-means++\nen yüksek geçerli silhouette', 'Selected centers: 4 × 2\nNo expected group labels\nSource sizes: 18 / 64 / 42 / 76': 'Seçilen merkezler: 4 × 2\nbeklenen grup etiketi verilmez\nkaynak sayıları: 18 / 64 / 42 / 76', 'LIVE: 6+6 actual answers → two rates → nearest fixed center → provisional group + separate explanation rule': 'CANLI: 6+6 gerçek cevap → iki oran → en yakın sabit merkez → geçici grup + açıklama kuralı', 'Visual teaching and picture choices stay separate. Unassisted native controls update history after the answer.\nTutoring transitions and 24-hour evidence are explicit rules; neither model certifies permanent learning.': 'Görsel öğretim ve resimli seçimler ayrı tutulur. Yardımsız uygun yanıtlar geçmişi günceller.\nÖğretim geçişleri ve 24 saatlik kontrol, açık kurallarla yönetilir.'}
def main(english=True):
 fig,ax=plt.subplots(figsize=(15,9));ax.set(xlim=(0,15),ylim=(0,9));ax.axis('off')
 def text(x,y,value,**kw):return ax.text(x,y,value if english else TR.get(value,value),**kw)
 text(.2,8.65,'LexiPath | Training and inference architecture',fontsize=22,weight='bold',color='#17394a')
 text(.2,8.13,'TRAIN fits transformations and models. DEV compares candidates. Runtime loads frozen fitted estimators.',fontsize=12,color='#486070')
 for y,title,color in [(7.55,'SUPERVISED TASK | Logistic regression','#087e86'),(4.05,'UNSUPERVISED TASK | K-Means','#8074bd')]:
  ax.add_patch(FancyBboxPatch((.25,y-2.85),14.25,2.7,boxstyle='round,pad=.12',facecolor='#f0f6f9',edgecolor=color,lw=2))
  text(.5,y-.55,title,fontsize=17,weight='bold',color=color,va='center')
 text(.5,6.65,'Raw X: N × 12\nword + format\n10 numeric history fields',fontsize=13,va='top')
 text(4.1,6.65,'OneHotEncoder + StandardScaler\nTRAIN-only fit\nEncoded X: N × 1382',fontsize=13,va='top')
 text(9.0,6.65,'LogisticRegression\n1382 coefficients + intercept\ny = actual target correctness (0/1)',fontsize=13,va='top')
 for a,b in [(3.45,3.95),(8.35,8.85)]:ax.annotate('',xy=(b,5.55),xytext=(a,5.55),arrowprops={'arrowstyle':'->','color':'#087e86','lw':2})
 text(.5,5.05,'LIVE: completed-history x → fixed transformations → sigmoid probability p_correct → writing-review priority',fontsize=12,color='#087e86')
 text(.5,3.15,'TRAIN profiles: 200 × 2\nlast-six text correct rate\nlast-six listening-writing rate',fontsize=13,va='top')
 text(4.8,3.15,'StandardScaler → KMeans\nk = 2, 3, 4; k-means++\nchoose highest valid silhouette',fontsize=13,va='top')
 text(10.0,3.15,'Selected centers: 4 × 2\nNo expected group labels\nSource sizes: 18 / 64 / 42 / 76',fontsize=13,va='top')
 for a,b in [(4.2,4.65),(9.35,9.85)]:ax.annotate('',xy=(b,2.05),xytext=(a,2.05),arrowprops={'arrowstyle':'->','color':'#8074bd','lw':2})
 text(.5,1.55,'LIVE: 6+6 actual answers → two rates → nearest fixed center → provisional group + separate explanation rule',fontsize=12,color='#8074bd')
 text(.25,.45,'Visual teaching and picture choices stay separate. Unassisted native controls update history after the answer.\nTutoring transitions and 24-hour evidence are explicit rules; neither model certifies permanent learning.',fontsize=12,color='#486070')
 fig.savefig(OUT/('technical_architecture_'+('en' if english else 'tr')+'.png'),dpi=180,bbox_inches='tight');fig.savefig(OUT/('technical_architecture_'+('en' if english else 'tr')+'.svg'),bbox_inches='tight');plt.close(fig)
if __name__=='__main__':main();main(english=False)
