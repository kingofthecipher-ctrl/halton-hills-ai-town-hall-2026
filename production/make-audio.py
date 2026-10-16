from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import time
import numpy as np
import soundfile as sf
import torch
from kokoro import KModel,KPipeline

torch.set_num_threads(4)
base=Path(__file__).resolve().parents[1]
work=base/'work/full-episode';work.mkdir(parents=True,exist_ok=True)
scenes=json.loads((base/'production/episode.json').read_text())['scenes']
import os
from huggingface_hub import snapshot_download
snapshot=Path(os.environ['KOKORO_SNAPSHOT']) if os.environ.get('KOKORO_SNAPSHOT') else Path(snapshot_download(repo_id='hexgrad/Kokoro-82M',revision='f3ff3571791e39611d31c381e3a41a3af07b4987'))
model=KModel(repo_id='hexgrad/Kokoro-82M',config=str(snapshot/'config.json'),model=str(snapshot/'kokoro-v1_0.pth')).to('cpu').eval()
pipelines={}
audio_cache=work/'audio-cache';audio_cache.mkdir(exist_ok=True)
for old in list(work.glob('*.hash')):
    wav=old.with_suffix('.wav')
    if wav.exists() and not (audio_cache/(old.read_text()+'.wav')).exists():
        shutil.copyfile(wav,audio_cache/(old.read_text()+'.wav'))
manifest={'engine':'Kokoro','package_version':importlib.metadata.version('kokoro'),'model':'hexgrad/Kokoro-82M',
    'snapshot':snapshot.name,'model_sha256':hashlib.sha256((snapshot/'kokoro-v1_0.pth').read_bytes()).hexdigest(),
    'sample_rate':24000,'source':'https://huggingface.co/hexgrad/Kokoro-82M','scenes':[]}
for i,s in enumerate(scenes):
    target=work/f'{i:03d}.wav';stamp=target.with_suffix('.hash')
    key=hashlib.sha256((s['voice']+str(s['speed'])+s['narration']+snapshot.name).encode()).hexdigest()
    if (audio_cache/(key+'.wav')).exists():
        shutil.copyfile(audio_cache/(key+'.wav'),target);stamp.write_text(key)
        samples,rate=sf.read(target,dtype='float32');assert rate==24000
        print(f'Audio {i+1}/{len(scenes)} cached',flush=True)
    else:
        voice=snapshot/'voices'/(s['voice']+'.pt');assert voice.is_file()
        lang=s['voice'][0]
        if lang not in pipelines:pipelines[lang]=KPipeline(lang_code=lang,repo_id='hexgrad/Kokoro-82M',model=model)
        chunks=[];start=time.monotonic()
        for _,_,a in pipelines[lang](s['narration'],voice=str(voice),speed=s['speed']):
            if a is None:raise RuntimeError('Missing audio')
            if chunks:chunks.append(np.zeros(1920,dtype=np.float32))
            chunks.append(a.detach().cpu().numpy())
        assert chunks
        samples=np.concatenate(chunks)
        assert np.isfinite(samples).all() and np.sqrt(np.mean(samples**2))>0.001
        peak=np.max(np.abs(samples))
        if peak>.94:samples*=.94/peak
        sf.write(target,samples,24000,subtype='PCM_16');stamp.write_text(key)
        shutil.copyfile(target,audio_cache/(key+'.wav'))
        print(f'Audio {i+1}/{len(scenes)}: {s["speaker"]}, {len(samples)/24000:.1f}s in {time.monotonic()-start:.1f}s',flush=True)
    manifest['scenes'].append({'scene':i,'speaker':s['speaker'],'voice':s['voice'],'speed':s['speed'],
        'seconds':len(samples)/24000,'file':target.name,'input_sha256':key,
        'voice_sha256':hashlib.sha256((snapshot/'voices'/(s['voice']+'.pt')).read_bytes()).hexdigest()})
(work/'voice-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(base/'production/voice-manifest.generated.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('All episode audio ready:',round(sum(s['seconds'] for s in manifest['scenes']),1),'seconds',flush=True)
