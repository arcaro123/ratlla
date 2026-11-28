"""Phase 3: shared secondary-menu layout, no game or save logic."""
from ratlla_home import GOLD, IVORY, MUTED, DIM, BG, SIDE, LINE, PANEL, ACTIVE, TITLES, mix, contains
SIZE=(700,750)
BACK=(15,15,120,42)
LEVEL_MATERIALS={
 'easy':('BRONZE',(184,149,96),(100,69,44),'../textures/bronze_detail.jpg'),
 'medium':('PLATA',(198,211,216),(75,92,101),'../textures/silver_detail.jpg'),
 'hard':('OR',(233,193,104),(123,91,39),'../textures/gold_detail.jpg'),
 'impossible':('OBSIDIANA',(171,183,185),(40,51,58),'../textures/obsidian_detail.jpg')}

def rects(n):
    if n>=6:
        return [(26+(i%2)*330,265+(i//2)*100,318,90) for i in range(n)]
    h=90 if n<=4 else 76
    step=h+10
    return [(26,265+i*step,648,h) for i in range(n)]

def render(p,state,kind,title,sub,opts,hint,points,unlock,mouse=(-1,-1),pressed=False):
    p.image('background.jpg',(0,0,*SIZE)); p.rect((0,0,700,61),SIDE); p.line((0,61),(700,61),LINE)
    hover=contains(BACK,mouse)
    p.rect(BACK,ACTIVE if hover else PANEL,GOLD if hover else LINE)
    p.text('‹  Enrere',75,28,16,IVORY,'bold',align='center')
    p.text('RATLLA  /  COL·LECCIÓ',350,28,13,GOLD,'bold',align='center',maxw=238)
    p.text(f"{points:,}".replace(',','.')+' PTS',674,26,17,GOLD,'bold',align='right',maxw=160)
    p.text(title,26,77,36,IVORY,'serif',maxw=648)
    p.text(sub,28,124,17,MUTED,maxw=644)
    art='morris' if state=='settings' else kind
    if art not in TITLES: art='chess'
    p.rect((26,155,648,93),SIDE,GOLD)
    p.image(art+'_hero.jpg',(376,156,297,91))
    p.rect((26,155,4,93),GOLD)
    section={'modes':'01  /  MODALITAT','diff':'02  /  NIVELL DEL RIVAL','side':'03  /  ORDRE DE JOC','settings':'PREFERÈNCIES  /  SO I MOVIMENT'}.get(state,'SELECCIÓ')
    p.text(section,43,168,12,GOLD,'bold',maxw=320)
    p.text(('Personalitza el joc' if state=='settings' else 'Selecciona una opció' if state=='modes' else TITLES[art]),43,193,26,IVORY,'serif',maxw=320)
    for i,(r,o) in enumerate(zip(rects(len(opts)),opts)):
        key,label,desc,enabled=o[:4]; locked=bool(len(o)>4 and o[4]); x,y,w,h=r
        t=enabled and contains(r,mouse); primary=LEVEL_MATERIALS.get(key) if state=='diff' else None
        col=primary[1] if primary else GOLD
        fill=mix(PANEL,ACTIVE,.78) if t else PANEL if enabled else SIDE
        if t and pressed: fill=mix(fill,SIDE,.35)
        p.rect(r,fill,col if t or primary else LINE)
        p.rect((x,y,3,h),col if enabled else DIM)
        # Compact numbered key badge, and material swatch for difficulty.
        bx=x+12; by=y+14
        if primary:
            mat,accent,base,texture=primary
            p.rect((bx,by,80,h-28),base,accent)
            if texture: p.image(texture,(bx+1,by+1,78,h-30))
            p.rect((bx+3,by+h-48,74,17),SIDE)
            p.text(mat,bx+40,by+h-46,10,accent,'bold',align='center',maxw=70)
            tx=x+105
        else:
            p.rect((bx,by,32,32),SIDE,col if enabled else DIM)
            p.text(f'{i+1:02}',bx+16,by+8,13,col if enabled else DIM,'bold',align='center')
            tx=x+56
        end=x+w-13
        if locked:
            p.text(label,tx,y+9,21,IVORY,'bold',maxw=end-tx-85)
            p.text('BLOQUEJAT',end,y+14,11,col,'bold',align='right')
            p.text(desc,tx,y+34,14,MUTED,maxw=end-tx)
            barw=end-tx-100
            p.rect((tx,y+60,barw,6),SIDE,LINE)
            progress=min(1,max(0,points/max(1,unlock)))
            if progress: p.rect((tx+1,y+61,max(1,int((barw-2)*progress)),4),GOLD)
            p.text(f'{points:,} / {unlock:,}'.replace(',','.'),end,y+55,12,MUTED,'bold',align='right',maxw=95)
        else:
            reserve=22 if enabled else 0
            p.text(label,tx,y+12,20,IVORY if enabled else MUTED,'bold',maxw=end-tx-reserve)
            p.text(desc,tx,y+43,15,MUTED if enabled else DIM,maxw=end-tx-reserve)
            if enabled: p.text('›',end,y+29,24,col,'bold',align='right')
            else: p.text('NO DISPONIBLE',end,y+h-17,10,DIM,'bold',align='right')
    p.line((26,686),(674,686),LINE)
    p.text(hint.split('   -   M =')[0].split(' · M =')[0],350,701,13,MUTED,align='center',maxw=648)
    p.text('ESC / M  ·  Enrere',350,724,11,DIM,align='center')
