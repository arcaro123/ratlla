"""Phase 1 only: shared library layout and Pygame drawing adapter."""
import os
from datetime import datetime

SIZE=(1080,850)
GAMES=('morris','c4','chess','go','shogi','dino','mines')
TITLES=dict(morris='Tres en ratlla',c4='4 en ratlla',chess='Escacs',go='Go',shogi='Shogi',dino='Dino Run',mines='Buscamines')
DESC={
 'morris':('Domina els tres quadrats.','Planifica cada fitxa i anticipa el rival.'),
 'c4':('Una línia pot decidir-ho tot.','Connecta quatre fitxes abans que el rival.'),
 'chess':('Cada moviment compta.','Domina el tauler, anticipa el rival','i converteix l’estratègia en victòria.'),
 'go':('Construeix el teu territori.','Envolta les pedres rivals i controla l’espai.'),
 'shogi':('La tradició japonesa del tauler.','Captura, promociona i reutilitza les peces.'),
 'dino':('El repte és arribar més lluny.','Esquiva obstacles i supera els teus rècords.'),
 'mines':('Una decisió, un nou descobriment.','Explora les caselles i rescata els robots.')}
NAV=[('library','Biblioteca'),('saves','Partides desades'),('shop','Botiga i col·lecció'),('achievements','Assoliments'),('settings','Configuració')]
IVORY=(229,223,211); GOLD=(184,149,96); MUTED=(165,184,179); DIM=(118,143,142); BG=(35,59,64); SIDE=(23,43,49); LINE=(72,101,104); PANEL=(38,65,70); ACTIVE=(51,79,85)
ASSETS=os.path.join(os.path.dirname(os.path.abspath(__file__)),'assets','home')

def rects():
    result={k:(12,193+i*56,194,48) for i,(k,_) in enumerate(NAV)}
    # Equal horizontal cards, arranged in two strategy rows and one arcade row.
    result.update({k:(240+(i%3)*274,419+(i//3)*119,260,108) for i,k in enumerate(GAMES[:5])})
    result['stats']=(12,727,194,62)
    result.update({'dino':(240,674,260,108),'mines':(514,674,260,108), 'play':(258,302,124,44), 'continue':(390,302,145,44),'guide':(258,354,200,26)})
    return result

def contains(r,pos):
    x,y,w,h=r; return x<=pos[0]<x+w and y<=pos[1]<y+h

def eligible_slot(save,key):
    candidates=[]
    for i,s in enumerate(save.get('slots',[])):
        if not isinstance(s,dict) or s.get('kind')!=key: continue
        if s.get('mode')=='bot' and s.get('difficulty')=='impossible' and save.get('points',0)<2000: continue
        try: date=datetime.strptime(s.get('date',''),'%d/%m/%Y %H:%M')
        except (ValueError,TypeError): date=datetime.min
        candidates.append((date,i))
    return max(candidates)[1] if candidates else None

def mix(a,b,t): return tuple(round(x+(y-x)*t) for x,y in zip(a,b))

def icon(p,key,x,y,c):
    # Consistent 20px outline pictograms, no emoji or external fonts.
    L=lambda a,b: p.line((x+a[0],y+a[1]),(x+b[0],y+b[1]),c,2)
    R=lambda a,b,w,h: p.rect((x+a,y+b,w,h),None,c,1)
    if key=='library':
        for a in (1,11):
            for b in (1,11): R(a,b,7,7)
    elif key=='saves':
        R(2,1,16,19); R(5,3,10,6); R(6,12,8,8)
    elif key=='shop':
        R(2,7,17,13); L((2,7),(5,2)); L((5,2),(16,2)); L((16,2),(19,7)); L((2,11),(19,11)); L((9,11),(9,15))
    elif key=='achievements':
        p.circle((x+10,y+8),6,None,c,2); L((6,13),(4,21)); L((4,21),(10,17)); L((10,17),(16,21)); L((16,21),(14,13))
    elif key=='stats':
        L((1,20),(20,20)); R(3,11,3,7); R(9,7,3,11); R(15,2,3,16)
    elif key=='settings':
        for i,a in enumerate((5,14,9)):
            b=4+i*7; L((1,b),(20,b)); p.circle((x+a,y+b),3,SIDE,c,1)
    elif key=='guide':
        R(2,2,17,17); L((10,3),(10,18)); L((5,7),(7,7)); L((13,7),(16,7))
    elif key=='profile':
        p.circle((x+10,y+6),4,None,c,2); p.line((x+3,y+18),(x+5,y+13),c,2); p.line((x+5,y+13),(x+15,y+13),c,2); p.line((x+15,y+13),(x+17,y+18),c,2)

def logo(p):
    p.image('logo_celestial.png',(53,2,112,112))
    p.text('R A T L L A',109,116,25,IVORY,'serif',align='center',maxw=192)
    p.text('STRATEGY COLLECTION',109,149,11,GOLD,'bold',align='center',maxw=190)

def render(p,selected,points,slots,achievements,slot,mouse=(-1,-1),hover=None,pressed=False):
    if selected not in GAMES: selected='chess'
    rs=rects(); hover=hover or {}
    intensity=lambda k: hover.get(k,1.0 if contains(rs[k],mouse) else 0.0)
    p.image('background.jpg',(0,0,1080,850)); p.rect((0,0,218,850),SIDE); p.line((217,0),(217,850),LINE,1)
    logo(p); p.line((23,177),(195,177),LINE,1)
    for k,label in NAV:
        r=rs[k]; active=k=='library'; enabled=True; t=intensity(k) if enabled else 0; c=GOLD if active else IVORY if enabled else DIM
        if active or t>0: p.rect(r,mix(SIDE,ACTIVE,1 if active else t*.75))
        if active: p.rect((r[0],r[1],3,r[3]),GOLD)
        icon(p,k,r[0]+10,r[1]+13,c); p.text(label,r[0]+40,r[1]+12,15,c,'bold' if active else 'sans',maxw=150)
    p.line((24,714),(194,714),LINE,1)
    r=rs['stats']; t=intensity('stats'); p.rect(r,mix(SIDE,ACTIVE,t*.8),LINE); icon(p,'stats',28,748,GOLD); p.text('Estadístiques',57,738,15,IVORY,'bold',maxw=145); p.text('El teu progrés',57,759,11,MUTED)
    p.text('RATLLA / 01',24,822,10,DIM,'bold')
    p.text('COL·LECCIÓ  /  BIBLIOTECA',240,22,11,GOLD,'bold'); p.text('Biblioteca',240,44,35,IVORY,'serif')
    p.rect((858,33,190,45),SIDE,LINE); p.circle((878,55),9,None,GOLD,2); p.circle((878,55),5,None,GOLD,1); p.text(f'{points:,}'.replace(',','.')+' PTS',1035,45,19,GOLD,'bold',align='right',maxw=140)
    p.line((240,94),(1048,94),LINE,1)
    # Hero: artwork is an independent crop; text and controls remain live.
    p.rect((240,108,808,282),BG); p.image(selected+'_hero.jpg',(538,113,505,272)); p.rect((240,108,808,282),None,GOLD,1)
    p.rect((240,108,4,282),GOLD)
    p.text('JOC DESTACAT  /  '+('ESTRATÈGIA' if selected in GAMES[:5] else 'ARCADE'),258,127,12,GOLD,'bold',maxw=276)
    p.text(TITLES[selected],258,155,40,IVORY,'serif',maxw=288)
    for i,line in enumerate(DESC[selected]): p.text(line,258,218+i*24,16,IVORY if i==0 else MUTED,'bold' if i==0 else 'sans',maxw=284)
    for k,label,primary in [('play','JUGAR  ›',True),('continue','CONTINUAR',False)]:
        if k=='continue' and slot is None: continue
        r=rs[k]; t=intensity(k); fill=mix(GOLD,(220,185,126),t*.55) if primary else mix(SIDE,ACTIVE,t); fill=mix(fill,SIDE,.22) if pressed and contains(r,mouse) else fill
        p.rect(r,fill,GOLD); p.text(label,r[0]+r[2]//2,r[1]+13,15,SIDE if primary else IVORY,'bold',align='center',maxw=r[2]-12)
    icon(p,'guide',258,357,MUTED); p.text('Com es juga',285,359,14,IVORY if intensity('guide') else MUTED,'sans')
    p.text('ESTRATÈGIA',240,399,12,GOLD,'bold'); p.text('05 JOCS',1048,399,11,MUTED,'bold',align='right')
    def game_card(k):
        x,y,w,h=rs[k]; t=intensity(k); chosen=k==selected; edge=GOLD if chosen else mix(LINE,GOLD,t)
        p.rect((x,y,w,h),mix(SIDE,ACTIVE,t*.55))
        p.image(k+'_card.jpg',(x+3,y+3,123,h-6))
        p.rect((x,y,w,h),None,edge,2 if chosen else 1)
        p.text('ESTRATÈGIA' if k in GAMES[:5] else 'ARCADE',x+137,y+14,10,GOLD,'bold',maxw=114)
        p.text(TITLES[k],x+137,y+33,22,IVORY,'serif',maxw=114)
        p.text('Seleccionat' if chosen else 'Veure joc  ›',x+137,y+77,12,GOLD if chosen else MUTED,maxw=114)
    for k in GAMES[:5]: game_card(k)
    p.text('ARCADE',240,654,12,GOLD,'bold'); p.text('02 JOCS',1048,654,11,MUTED,'bold',align='right')
    for k in GAMES[5:]: game_card(k)
    p.line((240,794),(1048,794),LINE,1); p.text('Selecciona un joc · Retorn per jugar',240,810,13,MUTED); p.text(f'{slots} partides desades  /  {achievements} assoliments',1048,810,13,MUTED,align='right',maxw=390)

class PygamePainter:
    def __init__(self,pg,surface): self.pg=pg; self.surface=surface; self.fonts={}; self.images={}; self.texts={}; self.custom_background=None
    def rect(self,r,fill=None,outline=None,width=1):
        if fill is not None: self.pg.draw.rect(self.surface,fill,r)
        if outline is not None: self.pg.draw.rect(self.surface,outline,r,width)
    def line(self,a,b,c,width=1): self.pg.draw.line(self.surface,c,a,b,width)
    def circle(self,center,r,fill=None,outline=None,width=1):
        if fill is not None: self.pg.draw.circle(self.surface,fill,center,r)
        if outline is not None: self.pg.draw.circle(self.surface,outline,center,r,width)
    def text(self,value,x,y,size,color,style='sans',align='left',maxw=None):
        key=(str(value),size,color,style,maxw)
        if key not in self.texts:
            if len(self.texts)>512: self.texts.clear()
            n=size
            while True:
                fk=(style,n)
                if fk not in self.fonts:
                    names='cinzel,georgia,dejavuserif,liberationserif,timesnewroman' if style=='serif' else 'inter,arial,liberationsans,dejavusans'
                    self.fonts[fk]=self.pg.font.SysFont(names,n,bold=style=='bold')
                t=self.fonts[fk].render(str(value),True,color)
                if maxw is None or t.get_width()<=maxw or n<=10: break
                n-=1
            if maxw and t.get_width()>maxw: t=self.pg.transform.smoothscale(t,(maxw,t.get_height()))
            self.texts[key]=t
        t=self.texts[key]; x=x-t.get_width()//2 if align=='center' else x-t.get_width() if align=='right' else x; self.surface.blit(t,(x,y))
    def image(self,name,r):
        x,y,w,h=r; key=(name,w,h)
        if name=='background.jpg' and self.custom_background is not None:
            self.surface.blit(self.custom_background,(x,y)); return
        if key not in self.images:
            try:
                source=self.pg.image.load(os.path.join(ASSETS,name))
                source=source.convert_alpha() if name.endswith('.png') else source.convert()
                iw,ih=source.get_size()
                if iw*h>ih*w:
                    cw=max(1,round(ih*w/h)); source=source.subsurface(((iw-cw)//2,0,cw,ih))
                elif iw*h<ih*w:
                    ch=max(1,round(iw*h/w)); source=source.subsurface((0,(ih-ch)//2,iw,ch))
                self.images[key]=self.pg.transform.smoothscale(source,(w,h))
            except (OSError,self.pg.error): self.images[key]=None
        if self.images[key] is None: self.rect(r,PANEL)
        else: self.surface.blit(self.images[key],(x,y))
