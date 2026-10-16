from pathlib import Path
import hashlib,json,math,shutil,subprocess,sys,textwrap,wave
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont,ImageOps
import numpy as np

BASE=Path(__file__).resolve().parents[1]
WORK=BASE/'work/full-episode';WORK.mkdir(parents=True,exist_ok=True);OUT=BASE/'production'
episode=json.loads((OUT/'episode.json').read_text());panel=episode['panel'];scenes=episode['scenes']
W,H=1920,1080;FPS=24
BG='#0b171e';CARD='#142a34';SOFT='#1d3843';INK='#f0f0e6';MUTED='#a8bcc5';MINT='#a5e4cd';GOLD='#e7c581'
COLORS=['#a5e4cd','#b7b6ef','#f0b99f','#dfcb8c','#a9d3ee','#e7bad8']
FONT='/System/Library/Fonts/Avenir Next.ttc'
@lru_cache(None)
def ft(n,weight='regular'):return ImageFont.truetype(FONT,n,index={'regular':7,'medium':5,'bold':0,'demi':2}[weight])
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if p.returncode:raise RuntimeError(str(args[:4])+'\n'+p.stderr[-4000:])
 return p.stdout
def duration(p):
 with wave.open(str(p)) as f:return f.getnframes()/f.getframerate()
def lines(d,text,size,width,weight='regular'):
 result=[]
 for para in text.split('\n'):
  if not para:result.append('');continue
  line=''
  for word in para.split():
   test=(line+' '+word).strip()
   if line and d.textlength(test,font=ft(size,weight))>width:result.append(line);line=word
   else:line=test
  result.append(line)
 return result
def block(d,text,x,y,width,size=44,line=60,fill=INK,bottom=735,weight='regular'):
 wrapped=lines(d,text,size,width,weight)
 assert y+len(wrapped)*line<=bottom,(text,size,len(wrapped),y,bottom)
 for row in wrapped:d.text((x,y),row,font=ft(size,weight),fill=fill);y+=line
 return y
def center(d,text,x,y,size=30,fill=INK,weight='regular'):
 d.text((x-d.textlength(text,font=ft(size,weight))/2,y),text,font=ft(size,weight),fill=fill)
def fmt(n):return f'{n:g}'

@lru_cache(None)
def robot(index,size=340,closed=False):
 # Original code-drawn robot cast: different silhouettes, antennae and chest marks.
 im=Image.new('RGBA',(340,330),(0,0,0,0));d=ImageDraw.Draw(im)
 c=COLORS[index] if index is not None else MINT;i=index if index is not None else 6
 d.ellipse((40,275,300,312),fill=(0,0,0,60))
 d.rounded_rectangle((94,220,246,298),25,fill='#203e4a',outline=c,width=3)
 d.line((100,239,65,272),fill=c,width=13);d.ellipse((48,259,80,291),fill='#203e4a',outline=c,width=3)
 d.line((240,239,275,272),fill=c,width=13);d.ellipse((260,259,292,291),fill='#203e4a',outline=c,width=3)
 d.rounded_rectangle((108,265,155,305),12,fill='#18313d',outline=c,width=2)
 d.rounded_rectangle((185,265,232,305),12,fill='#18313d',outline=c,width=2)
 d.line((170,26,170,3),fill=c,width=5);d.ellipse((160,0,180,19),fill=c)
 if i in (0,3):
  d.polygon([(65,46),(110,26),(245,26),(277,63),(277,188),(245,223),(92,223),(65,190)],fill='#294954',outline=c,width=4)
 elif i in (1,5):d.ellipse((55,24,285,230),fill='#294954',outline=c,width=4)
 else:d.rounded_rectangle((59,30,281,224),38 if i==2 else 15,fill='#294954',outline=c,width=4)
 d.rounded_rectangle((80,71,260,187),25,fill='#0b1922')
 for ex in (124,216):
  if closed:d.line((ex-15,109,ex+15,109),fill=c,width=6)
  elif i==3:d.rounded_rectangle((ex-13,94,ex+13,123),5,fill=c)
  elif i==4:d.polygon([(ex-15,100),(ex+14,93),(ex+10,122),(ex-13,122)],fill=c)
  else:d.ellipse((ex-13,96,ex+13,122),fill=c)
 d.line((132,155,208,155),fill=c,width=4)
 label=['SOL','ASTRA','SONNET','OPUS','GROK','GEMINI','HOST'][i]
 center(d,label,170,235,18,c,'demi')
 if i==1:d.arc((48,15,292,240),190,350,fill=c,width=3)
 if i==5:d.ellipse((282,36,300,54),fill=c)
 if size!=340:im=im.resize((size,round(size*330/340)),Image.Resampling.LANCZOS)
 return im

assets=WORK/'assets';assets.mkdir(exist_ok=True)
for i in range(7):
 robot(i if i<6 else None,300).save(assets/f'robot-{i}.png')
 robot(i if i<6 else None,300,closed=True).save(assets/f'robot-{i}-blink.png')
Image.new('RGBA',(4,4),(0,0,0,0)).save(assets/'blank.png')

photo_file=OUT/'candidate-photo-sources.json'
photos=json.loads(photo_file.read_text()) if photo_file.exists() else []
photo_by={p['candidate']:p for p in photos}
def portrait(canvas,name,box):
 x,y,w,h=box
 p=photo_by.get(name)
 if p and Path(p['local_path']).exists():
  image=Image.open(p['local_path']).convert('RGB')
  # Contain the complete portrait; no face edits or invented expressions.
  image=ImageOps.contain(image,(w,h),Image.Resampling.LANCZOS)
  canvas.paste(image,(x+(w-image.width)//2,y+(h-image.height)//2))
 else:
  d=ImageDraw.Draw(canvas);d.rounded_rectangle((x,y,x+w,y+h),18,fill=SOFT)
  center(d,''.join(n[0] for n in name.split()),x+w/2,y+h/2-35,56,MINT,'demi')

background=Image.new('RGB',(W,H),BG)
bd=ImageDraw.Draw(background)
for y in range(H):
 k=max(0,1-abs(y-460)/650);color=(int(11+7*k),int(23+12*k),int(30+15*k))
 bd.line((0,y,W,y),fill=color)
for x in range(0,W,120):bd.line((x,110,x,780),fill='#17313e',width=1)
bd.ellipse((-300,740,2220,1290),fill='#102630',outline='#36535d',width=2)
bd.line((60,110,1860,110),fill='#547478',width=1)
bd.line((60,1028,1860,1028),fill='#3a5661',width=1)

def scorecards(im,s,defer=False,plate=None):
 d=ImageDraw.Draw(im);ci=s['candidate_index']
 for i,r in enumerate(panel['reviewers']):
  x=60+i*302;active=s.get('speaker_index')==i
  d.rounded_rectangle((x,817,x+288,1005),20,fill='#25434b' if active else CARD,
      outline=COLORS[i] if active else '#2b4752',width=3 if active else 1)
  im.paste(robot(i,88),(x+10,849),robot(i,88))
  d.text((x+105,842),r['label'],font=ft(22,'demi'),fill=INK)
  value='—';issue=False
  if ci is not None and i<s['reveal']:
   row=r['scores'][ci];value=fmt(row['total']);issue=bool(row.get('rubric_violations'))
   if issue:value+='*'
  target=ImageDraw.Draw(plate) if defer and active else d
  target.text((x+105,883),value,font=ft(44,'demi'),fill=COLORS[i] if active else INK)
  d.text((x+106,946),'RUBRIC NOTE' if issue else ('OUT OF 100' if value!='—' else 'SAVED REVIEW'),font=ft(16,'medium'),fill=GOLD if issue else MUTED)

def frame(s):
 im=background.copy();d=ImageDraw.Draw(im)
 plate=Image.new('RGBA',(W,H),(0,0,0,0));pd=ImageDraw.Draw(plate)
 kind=s['kind'];ci=s['candidate_index'];ri=s.get('speaker_index');actor=kind in ('review','banter','method','rubric','findings','closing','credits','advice')
 d.text((60,37),'AI TOWN HALL',font=ft(32,'demi'),fill=INK)
 d.text((1490,43),'HALTON HILLS  /  2026',font=ft(22,'medium'),fill=MUTED)
 if kind=='banter':kicker='AI-WRITTEN SCRIPTED BANTER · NOT A LIVE PANEL EXCHANGE'
 elif kind=='review':kicker='EDITED SAVED REVIEW SUMMARY' if s.get('editorial_edit') else 'SAVED REVIEW SUMMARY · VERBATIM'
 elif kind=='quote':kicker='CANDIDATE EXCERPT · SYNTHETIC NARRATION'
 else:kicker=s.get('kicker','ONE QUESTION · SEVEN SUPPLIED REPLIES')
 d.text((60,145),kicker,font=ft(21,'demi'),fill=GOLD if kind=='banter' else MINT)
 heading=panel['responses'][ci]['candidate'] if ci is not None else s['title']
 d.text((60,190),heading,font=ft(56,'demi'),fill=INK)
 if ci is not None:d.text((1530,197),'CLOSING ADVICE' if kind=='advice' else f'CHAPTER {ci+1} OF 7',font=ft(24,'medium'),fill=MUTED)
 d.rounded_rectangle((60,288,1390,779),22,fill=CARD)
 d.rounded_rectangle((1420,288,1860,779),22,fill=CARD)
 if actor:
  label=s['speaker'];color=COLORS[ri] if ri is not None else MINT
  center(d,label,1640,305,30,color,'demi')
  if kind!='review':center(d,'SYNTHESIS NARRATOR' if kind=='advice' else 'SYNTHETIC STUDIO NARRATOR',1640,714,17,MUTED)
 if kind=='review':
  d.text((100,315),'WHAT THE REPLY DEMONSTRATES',font=ft(20,'medium'),fill=MUTED)
  block(d,s['display'],100,350,1245,size=40,line=54,bottom=737)
  value=fmt(s['score'])+('*' if s.get('rubric_exception') else '')
  center(pd,value,1620,650,85,GOLD if s.get('rubric_exception') else color,'demi')
  d.text((1760,714),'/100',font=ft(25),fill=MUTED)
  if s.get('rubric_exception'):d.text((100,748),'* Grok: criterion 2 implies level 3.5; submitted total retained.',font=ft(20,'medium'),fill=GOLD)
 elif kind=='banter':
  d.text((100,316),s['speaker'].upper(),font=ft(22,'demi'),fill=COLORS[ri])
  block(d,s['display'],100,385,1210,size=63,line=86,bottom=731,weight='medium')
  d.text((100,747),'Written by Codex for this video. The saved scores do not change.',font=ft(22),fill=GOLD)
 elif kind=='quote':
  d.text((100,316),s['topic'].upper(),font=ft(22,'medium'),fill=MINT)
  block(d,s['display'],100,385,1215,size=46,line=63,bottom=727)
  portrait(im,heading,(1444,315,392,399))
  credit=photo_by.get(heading,{}).get('display_credit','Supplied screenshot')
  center(d,credit,1640,733,19,MUTED)
 elif kind=='findings':
  d.text((100,321),'COMMON STRENGTH',font=ft(21,'demi'),fill=MINT)
  block(d,s['strength'],100,361,1200,49,66,bottom=495,weight='medium')
  d.text((100,522),'MAIN GAP',font=ft(21,'demi'),fill=GOLD)
  block(d,s['gap'],100,562,1200,49,66,bottom=705,weight='medium')
  values=[r['scores'][ci]['total'] for r in panel['reviewers']]
  d.text((100,738),f'Reviewer score range: {fmt(min(values))}–{fmt(max(values))}  / 100',font=ft(23),fill=MUTED)
 elif kind=='advice':
  block(d,s['advice_title'],100,320,1210,size=40,line=54,bottom=440,weight='demi',fill=MINT)
  block(d,s['display'],100,465,1200,size=44,line=63,bottom=725)
  d.text((100,748),'Based on saved reviews · Scores unchanged · No new candidate questions',font=ft(22),fill=MUTED)
 elif kind=='rubric':
  for i,(name,weight) in enumerate(zip(panel['criteria'],panel['weights'])):
   x=100+(i%2)*630;y=323+(i//2)*133
   block(d,name,x,y,490,29,39,bottom=y+82,weight='medium')
   d.text((x+503,y+7),str(weight),font=ft(42,'demi'),fill=MINT)
   d.rounded_rectangle((x,y+91,x+555,y+99),4,fill=SOFT)
   d.rounded_rectangle((x,y+91,x+int(555*weight/20),y+99),4,fill=MINT)
  d.text((100,748),'Integer level ÷ 4 × category weight = points',font=ft(25),fill=INK)
 elif kind in ('method','closing'):
  block(d,s['display'],100,340,1215,size=43,line=64,bottom=738)
 elif kind=='credits':
  credits=[('Sol 6.1','Explicit gpt-6.1-sol run'),('Astra','Explicit gpt-6-astra run'),('Sonnet + Opus','5.5 labels reported by user'),('Grok','Version / mode unrecorded'),('Gemini','2.5 Flash / Standard label from submission'),('Voice / music','Kokoro stock voices / original synth cues'),('Script / synthesis','AI-written by Codex from saved reviews')]
  for i,(a,b) in enumerate(credits):
   y=317+i*67;d.text((100,y),a,font=ft(28,'demi'),fill=MINT);d.text((420,y),b,font=ft(27),fill=INK)
 elif kind in ('candidates','cast','opener','comparison','race','scenarios'):
  actor=False
  # These scenes use the full stage instead of the two speech panels.
  d.rectangle((59,287,1861,1007),fill=BG)
  if kind=='candidates':
   for i,r in enumerate(panel['responses']):
    x=60+i*258
    d.rounded_rectangle((x,327,x+244,867),18,fill=CARD)
    portrait(im,r['candidate'],(x+8,340,228,330))
    block(d,r['candidate'],x+16,704,212,31,43,bottom=810,weight='demi')
    d.text((x+16,826),'SUPPLIED REPLY '+str(i+1),font=ft(17),fill=MUTED)
   d.text((60,935),'Screenshot order · These are the replies supplied for this project, not the whole ballot.',font=ft(27),fill=MUTED)
  elif kind=='cast':
   for i,r in enumerate(panel['reviewers']):
    x=60+i*302
    face=robot(i,280);im.paste(face,(x+4,360),face)
    center(d,r['label'],x+144,693,30,COLORS[i],'demi')
    center(d,'STOCK SYNTHETIC VOICE',x+144,748,17,MUTED)
   center(d,'Six saved assessments. Six original robot characters.',960,900,40,INK,'medium')
  elif kind=='race':
   race=s['race'];xs=[720,925,1130,1335,1540,1745]
   d.text((85,304),'SUPPLIED REPLY',font=ft(23,'medium'),fill=MUTED)
   for i,r in enumerate(panel['reviewers']):center(d,r['label'],xs[i],304,24,COLORS[i],'demi')
   rows=race['candidate_indices'];ungraded=race.get('ungraded',[])
   for idx,ci2 in enumerate(rows):
    y=370+idx*107
    d.rounded_rectangle((60,y-8,1860,y+92),12,fill=CARD)
    name=panel['responses'][ci2]['candidate'];portrait(im,name,(76,y,100,80))
    d.text((200,y+18),name,font=ft(35,'demi'),fill=INK)
    for ri2,r in enumerate(panel['reviewers']):center(d,fmt(r['scores'][ci2]['total']),xs[ri2],y+15,39,INK,'medium')
   for idx,row in enumerate(ungraded):
    y=505+idx*130
    d.rounded_rectangle((60,y-8,1860,y+104),12,fill=CARD)
    d.text((86,y+10),row['candidate'],font=ft(35,'demi'),fill=INK)
    d.text((86,y+61),'No reply reported by organiser',font=ft(23),fill=MUTED)
    for x in xs:center(d,'Ungraded',x,y+23,25,MUTED)
   takeaway_y=842 if len(rows)==4 else 812
   block(d,race['takeaway'],85,takeaway_y,1730,size=37,line=50,bottom=945,weight='medium',fill=MINT)
   d.text((85,925),'Official roster: haltonhills.ca/filed-nominations · 15 Oct 2026',font=ft(23),fill=MUTED)
   d.text((85,965),'Reply scores /100 · No panel average · No election prediction',font=ft(23),fill=MUTED)
  elif kind=='scenarios':
   for i,item in enumerate(s['scenarios']):
    x=60+i*606
    d.rounded_rectangle((x,327,x+585,850),22,fill=CARD)
    d.text((x+32,354),f'0{i+1}',font=ft(65,'demi'),fill=MINT)
    block(d,item['title'],x+32,456,515,size=44,line=60,bottom=587,weight='demi')
    block(d,item['body'],x+32,621,513,size=33,line=47,bottom=831)
   center(d,'Different paths. Named actions. A funded fallback.',960,918,41,INK,'medium')
   center(d,'Planning advice from saved reviews · These are scenarios, not forecasts.',960,967,23,MUTED)
  elif kind=='comparison':
   xs=[562,794,1026,1258,1490,1722]
   for i,r in enumerate(panel['reviewers']):center(d,r['label'],xs[i],313,25,COLORS[i],'demi')
   for ci2,r in enumerate(panel['responses']):
    y=384+ci2*72
    if ci2%2==0:d.rounded_rectangle((60,y-6,1860,y+60),10,fill=CARD)
    d.text((85,y),r['candidate'],font=ft(31,'medium'),fill=INK)
    for ri2,reviewer in enumerate(panel['reviewers']):
     row=reviewer['scores'][ci2];v=fmt(row['total'])+('*' if row.get('rubric_violations') else '')
     center(d,v,xs[ri2],y,35,GOLD if row.get('rubric_violations') else INK,'medium')
   d.text((65,934),'Six reviewers · Seven supplied replies · Same rubric · Each score out of 100.',font=ft(24),fill=MINT)
   d.text((65,967),'Scores assess supplied replies. No panel average. Reviewer range is not a confidence interval.',font=ft(23),fill=MUTED)
  else:
   d.text((65,300),'AI TOWN HALL',font=ft(126,'demi'),fill=INK)
   d.text((70,462),'THE FUTURE IS LOCAL.',font=ft(64,'medium'),fill=MINT)
   d.text((75,576),'Seven replies. Six AI reviewers. One local budget.',font=ft(40),fill=MUTED)
   for i in range(6):
    face=robot(i,200);im.paste(face,(65+i*302,723),face)
    center(d,panel['reviewers'][i]['label'],165+i*302,939,27,COLORS[i],'demi')
 if kind not in ('candidates','cast','opener','comparison','race','scenarios'):scorecards(im,s,defer=kind=='review',plate=plate)
 footer='Synthetic robot cast · Saved response assessments · Scripted banter is labelled'
 d.text((60,1040),footer,font=ft(21),fill=MUTED)
 d.text((1635,1040),'ONE ASSESSMENT',font=ft(20,'medium'),fill=MUTED)
 image_path=WORK/f'{s["id"]:03d}.png';im.save(image_path)
 plate_path=WORK/f'{s["id"]:03d}-score.png';plate.save(plate_path)
 return image_path,plate_path,actor

def cue(s,length):
 rate=24000;n=round(length*rate);t=np.arange(n)/rate;a=np.zeros(n,dtype=np.float64)
 if s['kind']=='review':
  start=.45;tt=t-start;env=np.where(tt>=0,np.exp(-tt*13),0)
  a+=(np.sin(2*np.pi*660*tt)+.45*np.sin(2*np.pi*990*tt))*env*.018
 elif s['kind'] in ('opener','quote','cast','candidates','race','scenarios'):
  # An original low-volume cinematic cue; no third-party music.
  for freq in (110,164.8138,220):
   env=np.minimum(t/1.2,1)*np.minimum(np.maximum(8.5-t,0)/2,1)
   a+=np.sin(2*np.pi*freq*t)*env*.011
  for start,freq in ((.1,220),(.8,261.626),(1.5,329.628),(2.2,440)):
   tt=t-start;env=np.where(tt>=0,np.exp(-tt*2.8),0)
   a+=np.sin(2*np.pi*freq*tt)*env*.025
 path=WORK/f'{s["id"]:03d}-cue.wav'
 with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((np.clip(a,-1,1)*32767).astype('<i2').tobytes())
 return path

def srt_stamp(t):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
def clock(t):
 seconds=int(t);m,s=divmod(seconds,60);h,m=divmod(m,60)
 return f'{h:02d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'

preview='--preview' in sys.argv
if preview:
 for idx in range(len(scenes)):
  if idx<len(scenes):frame(scenes[idx])
 print('Preview images prepared.');sys.exit()

segments=[];captions=[];chapters=[(0,'Opening, introductions and methods')];offset=0.;timings=[]
for s in scenes:
 i=s['id'];audio=WORK/f'{i:03d}.wav';seconds=duration(audio);length=math.ceil((seconds+.52)*FPS)/FPS
 png,plate,actor=frame(s);actor_id=s['speaker_index'] if s['speaker_index'] is not None else 6
 actor_path=assets/f'robot-{actor_id}.png' if actor else assets/'blank.png'
 blink_path=assets/f'robot-{actor_id}-blink.png' if actor else assets/'blank.png'
 music=cue(s,length);target=WORK/f'{i:03d}.mp4'
 signature=hashlib.sha256(png.read_bytes()+plate.read_bytes()+audio.read_bytes()+Path(__file__).read_bytes()).hexdigest()
 marker=target.with_suffix('.render-hash')
 if not target.exists() or not marker.exists() or marker.read_text()!=signature:
  # Floating head/body, timed blinking, and speech-driven mouth line animate each cast member.
  vf='[1:a]loudnorm=I=-18:TP=-1.5:LRA=11,apad=pad_dur=0.52,asplit=2[voice][mouth];'
  vf+='[voice][5:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a];'
  vf+='[3:v]format=rgba,fade=t=in:st=0.45:d=0.3:alpha=1[score];[0:v][score]overlay=0:0[p];'
  if actor:
   vf+='[p][2:v]overlay=x=1490:y=360+3*sin(t*3.5)[r];'
   vf+=r'[r][4:v]overlay=x=1490:y=360+3*sin(t*3.5):enable=lt(mod(t+1.2\,4.3)\,0.12)[b];'
   vf+='[mouth]showwaves=s=68x16:mode=line:colors=0xa5e4cd:r=24:draw=full,format=rgba[m];'
   vf+='[b][m]overlay=x=1606:y=489+3*sin(t*3.5)[v0];'
  else:
   vf+='[mouth]showwaves=s=1180x18:mode=line:colors=0xa5e4cd:r=24:draw=full,format=rgba[m];[p][m]overlay=90:1001[v0];'
  vf+=f'[v0]fade=t=in:st=0:d=0.14,fade=t=out:st={length-.16:.4f}:d=0.16,format=yuv420p[v]'
  args=['ffmpeg','-hide_banner','-loglevel','error','-y','-threads','4','-filter_complex_threads','2',
   '-loop','1','-framerate',str(FPS),'-i',str(png),'-i',str(audio),'-loop','1','-framerate',str(FPS),'-i',str(actor_path),
   '-loop','1','-framerate',str(FPS),'-i',str(plate),'-loop','1','-framerate',str(FPS),'-i',str(blink_path),'-i',str(music),
   '-filter_complex',vf,'-map','[v]','-map','[a]','-t',str(length),'-c:v','libx264','-preset','veryfast','-crf','22',
   '-threads','4','-r',str(FPS),'-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-ac','1',str(target)]
  run(args);marker.write_text(signature)
 segments.append(target)
 if s.get('chapter_start'):chapters.append((offset,panel['responses'][s['candidate_index']]['candidate']))
 if s['kind']=='comparison':chapters.append((offset,'All scores and closing findings'))
 if s.get('chapter_title'):chapters.append((offset,s['chapter_title']))
 chunks=textwrap.wrap(s['narration'],width=85,break_long_words=False);units=sum(len(c) for c in chunks);at=offset
 for chunk in chunks:
  span=seconds*len(chunk)/units;captions.append((at,at+span,chunk));at+=span
 timings.append({'scene':i,'start':offset,'duration':length,'kind':s['kind'],'speaker':s['speaker'],'title':s['title']})
 offset+=length
 print(f'Rendered {i+1}/{len(scenes)} · {s["kind"]} · {s["speaker"]} · total {clock(offset)}',flush=True)

srt=OUT/'ai-town-hall-full-episode.srt'
srt.write_text('\n\n'.join(f'{i+1}\n{srt_stamp(a)} --> {srt_stamp(b)}\n{textwrap.fill(t,45)}' for i,(a,b,t) in enumerate(captions))+'\n')
concat=WORK/'concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in segments))
joined=WORK/'joined.mp4';run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(joined)])
metadata=WORK/'chapters.ffmetadata'
meta=[';FFMETADATA1','title=AI Town Hall — Halton Hills','comment=One assessment of original replies. AI-written script by Codex. Synthetic cast; banter is not a live panel exchange.']
for i,(start,title) in enumerate(chapters):
 end=chapters[i+1][0] if i+1<len(chapters) else offset
 meta+=['[CHAPTER]','TIMEBASE=1/1000',f'START={round(start*1000)}',f'END={round(end*1000)}','title='+title]
metadata.write_text('\n'.join(meta)+'\n')
target=OUT/'ai-town-hall-full-episode.mp4'
run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(joined),'-i',str(srt),'-i',str(metadata),
 '-map','0:v','-map','0:a','-map','1:0','-map_metadata','2','-map_chapters','2','-c:v','copy','-c:a','copy','-c:s','mov_text',
 '-metadata:s:s:0','language=eng','-movflags','+faststart',str(target)])
(OUT/'ai-town-hall-chapters.md').write_text('# AI Town Hall — chapter guide\n\n'+ '\n'.join(f'{clock(t)} {name}' for t,name in chapters)+'\n')
(WORK/'timings.json').write_text(json.dumps(timings,indent=2)+'\n')
(OUT/'ai-town-hall-full-timings.json').write_text(json.dumps(timings,indent=2)+'\n')
shutil.copyfile(WORK/'000.png',OUT/'ai-town-hall-full-poster.png')
print('FULL EPISODE READY',target,'duration',offset,'bytes',target.stat().st_size,flush=True)
