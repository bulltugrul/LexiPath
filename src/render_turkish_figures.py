"""Türkçe raporun grafikleri; aynı kayıtlı sonuçlar, yeni model eğitimi yok."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/presentation_plots'
def main():
 plt.rcParams.update({'font.family':'DejaVu Sans'})
 read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
 exp=read('outputs/dev_feature_experiments/comparison.json')['metrics']
 base=read('outputs/dev_baseline_comparison/comparison.json')['metrics']
 cluster=read('outputs/kmeans_first_run/comparison.json')
 keys=['original','format_history','recent_history','format_and_recent'];names=['LR6','LR10: biçim','LR8: yakın dönem','LR12: birlikte']
 fig,axes=plt.subplots(1,3,figsize=(14,4.4),constrained_layout=True)
 for ax,key,title in zip(axes,['accuracy_at_0_5','log_loss','roc_auc_correct_positive'],['DEV doğruluğu (eşik 0,50)','DEV log loss (düşük daha iyi)','DEV ROC AUC']):
  vals=[exp[k][key] for k in keys];ax.bar(names,vals,color=['#90a6ba','#32a6a0','#8074bd','#087e86']);ax.set_title(title);ax.tick_params(axis='x',rotation=22);ax.set_ylim(0,.5 if key=='log_loss' else 1);ax.grid(axis='y',alpha=.2)
  for i,v in enumerate(vals):ax.text(i,v+.012,f'{v:.4f}',ha='center',fontsize=9)
 fig.suptitle('Kontrollü LR denemeleri: kaydedilmiş son DEV sonuçları');fig.savefig(OUT/'lr_run_metrics_tr.png',dpi=180);plt.close(fig)
 labels=['Sabit TRAIN','Öğrenci geçmişi','Öğrenci-kelime geçmişi','Kelime-biçim TRAIN','LR6','LR12']
 vals=[base[k]['log_loss'] for k in ['constant_train','learner_history','learner_word_history','word_format_train']]+[exp['original']['log_loss'],exp['format_and_recent']['log_loss']]
 fig,ax=plt.subplots(figsize=(9,4.5),constrained_layout=True);ax.barh(labels,vals,color=['#9aabba']*4+['#8074bd','#087e86'])
 for i,v in enumerate(vals):ax.text(v+.003,i,f'{v:.4f}',va='center')
 ax.set_xlim(0,.55);ax.invert_yaxis();ax.set_xlabel('DEV log loss (düşük daha iyi)');ax.set_title('Basit oranlara göre tahmin katkısı');fig.savefig(OUT/'baseline_loss_tr.png',dpi=180);plt.close(fig)
 cm=np.array(exp['format_and_recent']['confusion_rows_actual_cols_predicted_error_correct']);fig,ax=plt.subplots(figsize=(6,4.6),constrained_layout=True);ax.imshow(cm,cmap='Blues')
 for i in range(2):
  for j in range(2):ax.text(j,i,str(cm[i,j]),ha='center',va='center',fontsize=18,color='white' if cm[i,j]>cm.max()/2 else '#17394a')
 ax.set_xticks([0,1],['Tahmin: yanlış','Tahmin: doğru']);ax.set_yticks([0,1],['Gerçek: yanlış','Gerçek: doğru']);ax.set_title('LR12: DEV hata matrisi (eşik 0,50)');fig.savefig(OUT/'lr12_confusion_tr.png',dpi=180);plt.close(fig)
 candidates=cluster['candidates'];ks=[c['k'] for c in candidates];fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
 axes[0].plot(ks,[c['silhouette'] for c in candidates],'o-',color='#087e86');axes[0].set_title('Silhouette (yüksek daha iyi)')
 axes[1].plot(ks,[c['inertia_scaled'] for c in candidates],'s-',color='#8074bd');axes[1].set_title('Ölçeklenmiş inertia')
 for ax in axes:ax.set_xticks(ks);ax.set_xlabel('Küme sayısı');ax.grid(alpha=.25)
 fig.savefig(OUT/'kmeans_selection_tr.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
