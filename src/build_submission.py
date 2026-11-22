"""Açık dosya listesiyle kişisel kayıtlardan ayrılmış teslim arşivi."""
from pathlib import Path
import ast,hashlib,json,shutil,zipfile,tempfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/submission';STAGE=None;OUT.mkdir(parents=True,exist_ok=True)
def copy(path,target=None):
 source=ROOT/path;dest=STAGE/(target or path);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
def main():
 global STAGE
 build_root=Path(tempfile.mkdtemp(prefix='_build_',dir=OUT)).resolve()
 assert build_root.is_relative_to(OUT.resolve()) and build_root!=OUT.resolve()
 STAGE=build_root/'LexiPath';STAGE.mkdir()
 for folder in ['src','web','notebooks']:
  for path in (ROOT/folder).rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts:copy(path.relative_to(ROOT))
 for name in ['requirements-lock.txt','Baslat.cmd','Kurulum.cmd','CALISTIRMA.txt','project_decisions.json','PILOT_KILAVUZU.txt']:
  copy(Path(name))
 copy(Path('output/pdf/LexiPath_Midterm_Raporu.pdf'),Path('Rapor_TR.pdf'))
 copy(Path('output/pdf/LexiPath_Midterm_Report_EN.pdf'),Path('Rapor_EN.pdf'))
 for path in (ROOT/'data/prepared/slam200').iterdir():
  if path.is_file():copy(path.relative_to(ROOT))
 for name in ['catalog.json','catalog_audit.json','catalog_v2_audit.json']:
  copy(Path('data/prototype')/name)
 folders=['logistic_first_run','dev_baseline_comparison','dev_feature_experiments','kmeans_first_run','diagrams','report_assets','final_scenario','presentation_plots']
 for folder in folders:
  for path in (ROOT/'outputs'/folder).rglob('*'):
   if path.is_file() and path.suffix in ['.json','.txt','.png','.jpg','.svg','.joblib','.csv'] and 'archive_lr6' not in path.parts:copy(path.relative_to(ROOT))
 for name in ['listen_write.jpg','group3.jpg','report.json']:copy(Path('outputs/pilot_common_control')/name)
 copy(Path('LICENSES/SLAM_LICENSE.txt'))
 copy(Path('LICENSES/SLAM_CITING.txt'))
 (STAGE/'LICENSES/ATTRIBUTION.txt').write_text('Duolingo SLAM 2018 - Settles, Brust, Gustafson, Hagiwara, Madnani. DOI 10.7910/DVN/8SWHNO.\nCC BY-NC 4.0. Paket data/prepared/slam200 dosyaları resmi en_es verisinden seed=42 ile alınmış 200 öğrencilik türetilmiş alt kümedir. Alanlar normalize edilmiş, süre yalnız log tutulmuş, source_error terslenerek correct üretilmiştir.\nHam arşiv, Dataverse erişim formu bilgileri ve kişisel yerel öğrenci kayıtları dahil edilmemiştir.\nYerel sesler Microsoft Zira ile oluşturulmuş WAV, SVG resimler nesne simgeleridir.\n',encoding='utf-8')
 code_map=[]
 for source in sorted((ROOT/'src').glob('*.py')):
  tree=ast.parse(source.read_text(encoding='utf-8'));code_map.append(source.name+'\n'+(ast.get_docstring(tree) or '')+'\n')
  for n in ast.walk(tree):
   if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
    code_map.append(f'  {n.name} (satır {n.lineno}-{n.end_lineno}): '+(ast.get_docstring(n) or 'İşlevin çağrı bağlamı ve açıklaması kaynak dosyada / rapor kod rehberinde.')+'\n')
 (STAGE/'KOD_HARITASI.txt').write_text(''.join(code_map),encoding='utf-8')
 control=ROOT/'outputs/final_delivery_check.json'
 if control.exists():shutil.copy2(control,STAGE/'TESLIM_KONTROLU.json')
 internal={'SUNUM_PROVASI.txt','DIYAGRAM_SAVUNMASI.txt','TESLIM_MESAJI.txt'}
 files=sorted(p for p in STAGE.rglob('*') if p.is_file() and p.name!='DOSYA_LISTESI.json' and p.relative_to(STAGE).as_posix() not in internal)
 assert not any(p.suffix in ['.sqlite3','.db','.log'] or '.venv' in p.parts or '__pycache__' in p.parts for p in files)
 manifest=[{'path':str(p.relative_to(STAGE)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
 (STAGE/'DOSYA_LISTESI.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 archive=OUT/'LexiPath_Midterm.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  z.writestr('LexiPath/tmp/','')
  for p in sorted(STAGE.rglob('*')):
   if p.is_file() and p.relative_to(STAGE).as_posix() not in internal:z.write(p,'LexiPath/'+p.relative_to(STAGE).as_posix())
 print(json.dumps({'zip':str(archive),'files':len(files)+1,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
 assert build_root.is_relative_to(OUT.resolve()) and build_root.name.startswith('_build_')
 shutil.rmtree(build_root)
if __name__=='__main__':main()
