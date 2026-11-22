"""Ayrı bir veritabanında açıklanmış sentetik sunum örneği üretir."""
from pathlib import Path
import argparse,json
from app_server import create_app
from tutor_engine import ROOT

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--db',type=Path,default=ROOT/'data/demo/demo.sqlite3');args=parser.parse_args()
 app=create_app(args.db);p=app.extensions['pilot'];e=app.extensions['tutor_engine']
 s=p.new('Ayşe - SENTETİK ÖRNEK')
 while s['stage']!='waiting':
  if s['stage']=='teaching':p.teach(s,s['pending']['id'])
  elif s['stage']=='assisted_feedback':p.continue_support(s,s['pending']['id'])
  else:
   q=s['pending'];typed=q['skill'] in ['writing','listen_write','spacing']
   value=q['word'] if typed else e.audio_keys[q['word']]
   if q['skill']=='listen_write' and q['word'] in ['dog','book']:value='wrong'
   if q['stage']=='measurement' and q['word']=='cat' and q['skill']=='writing':value='ca'
   if q['stage']=='assisted' and q['skill']=='writing' and not any(r['stage']=='assisted' for r in s['records']):value='ca'
   p.answer(s,q['id'],value)
 app.extensions['pilot_store'].create(s)
 print(json.dumps({'synthetic':True,'db':str(args.db),'path':'/pilot?run='+s['id'],
                   'profile':p.payload(s)['model_audit']['kmeans']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
