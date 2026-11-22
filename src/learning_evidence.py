"""Gözlenen başarıyı, model tahminini ve açıklanabilir öneriyi ayrı tutar."""
from collections import defaultdict


def pattern_guidance(profile):
    if not profile.get('group'):
        return {'basis':'insufficient_history','text':'İki biçimde de altışar gerçek cevap oluşunca yakın dönem örüntüsünü inceleyebiliriz.'}
    own=profile['features'];center=profile['group']['reference_center']
    text,listen=own['text_target_accuracy'],own['listen_target_accuracy']
    if text>listen:
        advice='Bu kayıtlarda dinleyerek yazma daha düşük. Ses kaydını dinleyip kelimeyi yardımsız yazma çalışmasına ek zaman ayırmayı düşün.'
    elif listen>text:
        advice='Bu kayıtlarda metinden yazma daha düşük. Anlamdan kelimeyi yardımsız yazmayı ayrıca çalışmayı düşün.'
    else:
        advice='Bu kayıtlarda iki biçimin oranı aynı. Biçim önceliği vermeden yanlış yaptığın kelimeleri hedefle.'
    return {'basis':'observed_last_six_and_nearest_source_center','text':advice,
            'observed':own,'reference_center':center,
            'note':'Öneri bir açıklama kuralıdır. Her biçimde yalnız 6 cevap var; bir cevap oranı 16,7 puan değiştirir. Grubun öğretim etkisi ölçülmedi.'}


def attempt_summary(attempts, words, topics):
    buckets=defaultdict(list);rounds=defaultdict(list);word_rows=defaultdict(list)
    for a in attempts:
        phase='tanılama' if a.get('kind')=='diagnostic' else 'alıştırma'
        key=(a['topic_id'],a['format'],phase)
        buckets[key].append(a)
        rounds[(a.get('session_id','unknown'),phase,a['format'])].append(a)
        if phase=='alıştırma':word_rows[(a['word_id'],a['format'])].append(a)
    def values(rows):
        return {'correct':sum(r['correct'] for r in rows),'count':len(rows),
                'rate':sum(r['correct'] for r in rows)/len(rows),
                'words':len({r['word_id'] for r in rows}),
                'rounds':len({r.get('session_id','unknown') for r in rows}),
                'first_at':rows[0]['timestamp'],'last_at':rows[-1]['timestamp']}
    areas=[dict(topic_id=t,topic=topics[t]['title'],format=m,phase=p,**values(rows))
           for (t,m,p),rows in sorted(buckets.items())]
    timeline=[dict(round_id=s,phase=p,format=m,**values(rows)) for (s,p,m),rows in rounds.items()]
    repeated=[]
    for (w,m),rows in word_rows.items():
        # Uygulama çalışma kuralı; konu yeterliliği veya bilimsel eşik değil.
        if len(rows)<3 or len({r.get('session_id') for r in rows})<2:continue
        last=rows[-3:];wrong=sum(not r['correct'] for r in last)
        if wrong>=2 or wrong==0:
            repeated.append({'word':w,'format':m,'last_three':[r['correct'] for r in last],
                'rounds':len({r.get('session_id') for r in rows}),
                'label':'Tekrar önceliği: son üçte en az iki yanlış' if wrong>=2 else 'Tekrarlı doğru: son üç cevap doğru'})
    return {'areas':areas,'timeline':timeline,'repeated_words':repeated,
            'interpretation':'Oranlar bu görevlerdeki gözlenen doğru/toplamdır. Konu yeterliliği için hüküm verilmez; kayıt, kelime ve tur sayıları birlikte gösterilir.'}


def pilot_evidence(outcomes, records, words, topics):
    buckets=defaultdict(list)
    for o in outcomes:buckets[(words[o['word']]['topic_id'],o['skill'])].append(o)
    areas=[]
    for (topic,skill),rows in sorted(buckets.items()):
        item={'topic':topics[topic]['title'],'skill':skill,'target_words':len(rows)}
        for stage in ['measurement','independent','delayed','extra_check']:
            observed=[r[stage] for r in rows if r[stage] is not None]
            item[stage]={'correct':sum(observed),'count':len(observed),
                         'rate':sum(observed)/len(observed) if observed else None}
        item['retained']=sum(r['decision']=='retained' for r in rows)
        item['reteach']=sum(r['decision']=='reteach' for r in rows)
        item['paused']=sum(r['paused'] for r in rows)
        areas.append(item)
    timeline=defaultdict(list)
    for r in records:
        if 'correct' in r and r['skill'] in ['writing','recognition','listening','listen_write']:
            timeline[(r['cycle'],r['stage'],r['skill'])].append(r)
    return {'areas':areas,
        'remembered':[o['word']+' / '+o['skill'] for o in outcomes if o['decision']=='retained'],
        'needs_support':[o['word']+' / '+o['skill'] for o in outcomes if o['decision'] in ['reteach','paused']],
        'needs_check':[o['word']+' / '+o['skill'] for o in outcomes if o['decision']=='extra_required'],
        'timeline':[{'cycle':c,'stage':s,'skill':k,'correct':sum(r['correct'] for r in rows),
                    'count':len(rows),'first_at':rows[0]['at'],'last_at':rows[-1]['at']}
                    for (c,s,k),rows in timeline.items()],
        'interpretation':'Yardımsız kontrol başarısı ve gecikmeli hatırlama ayrı ölçülür. Her konu yalnız gösterilen kelimelerle temsil edilir; tek kelimeden bütün konuya genelleme yapılmaz.'}
