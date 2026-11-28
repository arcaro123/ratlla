"""Persistent RATLLA navigation: shared coordinates, no changes to game rules."""
from ratlla_home import (SIZE, NAV, SIDE, LINE, ACTIVE, GOLD, IVORY, MUTED, DIM,
                         PygamePainter, rects, contains, icon, logo, mix)

WIDTH = 218
HEIGHT = SIZE[1]
NAV_RECTS = {k: rects()[k] for k, _ in NAV}
NAV_RECTS['stats'] = rects()['stats']
_surface = None
_painter = None


def layout(display_size, logical):
    """Return outer, content, and sidebar pixel rectangles."""
    w, h = display_size
    ow, oh = SIZE
    scale = min(w / ow, h / oh)
    fw, fh = max(1, int(ow * scale)), max(1, int(oh * scale))
    x, y = (w - fw) // 2, (h - fh) // 2
    sw = max(1, min(fw, round(fw * WIDTH / ow)))
    outer = (x, y, fw, fh)
    side = (x, y, sw, fh)
    if logical == SIZE:
        return outer, outer, side
    lw, lh = logical
    area = max(1, fw - sw)
    s = min(area / lw, fh / lh)
    cw, ch = max(1, int(lw * s)), max(1, int(lh * s))
    return outer, (x + sw + (area - cw) // 2, y + (fh - ch) // 2, cw, ch), side


def side_pos(rect, pos):
    x, y, w, h = rect
    return ((pos[0] - x) * WIDTH / w, (pos[1] - y) * HEIGHT / h)


def active_key(app):
    return app.state if app.state in NAV_RECTS else 'library'


def draw(pg, display, rect, app):
    global _surface, _painter
    if _surface is None:
        _surface = pg.Surface((WIDTH, HEIGHT))
        _painter = PygamePainter(pg, _surface)
    p = _painter
    mouse = side_pos(rect, pg.mouse.get_pos())
    active = active_key(app)
    p.rect((0, 0, WIDTH, HEIGHT), SIDE)
    p.line((WIDTH - 1, 0), (WIDTH - 1, HEIGHT), LINE)
    logo(p)
    p.line((23, 177), (195, 177), LINE)
    for key, label in NAV:
        r = NAV_RECTS[key]
        selected = key == active
        hover = contains(r, mouse)
        if selected or hover:
            p.rect(r, ACTIVE if selected else mix(SIDE, ACTIVE, .75))
        if selected:
            p.rect((r[0], r[1], 3, r[3]), GOLD)
        c = GOLD if selected else IVORY
        icon(p, key, r[0] + 10, r[1] + 13, c)
        p.text(label, r[0] + 40, r[1] + 12, 15, c, 'bold' if selected else 'sans', maxw=150)
    if getattr(app, '_sidebar_pending', None):
        p.rect((12, 510, 194, 105), ACTIVE, GOLD)
        p.text('Sortir de la partida?', 22, 522, 14, GOLD, 'bold', maxw=174)
        p.text('Torna a prémer', 22, 548, 13, IVORY)
        p.text('la mateixa opció.', 22, 566, 13, IVORY)
        p.text('Desa abans de sortir.', 22, 590, 12, MUTED, maxw=174)
    p.line((24, 714), (194, 714), LINE)
    r = NAV_RECTS['stats']
    p.rect(r, ACTIVE if active == 'stats' or contains(r, mouse) else SIDE,
           GOLD if active == 'stats' else LINE)
    icon(p, 'stats', 28, 748, GOLD)
    p.text('Estadístiques', 57, 738, 15, IVORY, 'bold', maxw=145)
    p.text('El teu progrés', 57, 759, 11, MUTED)
    p.text('RATLLA / 01', 24, 822, 10, DIM, 'bold')
    display.blit(_surface if rect[2:] == (WIDTH, HEIGHT) else
                 pg.transform.smoothscale(_surface, rect[2:]), rect[:2])


def navigate(app, key):
    target = 'main' if key == 'library' else key
    if target == app.state:
        app._sidebar_pending = None
        return
    playing = app.state == 'play' or (app.state == 'saves' and app.save_mode)
    if playing and app.game is not None and not app.result:
        # A second deliberate click is required before leaving unsaved gameplay.
        if getattr(app, '_sidebar_pending', None) != key:
            app._sidebar_pending = key
            return
    app._sidebar_pending = None
    if playing:
        app.leave()
    app.state = target
    app.save_mode = False
    app.page = 0
    app.stats_tab = 0
    app.delete_pending = None
    app.shop_sel = None
    if target == 'shop':
        app.shop_msg = None


def route(pg, app, events, sidebar, content):
    """Consume sidebar clicks before converting the remaining game coordinates."""
    if sidebar is None:
        return events
    sidebar_rect = pg.Rect(sidebar)
    content_rect = pg.Rect(content)
    remaining = []
    for event in events:
        if event.type == pg.MOUSEBUTTONDOWN and sidebar_rect.collidepoint(event.pos):
            if event.button == 1:
                point = side_pos(sidebar, event.pos)
                key = next((k for k, r in NAV_RECTS.items() if contains(r, point)), None)
                if key:
                    navigate(app, key)
                    # Never forward this click to a board or arcade action.
                    return [e for e in events if e.type == pg.QUIT]
            continue
        if event.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP):
            if not content_rect.collidepoint(event.pos):
                continue
            if event.type == pg.MOUSEBUTTONDOWN:
                app._sidebar_pending = None
        if event.type == pg.KEYDOWN:
            app._sidebar_pending = None
        remaining.append(event)
    return remaining
