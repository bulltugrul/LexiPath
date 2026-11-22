"""Az yazılı sunum şekilleri; alan şemaları rapordaki tablolarda kalır."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/diagrams'
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
INK='#17394a';TEAL='#087e86';PURPLE='#8074bd'
def text(ax,x,y,s,size=17,**kw):
 return ax.text(x,y,s,fontsize=size,color=INK,ha='center',va='center',linespacing=1.5,**kw)
def box(ax,x,y,w,h,label,color):
 ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=.12',facecolor='#eff7f8' if color==TEAL else '#f3f0fa',edgecolor=color,lw=2))
 text(ax,x,y,label,18,weight='bold')
def arrow(ax,a,b,color=TEAL):
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=23,lw=2.3,color=color))
def save(fig,name):
 fig.savefig(OUT/(name+'.png'),dpi=200,bbox_inches='tight',facecolor='white')
 fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',facecolor='white');plt.close(fig)
def main(english=False):
 OUT.mkdir(exist_ok=True);suffix='_en' if english else ''
 fig,ax=plt.subplots(figsize=(12,5.5));ax.set(xlim=(0,12),ylim=(0,5.5));ax.axis('off')
 text(ax,6,5.05,'LexiPath | Two learning tasks' if english else 'LexiPath | İki öğrenme görevi',23,weight='bold')
 rows=[(3.65,TEAL,'Past responses: 12 fields\n(correct / error labels)' if english else 'Geçmiş cevaplar: 12 alan\n(doğru / yanlış etiketli)',
        'SUPERVISED' if english else 'SUPERVISED · Denetimli',
        'Logistic Regression' if english else 'Lojistik Regresyon',
        'Correctness probability\np_correct: 0..1' if english else 'Doğru cevap olasılığı\np_correct: 0..1'),
       (1.5,PURPLE,'Learner profiles: 2 rates\n(no group labels)' if english else 'Öğrenci profilleri: 2 oran\n(grup etiketi yok)',
        'UNSUPERVISED' if english else 'UNSUPERVISED · Denetimsiz','K-Means',
        'Similar learner groups\ngroup.number: 1..4' if english else 'Benzer öğrenci grupları\ngroup.number: 1..4')]
 for y,color,left,kind,model,right in rows:
  text(ax,1.65,y,left,13);box(ax,6,y,3.4,1.05,model,color)
  ax.text(6,y+.86,kind,fontsize=12,ha='center',va='center',color=color,weight='bold')
  text(ax,10.35,y,right,14)
  arrow(ax,(3.18,y),(4.12,y),color);arrow(ax,(7.88,y),(8.82,y),color)
 text(ax,6,.3,'Text + audio: responses  •  Visual: preferences / teaching' if english else 'Metin + ses: cevaplar  •  Görsel: tercih / öğretim',12)
 save(fig,'ml_blok_diyagrami'+suffix)
 fig,ax=plt.subplots(figsize=(12,5.5));ax.set(xlim=(0,12),ylim=(0,5.5));ax.axis('off')
 text(ax,6,5.05,'LexiPath | Learning journey' if english else 'LexiPath | Öğrenme akışı',23,weight='bold')
 labels=['Initial check','Identify need','Teach','Unassisted\ncheck','24-hour\ncheck','Result / reteach'] if english else ['İlk ölçüm','İhtiyacı belirle','Öğretim','Yardımsız\nkontrol','24 saat sonra\nkontrol','Sonuç / tekrar']
 positions=[(2,3.55),(6,3.55),(10,3.55),(10,1.55),(6,1.55),(2,1.55)]
 for i,((x,y),label) in enumerate(zip(positions,labels)):
  box(ax,x,y,3.05,1.0,label,TEAL)
 for i in range(5):
  x,y=positions[i];xx,yy=positions[i+1]
  if y==yy:
   direction=1 if xx>x else -1
   arrow(ax,(x+direction*1.68,y),(xx-direction*1.68,yy))
  else:arrow(ax,(x,y-.65),(xx,yy+.65))
 save(fig,'ogrenci_akisi'+suffix)
 if not english:
  (OUT/'DIYAGRAM_ACIKLAMASI.txt').write_text('Ana şekiller az yazılı sunum özetidir. ML şeklinde yalnız LR ve K-Means kutuları öğrenen görevlerdir.\nLR etiketli geçmişten sonraki cevap olasılığını, K-Means grup etiketi verilmemiş profillerden benzerlik grubunu üretir.\n12 girdi alanı, çıktı şemaları, 6+6 koşulu ve ayrıntılı öğretim geçişleri raporun tablolarında açıklanır.\nÖğrenci akışı destekleyici senaryodur; ML blok diyagramının yerine geçmez.\n',encoding='utf-8')
if __name__=='__main__':main()
