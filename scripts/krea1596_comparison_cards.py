"""Build advisory contact sheets from preserved benchmark PNGs; originals are never modified."""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
MODELS=['anima_base_rebuilt','anima_turbo','krea2_base']
SEEDS=[7725,7726,7727]
def build(cohort):
 results=json.loads((cohort/'results.json').read_text())['results'];lookup={(r.get('candidate_id'),r.get('workflow_id'),r.get('seed')):r for r in results}
 cards=cohort/'comparison_cards';cards.mkdir(exist_ok=True);inventory=[];index=['# 24-style model comparison','', 'All images REVIEW_REQUIRED. Three distinct seeds show variation consistency; exact rerun repeatability NOT_MEASURED. Originals are linked separately.','']
 for n in range(1,25):
  cid=f'CAND-{n:03}';sheet=Image.new('RGB',(1152,1884),'#252525');draw=ImageDraw.Draw(sheet);draw.text((10,8),cid+' | columns: seeds 7725 / 7726 / 7727',fill='white')
  index.extend(['## '+cid,'',f'![{cid} comparison](comparison_cards/{cid}.png)',''])
  for row,model in enumerate(MODELS):
   draw.text((8,32+row*612),model,fill='white')
   for col,seed in enumerate(SEEDS):
    r=lookup.get((cid,model,seed));x=col*384;y=58+row*612
    if not r or not r.get('originals'):
     draw.text((x+10,y+10),'FAILED' if r else 'NOT_GENERATED',fill='white');continue
    original=Path(r['originals'][0]['path']).resolve();digest=hashlib.sha256(original.read_bytes()).hexdigest()
    if digest!=r['originals'][0]['sha256']:raise ValueError('Original hash changed')
    with Image.open(original) as im:sheet.paste(im.convert('RGB').resize((384,576),Image.Resampling.LANCZOS),(x,y))
    inventory.append({'candidate_id':cid,'model':model,'seed':seed,'path':str(original),'sha256':digest})
    index.append(f'- {model} / {seed}: [original]({original.as_posix()}) SHA256 `{digest}`')
  sheet.save(cards/(cid+'.png'))
  for row,model in enumerate(MODELS):
   sheet.crop((0,32+row*612,1152,58+row*612+576)).save(cards/(cid+'_'+model+'.png'))
  index.append('')
 (cohort/'comparison_card.md').write_text('\n'.join(index),encoding='utf-8')
 (cohort/'image_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
 print('Preserved original inventory:',len(inventory))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('cohort',type=Path);build(p.parse_args().cohort)
