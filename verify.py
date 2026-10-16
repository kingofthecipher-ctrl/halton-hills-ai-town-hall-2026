#!/usr/bin/env python3
"""Recalculate the published record without a model API or third-party packages."""
from pathlib import Path
import argparse,csv,hashlib,json,re

ROOT=Path(__file__).resolve().parent
def load(path):return json.loads((ROOT/path).read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def files():
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if not p.is_file() or any(part=='.git' or part=='work' or part=='__pycache__' or part.startswith('.venv') for part in rel.parts):continue
        if rel.as_posix()=='SHA256SUMS.json':continue
        if p.suffix in ('.mp4','.wav','.pt','.pth','.hash','.pyc') or p.name.endswith('.render-hash'):continue
        yield rel.as_posix(),p
def raw_summary(path,name):
    for line in (ROOT/path).read_text().splitlines():
        if not line.startswith('|'):continue
        cells=[c.strip().replace('**','') for c in line.split('|')[1:-1]]
        if len(cells)!=8 or cells[0]!=name:continue
        values=[]
        for cell in cells[1:]:
            numbers=re.findall(r'\d+(?:\.\d+)?',cell)
            assert numbers, (path,name,cell)
            values.append(float(numbers[-1]))
        assert abs(sum(values[:6])-values[6])<1e-9
        return values[:6],values[6]
    raise AssertionError(('No original summary row',path,name))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-manifest',action='store_true',help='Explicitly regenerate the publication checksum list after a documented edit.')
    parser.add_argument('--video',type=Path,help='Optional downloaded canonical MP4 to compare with the published checksum.')
    args=parser.parse_args()
    if args.write_manifest:
        values={name:digest(p) for name,p in files()}
        (ROOT/'SHA256SUMS.json').write_text(json.dumps(values,indent=2)+'\n')
        print('Wrote checksum list for',len(values),'published files.')

    panel=load('data/panel.json')
    common=(ROOT/'prompts/common-review-prompt.md').read_text().split('\n---\n',1)[1]
    for wrapper in ['grok-review-prompt.md','gemini-review-prompt.md']:
        assert (ROOT/('prompts/'+wrapper)).read_text().split('\n---\n',1)[1]==common,'Grading bodies differ'
    assert [int(n) for n in re.findall(r'^[1-6]\. .+? — (\d+) points',common,re.M)]==[20,20,15,15,20,10]
    prompt_record=load('data/prompt-provenance.json')
    assert hashlib.sha256(common.encode()).hexdigest()==prompt_record['common_grading_body_sha256']
    names=[r['candidate'] for r in panel['responses']]
    expected_names=['Shanna Maltby','Kevin Carruthers','Mike Albano','Jason Brass','Alex Hilson','Hillary Spurr','Anthony Galati']
    assert names==expected_names
    assert panel['weights']==[20,20,15,15,20,10]
    assert [r['key'] for r in panel['reviewers']]==['sol','astra','sonnet','opus','grok','gemini']
    changes=load('data/score-corrections.json')
    assert len(changes)==2 and {c['candidate'] for c in changes}=={'Shanna Maltby','Jason Brass'}
    expected_csv=[]
    for reviewer in panel['reviewers']:
        assert [s['candidate'] for s in reviewer['scores']]==names
        raw_path='reviews/'+reviewer['key']+'.md'
        if reviewer.get('source_sha256'):assert digest(ROOT/raw_path)==reviewer['source_sha256'],raw_path
        for score in reviewer['scores']:
            points,total=raw_summary(raw_path,score['candidate'])
            for change in changes:
                if (reviewer['key'],score['candidate'])!=(change['reviewer'],change['candidate']):continue
                i=change['criterion']-1
                assert i==1 and total==change['old_total'] and points[i]==change['old_points']
                assert change['old_level']==3.5 and change['new_level']==4
                assert change['new_points']==20
                correction=(ROOT/change['source']).read_text()
                request=(ROOT/change['request']).read_text()
                assert str(change['new_total']) in correction and 'level' in correction.lower()
                assert 'integer' in request.lower() and 'automatically round' in request.lower()
                points[i]=change['new_points'];total=sum(points)
                assert total==change['new_total']
            assert points==score['points'] and total==score['total'],(reviewer['key'],score['candidate'],'source/final mismatch')
            assert not score.get('rubric_violations')
            assert len(score['levels'])==len(score['points'])==6
            for criterion,weight,level,point in zip(panel['criteria'],panel['weights'],score['levels'],score['points']):
                assert float(level).is_integer() and 0<=level<=4
                assert level/4*weight==point
                expected_csv.append([reviewer['label'],score['candidate'],criterion,float(weight),float(level),float(point)])
    with (ROOT/'data/criterion-scores.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    actual=[[r['reviewer'],r['candidate'],r['criterion'],float(r['weight']),float(r['level']),float(r['weighted_points'])] for r in rows]
    assert actual==expected_csv and len(actual)==252
    with (ROOT/'data/totals.csv').open(newline='') as f:
        totals=list(csv.DictReader(f))
    assert [r['candidate'] for r in totals]==names
    for i,row in enumerate(totals):
        for r in panel['reviewers']:assert float(row[r['label']])==r['scores'][i]['total']

    for response in panel['responses']:
        assert digest(ROOT/response['screenshot'])==response['screenshot_sha256']
    for photo in load('production/candidate-photo-sources.json'):
        assert digest(ROOT/photo['local_path'])==photo['sha256']
    for r in load('data/model-provenance.json'):
        assert digest(ROOT/r['raw_review'])==r['raw_review_sha256']
    episode=load('production/episode.json')
    assert episode['panel']==panel
    scenes=episode['scenes'];assert len(scenes)==98
    reviews=[s for s in scenes if s['kind']=='review']
    assert len(reviews)==42 and len({(s['candidate_index'],s['speaker_index']) for s in reviews})==42
    for scene in reviews:
        score=panel['reviewers'][scene['speaker_index']]['scores'][scene['candidate_index']]
        assert scene['score']==score['total']
        assert scene['original_narration']==score['narration']
        assert (ROOT/scene['source_file']).is_file()
        if not scene.get('editorial_edit'):assert scene['narration']==score['narration']
    assert sum(bool(s.get('editorial_edit')) for s in reviews)==4
    assert sum(s['kind']=='banter' for s in scenes)==20
    assert sum(s['kind']=='advice' for s in scenes)==7
    for scene in scenes:
        if scene['kind']=='quote':assert scene['display'][1:-1] in panel['responses'][scene['candidate_index']]['transcript']
    voice=load('production/voice-manifest.json')
    assert len(voice['scenes'])==98
    for scene,item in zip(scenes,voice['scenes']):
        key=hashlib.sha256((scene['voice']+str(scene['speed'])+scene['narration']+voice['snapshot']).encode()).hexdigest()
        assert key==item['input_sha256']
    closing=load('production/closing-summary.json')
    assert [r['key'] for r in closing['races']]==['ward1','regional12','mayoral']
    assert closing['races'][0]['seats']==2
    for race in closing['races']:
        for ci,row in zip(race['candidate_indices'],race['scores']):
            assert row['candidate']==names[ci]
            assert row['reviewer_scores']=={r['label']:r['scores'][ci]['total'] for r in panel['reviewers']}
    assert [r['candidate'] for r in closing['races'][2]['ungraded']]==['Ann Lawlor','Ivan Bosnjak']

    manifest=load('SHA256SUMS.json')
    for name,expected in manifest.items():assert digest(ROOT/name)==expected,('Published hash mismatch',name)
    assert set(manifest)=={name for name,p in files()},'Published file list differs from checksum list'
    for name,path in files():
        if path.suffix not in ('.py','.md','.json','.csv','.txt','.yml'):continue
        text=path.read_text()
        assert not re.search(r'/Users/[A-Za-z0-9._-]+/',text),(name,'local user path')
        assert not re.search(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text),(name,'credential-like string')
    if args.video:
        video=load('production/video-manifest.json')
        assert args.video.stat().st_size==video['bytes']
        assert digest(args.video)==video['sha256'],'Downloaded video differs from canonical export'
        print('Released MP4 byte size and SHA-256 match.')
    print('PASS: 6 raw reviews, 42 totals, 252 integer criterion scores, 2 documented repairs, 7 screenshots, 98 scene mappings, CSVs and',len(manifest),'published file hashes.')
    print('These checks establish consistency, not unbiased or objectively correct grading.')

if __name__=='__main__':main()
