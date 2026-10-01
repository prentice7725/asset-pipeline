"""Read-only M2.5 evidence aggregation and candidate galleries; no approval or generation."""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from assetpipe.manifests import write
from assetpipe.prompt_mining import sha256

ROOT=Path(__file__).resolve().parents[1]
CRITERIA=['1x readability','silhouette','color clusters','outline','equipment separation','transparent boundary','postprocessing cost']


def gallery(rows, directory, name, native):
    cards=[]
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
    for row in rows:
        if not row.get('original_pngs'):
            continue
        source=ROOT/row['original_pngs'][0]['path']
        with Image.open(source) as opened:
            image=opened.convert('RGBA')
        if not native:
            image.thumbnail((384,384),Image.Resampling.LANCZOS)
        width=max(400,image.width+32)
        height=image.height+112
        card=Image.new('RGB',(width,height),(236,236,236))
        card.paste(image,(16,96),image)
        draw=ImageDraw.Draw(card)
        draw.text((16,12),row['style_id']+' / '+row['asset_role'],font=font,fill='black')
        draw.text((16,36),row['status'],font=small,fill='black')
        draw.text((16,56),('Native 1x, original pixels' if native else 'Preview thumbnail; inspect original separately'),font=small,fill='black')
        draw.text((16,74),'Unapproved candidate; art review required',font=small,fill='black')
        cards.append(card)
    if not cards:
        return None
    width=max(c.width for c in cards);height=max(c.height for c in cards)
    sheet=Image.new('RGB',(width*2,height*((len(cards)+1)//2)),(190,190,190))
    for i,card in enumerate(cards):
        sheet.paste(card,((i%2)*width,(i//2)*height))
    path=directory/name
    sheet.save(path)
    return {'path':str(path.relative_to(ROOT)),'sha256':sha256(path),'native_1x':native}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',type=Path,required=True)
    args=parser.parse_args()
    out=args.cohort.resolve()
    report=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    rows=report['samples']
    analysis=[]
    for row in rows:
        path=ROOT/row.get('manifest','MISSING')
        if not path.is_file():
            continue
        manifest=json.loads(path.read_text(encoding='utf-8'))
        directory=path.parent
        original=row.get('original_pngs',[])
        dimensions=[]
        for item in original:
            with Image.open(ROOT/item['path']) as image:
                dimensions.append(list(image.size))
        prepared=json.loads((ROOT/row['prepared']).read_text(encoding='utf-8'))
        pixel=prepared['brief']['output_class']=='PIXEL_STATIC'
        gate=directory/'040_pixel_gate/pixel_report.json'
        # The ported report filenames are discovered rather than inferred.
        gate_reports=list((directory/'040_pixel_gate').glob('*.json'))
        analyzer=json.loads(gate_reports[0].read_text()) if gate_reports else None
        refine=directory/'030_refiner/refine_report.json'
        ref=json.loads(refine.read_text()) if refine.exists() else None
        generation=directory/'010_generation/generation.json'
        gen=json.loads(generation.read_text()) if generation.exists() else {}
        duration=None
        if gen.get('completed_at_utc') and gen.get('created_at_utc'):
            duration=(datetime.fromisoformat(gen['completed_at_utc'])-datetime.fromisoformat(gen['created_at_utc'])).total_seconds()
        analysis.append({'id':row['id'],'output_class':prepared['brief']['output_class'],
            'technical_status':manifest['status'],'pixel_gate':analyzer['status'] if analyzer else 'NOT_APPLICABLE' if not pixel else 'NOT_RUN',
            'pixel_reasons':analyzer['reasons'] if analyzer else None,
            'unique_colors':analyzer['palette']['unique_color_count'] if analyzer else None,
            'alpha':analyzer['alpha'] if analyzer else None,
            'gradient_suspicion':analyzer['gradient_suspicion'] if analyzer else None,
            'anti_alias_suspicion':analyzer['anti_alias_suspicion'] if analyzer else None,
            'changed_pixels':ref['changed_pixel_count'] if ref else None,
            'palette_pixels_changed':ref['palette_pixels_changed'] if ref else None,
            'generation_seconds':duration,'total_seconds':row.get('elapsed_seconds'),
            'postprocessing_seconds':None if duration is None else max(0,row['elapsed_seconds']-duration),
            'postprocessing_time_scope':'Approximate total-minus-generation; includes preflight/transfer overhead',
            'resolution_review':'REVIEW_REQUIRED' if (directory/'050_resolution/resolution_report.json').exists() else 'NOT_RUN_BLOCKED_BY_PIXEL_GATE' if pixel else 'NOT_APPLICABLE',
            'basic_image_qa':manifest['qa_results'] if not pixel else 'NOT_APPLICABLE',
            'aseprite':'NOT_RUN' if pixel else 'NOT_APPLICABLE','raw_png_dimensions':dimensions,
            'art_review':{'status':'REVIEW_REQUIRED','criteria':{key:'NOT_REVIEWED' for key in CRITERIA}},
            'human_approval':None,'game_ready':False,'error':manifest.get('error')})
    directory=out/'previews';directory.mkdir(exist_ok=True)
    pixel_rows=[r for r in rows if 'anima_pixelate' in r['workflow_id']]
    nonpixel_rows=[r for r in rows if 'anima_pixelate' not in r['workflow_id']]
    galleries=[gallery(pixel_rows,directory,'pixel_candidates_native_1x.png',True),gallery(nonpixel_rows,directory,'nonpixel_candidates_preview.png',False)]
    summary={'technical_counts':dict(Counter(r['technical_status'] for r in analysis)),
        'pixel_gate_counts':dict(Counter(r['pixel_gate'] for r in analysis if r['output_class']=='PIXEL_STATIC')),
        'nonpixel_basic_qa_pass':sum(r['technical_status']=='CANDIDATE_READY_REVIEW_REQUIRED' for r in analysis),
        'human_approved':0,'golden_approved':0,'automatic_art_scores':'NOT_MEASURED',
        'animation_e2e':report['current_animation_e2e'],'galleries':[g for g in galleries if g]}
    write(out/'comparison.json',{'summary':summary,'samples':analysis})
    report['comparison']=summary
    report['human_review']='REQUIRED_FOR_NEW_CANDIDATES'
    write(out/'manifest.json',report)
    write(ROOT/'docs/style/M25_STATUS.json',report)
    lines=['# M2.5 candidate comparison','', 'Original PNGs retained. Pixel gallery shows native 1x pixels. Nonpixel gallery is a preview; inspect originals for quality.', '', '| Candidate | Technical status | Pixel gate | Colors | Total seconds | Art review |','|---|---|---|---:|---:|---|']
    for r in analysis:
        lines.append(f"| {r['id']} | {r['technical_status']} | {r['pixel_gate']} | {r['unique_colors']} | {r['total_seconds']:.2f} | REQUIRED |")
    lines += ['', 'No technical result constitutes artistic approval. All seven art criteria remain NOT_REVIEWED for new candidates. Legacy sword_warrior remains NOT_APPROVED_AS_STATIC_MASTER.']
    (out/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
