"""Transkribus-Noten und Text geometrisch paaren und in common-gabc ausgeben.

Aufruf: nice -n 19 python skripte/gabc_transkribus.py {stufe2|pakete}
"""
import sys, re, json, math, textwrap, importlib.util, sqlite3, itertools, string
from pathlib import Path
from collections import Counter, defaultdict
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE / 'skripte'), str(HERE / 'LightOnOCR-3-1B'), '', '']
import gabc_zeilen as G
import systeme_pagexml as S
from silben_cantus import silben
from transkribus_index import QUELLEN
from gabcparser import GabcParser
PARSER = GabcParser.load_parser('common-gabc')
NAMES = ('brlm33', 'brlm34', 'mb2', 'vor259')
NS = S.NS

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def jsonl(path, items):
    path.write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in items), encoding='utf-8')
def split_text(text):
    # Die Hilfsfunktion normalisiert j/v und Großschreibung; nur ihre Schnittpositionen übernehmen.
    out=[]; prev=0
    for m in re.finditer(r'[^\W\d_]+', text, re.UNICODE):
        word=m.group(); parts=silben(word)
        if not parts or sum(map(len, parts)) != len(word):
            raise ValueError('Wort nicht verlustfrei silbierbar: '+word)
        pos=0
        for i, part in enumerate(parts):
            end=pos+len(part)
            pre=text[prev:m.start()] if i == 0 else ''
            out.append({'text': pre+word[pos:end], 'wortbeginn': i == 0})
            pos=end; prev=m.start()+end
    if out: out[-1]['text'] += text[prev:]
    return out

def gruppen(label):
    # Steuerzeichen bleiben an ihrer ursprünglichen Position; nur tonhaltige Kommagruppen zählen.
    out=[]; prefix=[]
    for raw in label.split(','):
        t=raw.split(); has=any(x in G.BUCHSTABE for x in t)
        if has:
            out.append(prefix+t); prefix=[]
        elif out: out[-1].extend(t)
        else: prefix.extend(t)
    if prefix and out: out[-1].extend(prefix)
    return out

def musik(gr, syllables):
    result=[]; current=[]; text=None; previous_group=False
    def close():
        nonlocal current, text
        if current:
            result.append((text or '', ''.join(current))); current=[]; text=None
    for gi, toks in enumerate(gr):
        si=gi if len(syllables)>1 else 0
        if gi == 0 or len(syllables)>1:
            close(); text=syllables[si]['text']
        elif current: current.append('<m>!')
        for token in toks:
            token=G.ein_schluessel(token)
            if G.SCHLUESSEL.fullmatch(token):
                close(); result.append(('', '<m>'+token[0]+'<m>'+token[1:]));
                if text is None and not any(x[0] for x in result): text=syllables[si]['text']
            elif token == '!':  # Neumengrenze innerhalb einer Silbe (gabc_transkribus_bild.py)
                if current: current.append('<m>!')
            elif token == 'L':
                close(); result.append(('', '<m>:'))
            elif token.startswith('cu_'): pass
            elif token.startswith(('b_', 'na_')):
                kind,p=token.split('_',1)
                if p not in G.BUCHSTABE or G.BUCHSTABE[p] not in 'abcdefghijklm': raise ValueError(token)
                current.extend(('<m>'+G.BUCHSTABE[p], '<m>'+('x' if kind=='b' else 'y')))
            elif token in G.BUCHSTABE and G.BUCHSTABE[token] in 'abcdefghijklm': current.append('<m>'+G.BUCHSTABE[token])
            else: raise ValueError('Unbekanntes Token '+token)
    close()
    # Wortabstände sind in den Silbentexten erhalten. Nach losen Zeichen muss ein Abstand stehen.
    out=''
    for t,m in result:
        if not t and out and not out.endswith(' '): out+=' '
        out+=t+'('+m+')'
    out=re.sub(r'^(\(<m>[cf]<m>\d\))(?=\S)',r'\1 ',out)
    out=re.sub(r'(?<!\s)(\(<m>:(?:<m>:)?\))',r' \1',out)
    return out

def norm(w):
    return w.lower().replace('v', 'u').replace('j', 'i')

def cantus_lexikon():
    db=sqlite3.connect(f"file:{ROOT / 'cantus_database.sqlite'}?mode=ro",uri=True)
    words=set(); bigrams=Counter()
    for record in db.execute('SELECT fulltext_ms, fulltext_standardized FROM chants'):
        for text in record:
            if not text: continue
            ws=[norm(w) for w in re.findall(r'[^\W\d_]+',text, re.UNICODE)]
            words.update(ws); bigrams.update(zip(ws,ws[1:]))
    db.close()
    return words,bigrams

def initiale_entscheiden(text, words, bigrams, buchstaben):
    matches=list(re.finditer(r'[^\W\d_]+',text,re.UNICODE))
    if not matches: return dict(text_alt=text,text_neu=text,kandidaten=[],belege={},entschieden='nein',grund='kein Wort')
    first=matches[0]; word=first.group(); rest=norm(word)
    # Normgleiche Buchstaben nur einmal prüfen; Schreibung aus der Quelle.
    prefletters=[c for c in string.ascii_lowercase if c not in 'jv']
    if buchstaben['v']>buchstaben['u']: prefletters[prefletters.index('u')]='v'
    following=norm(matches[1].group()) if len(matches)>1 else None
    after_two=norm(matches[2].group()) if len(matches)>2 else None
    candidates=[]
    def add(prefix, merge):
        if merge and (len(matches)<2 or text[first.end():matches[1].start()].strip()): return
        suffix=word+(matches[1].group() if merge else '')
        candidate=prefix.capitalize()+suffix
        if norm(candidate) not in words: return
        nextword=after_two if merge else following
        candidates.append(dict(text=candidate,praefix=prefix,verschmolzen=merge,
                               belege=bigrams[(norm(candidate),nextword)] if nextword else 0))
    for letter in prefletters:
        add(letter,False); add(letter,True)
    single=list(candidates)
    for letters in itertools.product(prefletters,repeat=2):
        add(''.join(letters),False); add(''.join(letters),True)
    if single:
        best=max(c['belege'] for c in single)
        candidates=[c for c in candidates if len(c['praefix'])==1 or c['belege']>=max(1,3*best)]
    if rest in words:
        candidates.append(dict(text=word,praefix='',verschmolzen=False,
                               belege=bigrams[(rest,following)] if following else 0))
    # Ein normalisierter Kandidat zählt einmal; verschmolzene und unverschmolzene
    # Lesungen mit demselben Ergebnis sind auch eine einzige Alternative.
    unique={}
    for c in candidates:
        key=(norm(c['text']),c['verschmolzen'])
        if key not in unique or c['belege']>unique[key]['belege']: unique[key]=c
    candidates=list(unique.values()); ranked=sorted(candidates,key=lambda c:(-c['belege'],c['text']))
    selected=None
    if ranked:
        high=ranked[0]['belege']; second=ranked[1]['belege'] if len(ranked)>1 else 0
        if high>=1 and high>=3*second and high>second: selected=ranked[0]
        elif high==0 and len(ranked)==1: selected=ranked[0]
    added=bool(selected and selected['praefix'])
    end=matches[1].end() if added and selected['verschmolzen'] else first.end()
    new=text[:first.start()]+selected['text']+text[end:] if added else text
    evidence={c['text']+(' [Wörter verbunden]' if c['verschmolzen'] else ''):c['belege'] for c in candidates}
    return dict(text_alt=text,text_neu=new,kandidaten=list(evidence),belege=evidence,entschieden='ja' if added else 'nein',grund=('ergänzt' if added else 'unverändertes Wort bevorzugt' if selected else 'keine eindeutige Entscheidung'),naechstes_wort=matches[1].group() if following else None,praefix=selected['praefix'].capitalize() if added else '',woerter_verbunden=bool(added and selected['verschmolzen']))

def run():
 words,bigrams=cantus_lexikon()
 for name in NAMES:
    target=HERE/'daten/cantus_gabc'/name; target.mkdir(parents=True,exist_ok=True)
    (target/'bilder').mkdir(exist_ok=True)
    cfg=QUELLEN[name]; export=HERE/cfg['export']
    rows=[json.loads(s) for s in (HERE/'daten'/name/'music/index.jsonl').read_text().splitlines()]
    low, high = (80, 110) if name == 'mb2' else (1, 27) if name == 'vor259' else (1, 30)
    rows = [r for r in rows if low <= int(r['id'].split('_')[0]) <= high and r.get('label')]
    bypage=defaultdict(list)
    for row in rows: bypage[row['id'].split('_')[0]].append(row)
    counts=Counter(zeilen=len(rows)); output=[]; locations=[]; pending=[]; initialen=[]
    xmls={p.stem[:4]:p for p in (export/'page').glob('*.xml')}
    buchstaben=Counter()
    for pid in bypage:
        if pid not in xmls: continue
        page_root=ET.parse(xmls[pid]).getroot()
        for reg in page_root.iter(NS+'TextRegion'):
            if not re.search(r'type:text(?:[;}]|$)',reg.get('custom','')): continue
            for u in reg.findall('./'+NS+'TextLine/'+NS+'TextEquiv/'+NS+'Unicode'):
                buchstaben.update((u.text or '').lower())
    for pageid, entries in sorted(bypage.items()):
        if pageid not in xmls: counts['xml_fehlt']+=len(entries); continue
        root=ET.parse(xmls[pageid]).getroot(); page=root.find(NS+'Page')
        notes=S.regionen(root,'notation'); systems=S.zeilen_bilden(notes)
        texts=[]
        for reg in root.iter(NS+'TextRegion'):
            m=re.search(r'type:([^;}]+)',reg.get('custom',''))
            if not m or m[1].strip()!='text': continue
            lines=[''.join(u.itertext()) for line in reg.findall(NS+'TextLine') for u in line.findall('./'+NS+'TextEquiv/'+NS+'Unicode')]
            txt=' '.join(t.strip() for t in lines if t.strip())
            if txt: texts.append((S.rechteck(reg),txt))
        texts.sort(key=lambda t:(t[0][1],t[0][0]))
        initial_boxes=[S.rechteck(r) for r in root.iter(NS+'TextRegion') if re.search(r'type:initiale_(?:lombarde|fleuro_lombarde|cadelle|historisch)(?:[;}]|$)',r.get('custom',''))]
        matches=[]
        for i,z in enumerate(systems):
            found=S.text_unter(z,[t[0] for t in texts],systems[i+1][1] if i+1<len(systems) else None)
            matches.append([j for j,t in enumerate(texts) if t[0] in found])
        # Nur bei gleich großer Restmenge eindeutige Lesereihenfolge als Rückfall.
        used=Counter(j for m in matches for j in m)
        for i,m in enumerate(matches): matches[i]=[j for j in m if used[j]==1]
        free_s=[i for i,m in enumerate(matches) if not m]; taken={j for m in matches for j in m}; free_t=[j for j in range(len(texts)) if j not in taken]
        if free_s and len(free_s)==len(free_t):
            for i,j in zip(free_s,free_t): matches[i]=[j]
        imagepath=export/page.get('imageFilename')
        if not imagepath.exists(): counts['seite_fehlt']+=len(entries); continue
        im=Image.open(imagepath).convert('RGB'); crops=S.systeme(root,*im.size)
        allregions=sorted(notes,key=lambda b:(b[1],b[0]))
        # Je System genau ein Datensatz; alle Teilregionen müssen im GT-Index vorliegen.
        byregion={tuple(r['region']):r for r in entries}
        merged=[]
        for z in systems:
            parts=sorted(z[5],key=lambda b:b[0])
            present=[byregion[p] for p in parts if p in byregion]
            if not present: continue
            if len(present)!=len(parts): counts['teil_gt_fehlt']+=len(present); continue
            if len({r['split'] for r in present})!=1: counts['teil_split_konflikt']+=len(present); continue
            row=dict(present[0]); row['label']=' , '.join(r['label'] for r in present)
            row['teile']=len(parts); row['_regionen']=parts
            row['region']=[min(x[0] for x in parts),min(x[1] for x in parts),max(x[2] for x in parts),max(x[3] for x in parts)]
            merged.append(row)
        counts['systeme']+=len(merged)
        for row in merged:
            region=tuple(row['region']); inds=[i for i,z in enumerate(systems) if tuple(row['_regionen'][0]) in z[5]]
            if len(inds)!=1: counts['region_fehlt']+=1; continue
            i=inds[0]; z=systems[i]
            if not matches[i]: counts['ohne_text']+=1; continue
            text=' '.join(texts[j][1] for j in sorted(matches[i],key=lambda j:(texts[j][0][1],texts[j][0][0])))
            text_box=texts[sorted(matches[i],key=lambda j:(texts[j][0][1],texts[j][0][0]))[0]][0]
            d=row['d']
            initial_matches=[b for b in initial_boxes if min(b[3],text_box[3])>max(b[1],text_box[1]) and b[2]<=text_box[0]+0.5*d]
            if initial_matches:
                decision=initiale_entscheiden(text,words,bigrams,buchstaben)
                decision=dict(id=row['id'],**decision,initialregionen=initial_matches,textregion=text_box)
                initialen.append(decision); counts['initiale']+=1
                if decision['entschieden']=='ja': counts['initiale_ergaenzt']+=1
                else: counts['initiale_unsicher']+=1
                text=decision['text_neu']
            try: syll=split_text(text); groups=gruppen(row['label'])
            except (ValueError,KeyError): counts['unbrauchbar']+=1; continue
            if not syll or not groups: counts['leer']+=1; continue
            counts['gepaart']+=1
            if row['teile']>1: counts['gepaart_mehrteilig']+=1
            image=target/'bilder'/(row['id']+'.jpg'); im.crop(crops[i]['kasten']).save(image,quality=90)
            rel=str(image.relative_to(ROOT)); seite=str(imagepath.relative_to(ROOT))
            rec=dict(image=rel,transcription='',quelle=name,zweig='transkribus',id=row['id'],status='offen',offene_silben=len(syll),text=text,seite=seite,region=list(region),split=row['split'],teile=row['teile'])
            if len(syll)==len(groups) or len(syll)==1:
                try:
                    g=musik(groups,syll); PARSER.parse(g)
                    rec.update(transcription=g,status='voll',offene_silben=0); counts['eindeutig']+=1; counts['grammatik_ok']+=1; counts['eindeutig_mehrteilig']+=int(row['teile']>1)
                except Exception as e: counts['konvertierung_fehler']+=1; rec['grund']=str(e)[:160]
            else: counts['offen']+=1; counts['offen_mehrteilig']+=int(row['teile']>1)
            output.append(rec)
            locations.append(dict(bild=rel,seite=seite,box=list(region),andere=[list(x) for x in allregions if x not in row['_regionen']]))
            if rec['status']=='offen': pending.append(dict(id=row['id'],bilder=[str(image)],zooms=[],aufgabe=dict(gesangstext=[text],silben=[s['text'] for s in syll],notengruppen=groups,kandidaten=dict(beschreibung='Silbengrenzen an Kommagruppengrenzen; alle Gruppen und Silben in Reihenfolge verwenden.',gruppenzahl=len(groups),silbenzahl=len(syll),moeglich=len(groups)>=len(syll),grenzen_zwischen_gruppen=list(range(1,len(groups))),anzahl_grenzen=max(0,len(syll)-1)),silben_mit_noten=[],offene_woerter=[])))
    jsonl(target/'zeilen.jsonl',output); jsonl(target/'lage.jsonl',locations); dump(target/'zwischenstand.json',dict(counts)); dump(target/'offen_roh.json',pending); dump(target/'initialen.json',initialen)
    print(name,dict(counts),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='stufe2': run()
    elif sys.argv[1]=='pakete':
        for name in NAMES:
            target=HERE/'daten/cantus_gabc'/name; rows=[json.loads(x) for x in (target/'zeilen.jsonl').read_text().splitlines()]; counts=json.loads((target/'zwischenstand.json').read_text()); pending=json.loads((target/'offen_roh.json').read_text())
            byid={r['id']:r for r in rows}
            for entry in pending:
                if byid[entry['id']].get('grund'): entry['aufgabe']['konvertierungsproblem']=byid[entry['id']]['grund']
                if not entry['aufgabe']['kandidaten']['moeglich']: entry['aufgabe']['kandidaten']['beschreibung']='Weniger Notengruppen als Silben: keine Zuordnung allein durch Auswahl von Kommagrenzen möglich; am Bild prüfen.'
            packages=[]
            for j in range(0,len(pending),8):
                n=j//8+1; path=target/f'paket_{n}.json'; dump(path,pending[j:j+8]); packages.append(dict(nr=n,quelle=name,paket=str(path.relative_to(HERE)),antwort=str((target/f'antwort_{n}.json').relative_to(HERE)),zeilen=len(pending[j:j+8]),bilder=len(pending[j:j+8])))
            dump(target/'sonnet_pakete.json',packages)
            full=[r for r in rows if r['status']=='voll']; examples=full[:3]
            lines=[f'# {name}', '', '## Zahlen', '', 'Zeilen bezeichnet die Zahl der ursprünglichen GT-Notationsregionen; systeme zählt nach Zusammenführung.', '', *[f'- {k}: {v}' for k,v in counts.items()], f'- Offen insgesamt: {len(pending)}',f'- Pakete: {len(packages)}', '', 'Notationszeilen wurden geometrisch mit Textregionen darunter gepaart; Lesereihenfolge dient nur bei gleicher Zahl unzugeordneter Regionen als Rückfall. Mehrteilige Zeilen sind in horizontaler Reihenfolge vereinigt.', '', 'Die Silbentrennung ist regelbasiert und erfordert eine Sichtprüfung. Offene Zeilen enthalten absichtlich keine behauptete Zuordnung.', '', '## Beispiele', '']
            for e in examples: lines += [f"- {e['id']}: {e['text']} → `{e['transcription']}`"]
            (target/'bericht.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20); small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
            decisions={r['id']:r for r in json.loads((target/'initialen.json').read_text()) if r['entschieden']=='ja'}
            samples=full[:10]; width=1600; blocks=[]
            for r in samples:
                im=Image.open(ROOT/r['image']).convert('RGB'); im.thumbnail((width-40,300)); shown=r['text']; decision=decisions.get(r['id']);
                if decision:
                    old=decision['text_alt']; new=decision['text_neu']; n=len(decision['praefix']); pos=next((i for i,c in enumerate(old) if c.isalpha()),0); shown=new[:pos]+'['+new[pos:pos+n]+']'+new[pos+n:]
                texts=[r['id']+'  '+shown]+textwrap.wrap(r['transcription'],155,break_long_words=True,break_on_hyphens=False); blocks.append((im,texts))
            height=sum(im.height+35+len(t)*20 for im,t in blocks)+20; sheet=Image.new('RGB',(width,max(height,30)),'white'); d=ImageDraw.Draw(sheet); y=10
            for im,ts in blocks:
                sheet.paste(im,(10,y)); y+=im.height+5
                for k,t in enumerate(ts): d.text((10,y),t,fill='black',font=font if k==0 else small); y+=22 if k==0 else 18
                y+=10
            sheet.save(target/'pruefbogen.jpg',quality=88)
            print(name,'Pakete',len(packages),'Prüfzeilen',len(samples),flush=True)
