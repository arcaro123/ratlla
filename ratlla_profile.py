"""Fase 6: perfil local, sense canvis en l'economia ni en la lògica dels taulers."""
from ratlla_home import PygamePainter, IVORY, GOLD, MUTED, DIM, SIDE, LINE, PANEL, ACTIVE

GREEN=(132,185,159); RED=(197,126,117); NEUTRAL=(151,168,177)
BACK=(24,22,100,36); PREV=(110,680,120,42); NEXT=(470,680,120,42)
TABS=[(24+i*220,114,212,37) for i in range(3)]

def total(save,games,levels):
    return tuple(sum(save['records'][g][l][i] for g in games for l in levels) for i in range(3))

def progress(key,s,games,levels,done):
    if done: return 1,1
    if key.startswith('win:'): return max(s['records'][g][key.split(':')[1]][0] for g in games),1
    if key.startswith('streak:'):
        _,l,n=key.split(':'); return max(s['best_streaks'].get(g+':'+l,0) for g in games),int(n)
    if key.startswith('game:'): return sum(s['records'][key.split(':')[1]][l][0] for l in levels),1
    if key=='wins25': return total(s,games,levels)[0],25
    if key=='clean10': return s['clean_wins'],10
    vals={'dino:first':('runs',1),'dino:time':('time',45),'dino:sprint':('sprint',1),'dino:expedition':('expedition',1),'dino:coins':('coins',100)}
    if key in vals:
        field,target=vals[key]; return s['dino_profile'][field],target
    if key=='dino:gold': return s['dino_best'],3000
    if key.startswith('mines:'):
        w=s['mine_profile']['wins']; return (sum(w.values()) if key=='mines:first' else w.get('mine_hard' if key=='mines:hard' else 'mine_treasure',0)),1
    return 0,1

def base(p,title,sub):
    p.image('background.jpg',(0,0,700,750)); p.rect((0,0,700,110),SIDE); p.line((24,106),(676,106),LINE)
    p.text('PERFIL LOCAL  /  RATLLA',676,18,11,GOLD,'bold',align='right'); p.text(title,24,61,30,IVORY,'serif',maxw=640); p.text(sub,676,80,13,MUTED,align='right',maxw=320)

def button(p,r,label,mouse,enabled=True,accent=False):
    from ratlla_home import contains
    x,y,w,h=r; p.rect(r,GOLD if accent and enabled else ACTIVE if enabled and contains(r,mouse) else SIDE, GOLD if enabled else LINE)
    p.text(label,x+w//2,y+int((h-16)/2),14,SIDE if accent and enabled else IVORY if enabled else DIM,'bold',align='center',maxw=w-8)

def bar(p,x,y,w,parts):
    p.rect((x,y,w,7),SIDE); n=sum(v for v,c in parts); left=x; seen=0
    for v,c in parts:
        seen+=v; end=x+int(w*seen/n) if n else x
        if end>left: p.rect((left,y,end-left,7),c)
        left=end

def metric(p,x,y,w,label,value):
    p.rect((x,y,w,77),PANEL,LINE); p.text(label,x+12,y+10,13,MUTED,'bold',maxw=w-24); p.text(str(value),x+12,y+31,30,IVORY,'serif',maxw=w-24)

def record_row(p,y,label,rec):
    w,l,d=rec; n=w+l+d; p.rect((24,y,652,52),PANEL,LINE); p.text(label,36,y+8,15,IVORY,'bold',maxw=175)
    p.text(f'{w} V   {l} D   {d} E',226,y+8,13,MUTED,maxw=200); p.text(f'{100*w/n:.1f}%' if n else '—',663,y+8,17,GOLD,'bold',align='right')
    bar(p,226,y+34,436,[(w,GREEN),(l,RED),(d,NEUTRAL)])

def statistics(p,s,games,levels,titles,level_info,mine_levels,tab,mouse):
    base(p,'Estadístiques','Resultats registrats'); button(p,BACK,'‹ Enrere',mouse)
    for i,label in enumerate(('Estratègia','Dificultats','Arcade')): button(p,TABS[i],label,mouse,accent=tab==i)
    rec=total(s,games,levels); w,l,d=rec; n=sum(rec)
    if tab in (0,1):
        for i,(label,v) in enumerate((('Partides contra l’ordinador',n),('Victòries',w),('Derrotes',l),('Empats',d))): metric(p,24+(i%2)*330,164+(i//2)*87,322,label,v)
        p.text('Percentatge de victòries',24,343,14,MUTED,'bold'); p.text(f'{100*w/n:.1f}%' if n else '—',300,338,23,GOLD,'serif',align='right')
        p.text('Millor ratxa',365,343,14,MUTED,'bold'); p.text(str(max(s['best_streaks'].values(),default=0)),676,338,23,GOLD,'serif',align='right')
        p.text('V = victòries · D = derrotes · E = empats',24,378,12,MUTED)
        rows=[(titles[g],total(s,[g],levels)) for g in games] if tab==0 else [(level_info[l][0].capitalize(),total(s,games,[l])) for l in levels]
        for i,(label,r) in enumerate(rows): record_row(p,400+i*57,label,r)
        if tab==0: p.text(f'Partides locals finalitzades: {sum(total(s,games,["local"]))} · Sense atribuir-les al perfil',24,703,12,MUTED,maxw=652)
        else: p.text('Les partides en línia no tenen historial registrat.',24,703,12,MUTED)
    else:
        dp=s['dino_profile']; p.text('Dino Run',24,166,22,IVORY,'serif')
        for i,(label,v) in enumerate((('Curses finalitzades',dp['runs']),('Rècord de puntuació',s['dino_best']),('Monedes recollides',dp['coins']),('Millor temps',str(dp['time'])+' s'))): metric(p,24+(i%2)*330,198+(i//2)*85,322,label,v)
        p.text(f'Sprints completats: {dp["sprint"]}  ·  Expedicions: {dp["expedition"]}',24,372,14,MUTED)
        p.text('Buscamines',24,407,22,IVORY,'serif'); p.text('Victòries / millor temps',676,414,13,MUTED,align='right')
        mp=s['mine_profile'];
        for i,(k,data) in enumerate(mine_levels.items()):
            y=441+i*34; p.rect((24,y,652,30),PANEL,LINE); p.text(data[0],36,y+7,14,IVORY,maxw=310); p.text(str(mp['wins'].get(k,0)),468,y+7,14,GOLD,align='right'); p.text(f'{mp["best"][k]:.1f} s' if k in mp['best'] else '—',663,y+7,14,MUTED,align='right')
        p.text('Intents i derrotes anteriors: no registrats.',24,660,12,MUTED)
        count=s.get('mine_attempts_v6',{}); p.text(f'Des de la fase 6: {count.get("wins",0)} victòries · {count.get("losses",0)} derrotes',24,685,13,IVORY,maxw=652)

def profile_medal(p,x,y,key,done):
    light=(229,196,130) if done else (157,177,178); dark=(87,59,32) if done else (54,76,82)
    for r in range(25,0,-1):
        t=(25-r)/25; col=tuple(round(a+(b-a)*(.35+.65*abs((t*3)%2-1))) for a,b in zip(dark,light))
        p.circle((x,y),r,col,None)
    p.circle((x,y),19,SIDE,light,1); p.circle((x,y),16,None,light,1)
    if key.startswith('streak:'): symbol='III'
    elif key.startswith('win:'): symbol='V'
    elif key.startswith('game:'): symbol='R'
    elif key.startswith('dino:'): symbol='D'
    elif key.startswith('mines:'): symbol='M'
    elif key.startswith('secret'): symbol='?'
    else: symbol='★'
    p.text(symbol,x,y-10,16,light,'bold',align='center',maxw=26)

def achievement_screen(p,s,ach,games,levels,page,mouse,medal):
    unlocked=set(s['achievements']); n=sum(k in unlocked for k,*_ in ach); base(p,'Assoliments',f'{n} de {len(ach)} desbloquejats'); button(p,BACK,'‹ Enrere',mouse)
    bar(p,24,118,652,[(n,GOLD),(len(ach)-n,LINE)])
    for i,(key,name,desc,hidden,cond) in enumerate(ach[page*7:(page+1)*7]):
        y=140+i*75; done=key in unlocked; p.rect((24,y,652,68),PANEL if done else SIDE,GOLD if done else LINE); profile_medal(p,60,y+33,key,done)
        p.text('Assoliment secret' if hidden and not done else name,100,y+8,17,IVORY,'bold',maxw=420)
        p.text('Requisit ocult' if hidden and not done else desc,100,y+31,12,MUTED,maxw=550)
        if not hidden or done:
            v,t=progress(key,s,games,levels,done); v=min(v,t); bar(p,100,y+53,420,[(v,GOLD),(t-v,LINE)]); p.text('Completat' if done else f'{v}/{t}',663,y+47,12,GOLD if done else MUTED,align='right')
        else: p.text('Per descobrir',663,y+47,12,DIM,align='right')
    pages=(len(ach)+6)//7; button(p,PREV,'‹ Anterior',mouse,page>0); button(p,NEXT,'Següent ›',mouse,page+1<pages); p.text(f'{page+1} / {pages}',350,693,15,MUTED,align='center')

def thumbnail(p,slot,state,x,y):
    kind=slot['kind']; p.rect((x,y,84,82),SIDE,LINE)
    if kind=='dino':
        p.image('dino_card.jpg',(x+2,y+2,80,58)); p.text(str(state.get('score',0))+' pts',x+42,y+63,11,IVORY,align='center'); return
    if kind=='morris':
        cx,cy=x+42,y+41
        for h in (34,23,12): p.rect((cx-h,cy-h,h*2,h*2),None,GOLD)
        for a,b in [((-34,0),(-12,0)),((12,0),(34,0)),((0,-34),(0,-12)),((0,12),(0,34))]: p.line((cx+a[0],cy+a[1]),(cx+b[0],cy+b[1]),GOLD)
        for (ring,r,c),v in state['board'].items():
            if v: h=(34,23,12)[ring]; p.circle((cx+(c-1)*h,cy+(r-1)*h),4,IVORY if v=='W' else (66,89,100),GOLD)
        return
    if kind=='c4':
        for c,col in enumerate(state['grid']):
            for r,v in enumerate(col): p.circle((x+12+c*10,y+67-r*10),4,GOLD if v==2 else (150,60,50) if v==1 else (18,30,36),LINE)
        return
    n=state['n'] if kind=='mines' else 8 if kind=='chess' else 9; cell=70//n; ox=x+(84-cell*n)//2; oy=y+(82-cell*n)//2
    if kind=='go':
        p.rect((ox,oy,cell*n,cell*n),(174,139,94)); offset=cell//2
        for k in range(n):
            p.line((ox+offset,oy+offset+k*cell),(ox+offset+(n-1)*cell,oy+offset+k*cell),SIDE); p.line((ox+offset+k*cell,oy+offset),(ox+offset+k*cell,oy+offset+(n-1)*cell),SIDE)
        for i,v in enumerate(state['board']):
            if v: r,c=divmod(i,n); p.circle((ox+offset+c*cell,oy+offset+r*cell),max(2,cell//2-1),IVORY if v==2 else (24,32,36),None)
        return
    for r in range(n):
        for c in range(n):
            i=r*n+c; xx=ox+c*cell; yy=oy+r*cell
            if kind=='mines':
                opened=i in state['opened']; flagged=i in state['flags']; p.rect((xx,yy,cell,cell),GOLD if flagged else (180,174,148) if opened else (54,81,86),SIDE); continue
            p.rect((xx,yy,cell,cell),(174,139,94) if kind!='chess' or (r+c)%2==0 else (73,66,62),SIDE); v=state['board'][i]
            if v:
                if kind=='go': p.circle((xx+cell//2,yy+cell//2),max(2,cell//2-1),IVORY if v==2 else (24,32,36),None)
                else: p.circle((xx+cell//2,yy+cell//2),max(2,cell//2-1),IVORY if v>0 else (24,32,36),None)

def slots_screen(p,s,titles,level_info,page,mouse,save_mode,current,pending,decode,locked):
    base(p,'Desar la partida' if save_mode else 'Partides desades',f'{sum(v is not None for v in s["slots"])} / 10 espais'); button(p,BACK,'‹ Enrere',mouse)
    for j,i in enumerate(range(page*5,page*5+5)):
        y=125+j*108; slot=s['slots'][i]; p.rect((24,y,652,100),PANEL,LINE)
        if slot:
            try: thumbnail(p,slot,decode(slot['game']),34,y+9)
            except (KeyError,ValueError,TypeError,IndexError): p.image(slot['kind']+'_card.jpg',(34,y+9,84,82))
            p.text(f'{i+1:02}  /  {titles.get(slot["kind"],slot["kind"])}',132,y+10,18,IVORY,'serif',maxw=330)
            mode=slot.get('mode'); difficulty=level_info.get(slot.get('difficulty'),('—',))[0].capitalize(); blocked=mode=='bot' and locked(slot.get('difficulty'))
            p.text(f'{"Contra l’ordinador · "+difficulty if mode=="bot" else "Local" if mode=="local" else mode or "—"}  ·  {slot.get("moves",0)} mov.',132,y+38,13,MUTED,maxw=320)
            p.text(slot.get('date') or 'Data no disponible',132,y+61,12,MUTED,maxw=320)
            button(p,(486,y+12,178,32),'Actualitza' if save_mode else 'Bloquejada' if blocked else 'Continuar',mouse,(i==current) if save_mode else not blocked,True)
            button(p,(486,y+55,178,32),'Confirma l’eliminació' if pending==i else 'Eliminar',mouse)
        else:
            p.text(f'{i+1:02}  /  Espai lliure',44,y+20,18,MUTED,'serif'); p.text('Disponible per desar una partida',44,y+50,13,DIM)
            if save_mode: button(p,(486,y+12,178,32),'Desar aquí',mouse,True,True)
    button(p,PREV,'‹ Anterior',mouse,page>0); button(p,NEXT,'Següent ›',mouse,page<1); p.text(f'{page+1} / 2',350,693,15,MUTED,align='center')
