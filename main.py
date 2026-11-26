import asyncio
import json
import math
import os
import random
import sys
import time

import pygame

# "js" només existeix al navegador (pygbag). A l'ordinador no, i els modes
# local i contra l'ordinador funcionen igualment.
try:
  import js
  HAS_JS = True
except ImportError:
  js = None
  HAS_JS = False

pygame.init()
pygame.font.init()

# ---------------------------------------------------------------
# CONSTANTS GENERALS
# ---------------------------------------------------------------

# Taules: si la mateixa posició (amb el mateix torn) es repeteix aquest
# nombre de cops, la partida s'acaba en empat (només local i contra el bot).
REPETITIONS_FOR_DRAW = 3

# Si una partida arriba a aquest nombre de moviments sense guanyador, taules.
MAX_MOVES = 120

# Valor que el bot dóna a una taula per repetició. És negatiu a propòsit:
# així l'evita mentre no estigui clarament perdut.
DRAW_SCORE = -12

# Punts per guanyar a cada dificultat (una taula en dóna una cinquena part).
# Si has usat desfer o pista, només en cobres la meitat.
POINTS = {"easy": 10, "medium": 30, "hard": 100, "impossible": 300}

# Punts totals necessaris per poder jugar el nivell IMPOSSIBLE.
UNLOCK_POINTS = 2000

# Punts que costa demanar una pista (com més fort és el bot, més cara).
# Si uses una pista, la victòria només dona 1 punt.
HINT_COST = {"easy": 5, "medium": 15, "hard": 50, "impossible": 150, "local": 5}

# Desfer també costa punts, però bastant menys que una pista (aprox. 1/4).
UNDO_COST = {"easy": 2, "medium": 5, "hard": 15, "impossible": 40, "local": 2}

LEVELS = ("easy", "medium", "hard", "impossible")
LEVEL_INFO = {
    "easy": ("FÀCIL", "Es despista sovint"),
    "medium": ("MITJÀ", "Veu unes quantes jugades"),
    "hard": ("DIFÍCIL", "Molt difícil de guanyar"),
    "impossible": ("IMPOSSIBLE", "No falla mai"),
}


def is_locked(level):
  """L'impossible està bloquejat fins que s'arriba a UNLOCK_POINTS punts.

  Un cop desbloquejat ho queda per sempre, encara que gastis punts.
  """
  return (level == "impossible" and not SAVE.get("unlocked")
          and SAVE["points"] < UNLOCK_POINTS)


WIDTH, HEIGHT = 700, 750
BOARD_SIZE = 550
OFFSET_X = (WIDTH - BOARD_SIZE) // 2
OFFSET_Y = 110

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jocs de taula")

# LA TEVA URL DE FIREBASE (només es fa servir en el mode online)
FIREBASE_URL = (
    "https://arnau-2-default-rtdb.europe-west1.firebasedatabase.app/game.json"
)

ONLINE_ENGINE = {"started": False}


def start_online_engine():
  """Injecta el motor de Firebase en JavaScript (només en mode online)."""
  if ONLINE_ENGINE["started"] or not HAS_JS:
    return

  js.window.eval(f"""
window.latestGameState = null;
window.firebaseUrl = "{FIREBASE_URL}";

setInterval(async () => {{
    try {{
        let res = await fetch(window.firebaseUrl, {{ cache: 'no-store' }});
        if (res.ok) {{
            let text = await res.text();
            if (text && text !== "null") {{
                window.latestGameState = text;
            }}
        }}
    }} catch(e) {{}}
}}, 300);

window.sendGameState = function(jsonStr) {{
    window.latestGameState = jsonStr;
    try {{
        fetch(window.firebaseUrl, {{
            method: 'PUT',
            headers: {{'Content-Type': 'application/json'}},
            body: jsonStr
        }});
    }} catch(e) {{}}
}};
""")

  ONLINE_ENGINE["started"] = True


# COLORS
BG_COLOR = (240, 217, 181)
LINE_COLOR = (75, 54, 33)
TEXT_COLOR = (50, 50, 50)
SOFT_TEXT = (120, 100, 80)
WHITE_PIECE = (240, 240, 240)
WHITE_BORDER = (100, 100, 100)
BLACK_PIECE = (40, 40, 40)
BLACK_BORDER = (0, 0, 0)
HIGHLIGHT_COLOR = (0, 220, 100)
WIN_LINE_COLOR = (30, 200, 80)
HINT_COLOR = (0, 190, 90)
LAST_COLOR = (255, 160, 0)
TIP_COLOR = (30, 120, 255)
COLOR_WIN = (30, 150, 70)
COLOR_LOSE = (190, 50, 50)
COLOR_DRAW = (190, 130, 20)

# cadenes del nivell bloquejat
CHAIN_DARK = (70, 72, 78)
CHAIN_LIGHT = (175, 178, 186)
LOCK_GOLD = (230, 180, 40)

BOARD_BLUE = (30, 80, 170)
BOARD_DARK = (18, 50, 120)
C4_COLORS = {
    1: ((215, 50, 50), (140, 20, 20)),
    2: ((245, 200, 40), (170, 130, 10)),
}

FONT = pygame.font.SysFont("arial", 20, bold=True)
SMALL = pygame.font.SysFont("arial", 16, bold=True)
TITLE_FONT = pygame.font.SysFont("arial", 28, bold=True)
RES_FONT = pygame.font.SysFont("arial", 36, bold=True)
BIG_FONT = pygame.font.SysFont("arial", 44, bold=True)

# ---------------------------------------------------------------
# BOTIGA: DADES (taulers, fitxes, marques, celebracions, extres i packs)
# ---------------------------------------------------------------
# "req" = requisit de progrés: ("wins", n) victòries contra el bot en total,
# o ("level", nivell) haver guanyat com a mínim una vegada a aquest nivell.

# Taulers: color de fons, de línies i del tauler del 4 en ratlla.
BOARD_THEMES = {
    "classic": dict(name="Clàssic", price=0, bg=(240, 217, 181),
                    line=(75, 54, 33), c4=(30, 80, 170), c4dark=(18, 50, 120),
                    desc="El tauler de sempre: beix càlid i fusta fosca."),
    "forest": dict(name="Bosc", price=250, bg=(206, 226, 188),
                   line=(44, 74, 40), c4=(34, 120, 80), c4dark=(20, 80, 52),
                   desc="Verds tranquils per pensar millor cada jugada."),
    "ocean": dict(name="Oceà", price=400, bg=(190, 224, 238),
                  line=(22, 62, 102), c4=(0, 125, 160), c4dark=(0, 84, 110),
                  desc="Blaus profunds i calmats, com una tarda a la platja."),
    "cherry": dict(name="Cirera", price=600, bg=(246, 208, 214),
                   line=(110, 30, 50), c4=(170, 40, 80), c4dark=(110, 20, 52),
                   req=("wins", 3),
                   desc="Rosa cirera. Reservat a jugadors amb una mica d'experiència."),
    "lavender": dict(name="Lavanda", price=800, bg=(222, 212, 242),
                     line=(62, 42, 110), c4=(100, 70, 170), c4dark=(62, 42, 120),
                     req=("wins", 8),
                     desc="Tons violeta suaus per a qui ja domina el tauler."),
    "sand": dict(name="Desert", price=1200, bg=(236, 200, 140),
                 line=(120, 70, 20), c4=(200, 120, 30), c4dark=(140, 80, 15),
                 req=("level", "hard"),
                 desc="Or i sorra. Només per a qui ha derrotat el nivell Difícil."),
}

# Fitxes: w/b = escacs i Tres en ratlla (blanques/negres), b/w al Go,
# c1/c2 = 4 en ratlla. Cada color és (farciment, vora). deco: 0 llisa, 1 anell, 2 gemma.
PIECE_STYLES = {
    "classic": dict(name="Clàssiques", price=0, deco=0,
                    w=((240, 240, 240), (100, 100, 100)),
                    b=((40, 40, 40), (0, 0, 0)),
                    c1=((215, 50, 50), (140, 20, 20)),
                    c2=((245, 200, 40), (170, 130, 10)),
                    desc="Blanques i negres de tota la vida."),
    "wood": dict(name="Fusta", price=200, deco=1,
                 w=((236, 206, 150), (150, 110, 60)),
                 b=((112, 70, 36), (60, 36, 16)),
                 c1=((196, 120, 60), (110, 60, 25)),
                 c2=((240, 214, 160), (150, 110, 60)),
                 desc="Peces de fusta tornejada amb un anell gravat."),
    "gem": dict(name="Gemmes", price=400, deco=2,
                w=((90, 200, 235), (30, 110, 150)),
                b=((225, 60, 110), (130, 20, 60)),
                c1=((225, 60, 110), (130, 20, 60)),
                c2=((90, 200, 235), (30, 110, 150)),
                desc="Turquesa i robí amb una brillantor al centre."),
    "gold": dict(name="Or i plata", price=700, deco=1,
                 w=((245, 205, 80), (160, 120, 10)),
                 b=((185, 190, 200), (90, 95, 105)),
                 c1=((245, 205, 80), (160, 120, 10)),
                 c2=((185, 190, 200), (90, 95, 105)),
                 req=("wins", 5),
                 desc="Un exèrcit d'or contra un de plata."),
    "neon": dict(name="Neó", price=1000, deco=2,
                 w=((90, 255, 170), (0, 140, 80)),
                 b=((200, 90, 255), (100, 20, 150)),
                 c1=((200, 90, 255), (100, 20, 150)),
                 c2=((90, 255, 170), (0, 140, 80)),
                 req=("wins", 12),
                 desc="Verd i violeta elèctrics. Per a veterans."),
    "marble": dict(name="Marbre", price=1500, deco=1,
                   w=((245, 245, 250), (150, 150, 165)),
                   b=((62, 64, 76), (25, 26, 32)),
                   c1=((90, 110, 210), (40, 55, 130)),
                   c2=((240, 240, 246), (150, 150, 165)),
                   req=("level", "impossible"),
                   desc="Marbre blanc i pissarra. El premi als qui han vençut l'Impossible."),
}

# Marques de l'última jugada (color del ressaltat).
MARK_STYLES = {
    "orange": dict(name="Taronja", price=0, color=(255, 160, 0),
                   desc="El ressaltat clàssic de l'última jugada."),
    "cyan": dict(name="Cian", price=100, color=(0, 200, 230),
                 desc="Un blau elèctric que es veu de lluny."),
    "magenta": dict(name="Magenta", price=150, color=(230, 60, 170),
                    desc="Rosa intens per no perdre mai de vista la jugada."),
    "lime": dict(name="Llimona", price=200, color=(130, 220, 30),
                 desc="Verd llima fluorescent."),
}

# Celebracions quan guanyes una partida.
FX_STYLES = {
    "none": dict(name="Cap", price=0, desc="Sense efectes. Victòries discretes."),
    "confetti": dict(name="Confeti", price=150,
                     desc="Pluja de confeti de colors quan guanyes."),
    "stars": dict(name="Estels", price=300, req=("wins", 5),
                  desc="Estels daurats que centellegen sobre la pantalla."),
    "bubbles": dict(name="Bombolles", price=400,
                    desc="Bombolles que pugen suaument mentre celebres."),
}

# Extres consumibles (es poden comprar moltes vegades).
EXTRA_ITEMS = {
    "hints": dict(name="Pack de pistes", price=120, amount=3, field="hints",
                  big="x3", small="pistes",
                  desc="3 pistes que no costen punts. Compten igual: amb pista la victòria només dona 1 punt."),
    "undos": dict(name="Pack de desfer", price=40, amount=5, field="undos",
                  big="x5", small="desfer",
                  desc="5 usos de desfer gratuïts. Si els gastes, no et cobrem punts per tornar enrere."),
    "double": dict(name="Multiplicador x2", price=250, amount=3, field="double",
                   big="x2", small="3 victòries",
                   desc="Les teves 3 properes victòries contra el bot donen el doble de punts."),
}

# Packs: conjunts amb descompte. Si ja tens alguna peça, només pagues la resta.
PACKS = {
    "natura": dict(name="Pack Natura", disc=0.25,
                   items=(("boards", "forest"), ("pieces", "wood"),
                          ("marks", "lime"), ("fx", "bubbles")),
                   desc="Bosc, fusta, llimona i bombolles. Tot l'estil verd."),
    "arcade": dict(name="Pack Arcade", disc=0.30,
                   items=(("boards", "cherry"), ("pieces", "neon"),
                          ("marks", "cyan"), ("fx", "confetti")),
                   desc="Cirera, neó, cian i confeti. Per a veterans."),
    "reial": dict(name="Pack Reial", disc=0.25,
                  items=(("boards", "lavender"), ("pieces", "gold"),
                         ("marks", "magenta"), ("fx", "stars")),
                  desc="Lavanda, or i plata, magenta i estels. Tot un llinatge."),
}

SHOP_TABS = (("boards", "Taulers"), ("pieces", "Fitxes"), ("marks", "Marques"),
             ("fx", "Victòria"), ("extras", "Extres"), ("packs", "Packs"))
TAB_NAMES = {"boards": "tauler", "pieces": "fitxes", "marks": "marca", "fx": "efecte"}
COSMETIC_TABS = ("boards", "pieces", "marks", "fx")
DEAL_DISCOUNT = 0.30
STOCK_MAX = 99

RARITIES = ((900, "Llegendari", (210, 140, 0)), (500, "Èpic", (150, 60, 200)),
            (150, "Rar", (30, 120, 220)), (0, "Comú", (120, 110, 100)))


def _lighter(c):
  return tuple(min(255, v + 70) for v in c)


def shop_table(tab):
  return {"boards": BOARD_THEMES, "pieces": PIECE_STYLES, "marks": MARK_STYLES,
          "fx": FX_STYLES, "extras": EXTRA_ITEMS, "packs": PACKS}[tab]


def rarity(price):
  for th, name, col in RARITIES:
    if price >= th:
      return name, col
  return RARITIES[-1][1], RARITIES[-1][2]


def total_wins():
  """Victòries contra el bot, sumant tots els jocs i nivells."""
  return sum(SAVE["records"][g][k][0] for g in GAMES for k in LEVELS)


def beat_level(level):
  """Has guanyat com a mínim una vegada a aquest nivell (o a un de superior)?"""
  return any(SAVE["records"][g][k][0] > 0
             for g in GAMES for k in LEVELS[LEVELS.index(level):])


def req_check(req):
  """(compleix, text) d'un requisit de progrés."""
  if not req:
    return True, ""
  if req[0] == "wins":
    w = total_wins()
    return w >= req[1], f"Cal guanyar {req[1]} partides al bot ({min(w, req[1])}/{req[1]})"
  return beat_level(req[1]), f"Cal guanyar al nivell {LEVEL_INFO[req[1]][0].capitalize()}"


def deal_key():
  """L'oferta del dia: un element de la botiga amb un 30% de descompte."""
  pool = [(t, k) for t in COSMETIC_TABS for k, it in shop_table(t).items()
          if it["price"] > 0]
  return random.Random(time.strftime("%Y-%m-%d")).choice(pool)


def is_owned(tab, key):
  if tab == "extras":
    return False
  if tab == "packs":
    return not pack_unowned(PACKS[key])
  return key in SAVE["owned"][tab]


def pack_unowned(pack):
  return [(t, k) for t, k in pack["items"] if k not in SAVE["owned"][t]]


def pack_price(pack):
  total = sum(shop_table(t)[k]["price"] for t, k in pack_unowned(pack))
  return int(round(total * (1 - pack["disc"]) / 5.0)) * 5


def pack_req(pack):
  for t, k in pack_unowned(pack):
    ok, why = req_check(shop_table(t)[k].get("req"))
    if not ok:
      return False, f"{shop_table(t)[k]['name']}: {why}"
  return True, ""


def price_of(tab, key):
  """(preu, preu original o None si no hi ha descompte)."""
  item = shop_table(tab)[key]
  if tab == "packs":
    return pack_price(item), None
  base = item["price"]
  if base > 0 and (tab, key) == deal_key() and key not in SAVE["owned"].get(tab, []):
    return max(5, int(round(base * (1 - DEAL_DISCOUNT) / 5.0)) * 5), base
  return base, None


def base_price(tab, key):
  item = shop_table(tab)[key]
  return pack_price(item) if tab == "packs" else item["price"]


def shop_primary(tab, key):
  """(text del botó principal, activat) per a la finestra de detall."""
  item = shop_table(tab)[key]
  price, _orig = price_of(tab, key)
  pts = SAVE["points"]
  if tab == "extras":
    if SAVE["items"][item["field"]] + item["amount"] > STOCK_MAX:
      return "Ja en tens molts", False
    return f"Comprar ({price})", pts >= price
  if tab == "packs":
    if not pack_unowned(item):
      return "Ja tens el pack", False
    if not pack_req(item)[0]:
      return "Bloquejat", False
    return f"Comprar pack ({price})", pts >= price
  if key in SAVE["owned"][tab]:
    if SAVE["equipped"][tab] == key:
      return "Equipat", False
    return "Equipar", True
  if not req_check(item.get("req"))[0]:
    return "Bloquejat", False
  return f"Comprar ({price})", pts >= price


def wrap_text(text, font, maxw):
  lines, cur = [], ""
  for w in text.split():
    t = (cur + " " + w).strip()
    if font.render(t, True, (0, 0, 0)).get_width() <= maxw:
      cur = t
    else:
      lines.append(cur)
      cur = w
  if cur:
    lines.append(cur)
  return lines




# ---------------------------------------------------------------
# DESAT (localStorage al navegador, fitxer a l'ordinador)
# ---------------------------------------------------------------

SAVE_KEY = "jocs_de_taula_save_v1"
SAVE_FILE = os.path.join(os.path.expanduser("~"), ".jocs_de_taula.json")
GAMES = ("morris", "c4", "chess", "go")


def default_save():
  return {
      "points": 0,
      "difficulty": "hard",
      "rules": {"pieces": 7, "fly": True, "diag": False},
      "unlocked": False,
      "owned": {"boards": ["classic"], "pieces": ["classic"],
                "marks": ["orange"], "fx": ["none"]},
      "equipped": {"boards": "classic", "pieces": "classic",
                   "marks": "orange", "fx": "none"},
      "items": {"hints": 0, "undos": 0, "double": 0},
      "records": {
          g: {k: [0, 0, 0] for k in LEVELS + ("local",)} for g in GAMES
      },
  }


def load_save():
  data = default_save()
  try:
    raw = None
    if HAS_JS:
      raw = js.window.localStorage.getItem(SAVE_KEY)
      raw = None if raw is None else str(raw)
    elif os.path.exists(SAVE_FILE):
      with open(SAVE_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
    if raw and raw not in ("null", "None", "undefined"):
      loaded = json.loads(raw)
      data["points"] = int(loaded.get("points", 0))
      if loaded.get("difficulty") in LEVELS:
        data["difficulty"] = loaded["difficulty"]
      if isinstance(loaded.get("rules"), dict):
        data["rules"].update(loaded["rules"])
      for g in GAMES:
        for k in LEVELS + ("local",):
          rec = loaded.get("records", {}).get(g, {}).get(k)
          if isinstance(rec, list) and len(rec) == 3:
            data["records"][g][k] = [int(x) for x in rec]
      tables = (("boards", BOARD_THEMES), ("pieces", PIECE_STYLES),
                ("marks", MARK_STYLES), ("fx", FX_STYLES))
      owned = loaded.get("owned")
      if isinstance(owned, dict):
        for k, table in tables:
          lst = owned.get(k)
          if isinstance(lst, list):
            first = next(iter(table))
            data["owned"][k] = [first] + [
                x for x in dict.fromkeys(lst) if x in table and x != first]
      eq = loaded.get("equipped")
      if isinstance(eq, dict):
        for k, table in tables:
          if eq.get(k) in table and eq[k] in data["owned"][k]:
            data["equipped"][k] = eq[k]
      its = loaded.get("items")
      if isinstance(its, dict):
        for k in data["items"]:
          try:
            data["items"][k] = max(0, min(STOCK_MAX, int(its.get(k, 0))))
          except Exception:
            pass
      data["unlocked"] = bool(loaded.get("unlocked", False))
  except Exception:
    pass
  if data["points"] >= UNLOCK_POINTS:
    data["unlocked"] = True
  # si el nivell desat és l'impossible però encara està bloquejat, torna al difícil
  if data["difficulty"] == "impossible" and not data["unlocked"]:
    data["difficulty"] = "hard"
  return data


def write_save():
  try:
    raw = json.dumps(SAVE)
    if HAS_JS:
      js.window.localStorage.setItem(SAVE_KEY, raw)
    else:
      with open(SAVE_FILE, "w", encoding="utf-8") as f:
        f.write(raw)
  except Exception:
    pass


SAVE = load_save()


# ---------------------------------------------------------------
# TRES EN RATLLA: TAULER I REGLES
# ---------------------------------------------------------------

POINTS_CONFIG = [
    (0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 1, 2), (0, 2, 2), (0, 2, 1),
    (0, 2, 0), (0, 1, 0),
    (1, 0, 0), (1, 0, 1), (1, 0, 2), (1, 1, 2), (1, 2, 2), (1, 2, 1),
    (1, 2, 0), (1, 1, 0),
    (2, 0, 0), (2, 0, 1), (2, 0, 2), (2, 1, 2), (2, 2, 2), (2, 2, 1),
    (2, 2, 0), (2, 1, 0),
]


def point_to_str(p):
  return f"{p[0]}_{p[1]}_{p[2]}"


def str_to_point(s):
  try:
    parts = s.split("_")
    return (int(parts[0]), int(parts[1]), int(parts[2]))
  except Exception:
    return None


def get_screen_coords(point):
  layer, r, c = point
  margin = 50 + layer * 70
  size = BOARD_SIZE - 2 * margin
  x = OFFSET_X + margin + c * (size // 2)
  y = OFFSET_Y + margin + r * (size // 2)
  return int(x), int(y)


POINT_POSITIONS = {p: get_screen_coords(p) for p in POINTS_CONFIG}

ADJACENCY = {
    (0, 0, 0): [(0, 0, 1), (0, 1, 0)],
    (0, 0, 1): [(0, 0, 0), (0, 0, 2), (1, 0, 1)],
    (0, 0, 2): [(0, 0, 1), (0, 1, 2)],
    (0, 1, 2): [(0, 0, 2), (0, 2, 2), (1, 1, 2)],
    (0, 2, 2): [(0, 1, 2), (0, 2, 1)],
    (0, 2, 1): [(0, 2, 2), (0, 2, 0), (1, 2, 1)],
    (0, 2, 0): [(0, 2, 1), (0, 1, 0)],
    (0, 1, 0): [(0, 2, 0), (0, 0, 0), (1, 1, 0)],
    (1, 0, 0): [(1, 0, 1), (1, 1, 0)],
    (1, 0, 1): [(1, 0, 0), (1, 0, 2), (0, 0, 1), (2, 0, 1)],
    (1, 0, 2): [(1, 0, 1), (1, 1, 2)],
    (1, 1, 2): [(1, 0, 2), (1, 2, 2), (0, 1, 2), (2, 1, 2)],
    (1, 2, 2): [(1, 1, 2), (1, 2, 1)],
    (1, 2, 1): [(1, 2, 2), (1, 2, 0), (0, 2, 1), (2, 2, 1)],
    (1, 2, 0): [(1, 2, 1), (1, 1, 0)],
    (1, 1, 0): [(1, 2, 0), (1, 0, 0), (0, 1, 0), (2, 1, 0)],
    (2, 0, 0): [(2, 0, 1), (2, 1, 0)],
    (2, 0, 1): [(2, 0, 0), (2, 0, 2), (1, 0, 1)],
    (2, 0, 2): [(2, 0, 1), (2, 1, 2)],
    (2, 1, 2): [(2, 0, 2), (2, 2, 2), (1, 1, 2)],
    (2, 2, 2): [(2, 1, 2), (2, 2, 1)],
    (2, 2, 1): [(2, 2, 2), (2, 2, 0), (1, 2, 1)],
    (2, 2, 0): [(2, 2, 1), (2, 1, 0)],
    (2, 1, 0): [(2, 2, 0), (2, 0, 0), (1, 1, 0)],
}

LINES_OF_THREE = [
    [(0, 0, 0), (0, 0, 1), (0, 0, 2)],
    [(0, 2, 0), (0, 2, 1), (0, 2, 2)],
    [(1, 0, 0), (1, 0, 1), (1, 0, 2)],
    [(1, 2, 0), (1, 2, 1), (1, 2, 2)],
    [(2, 0, 0), (2, 0, 1), (2, 0, 2)],
    [(2, 2, 0), (2, 2, 1), (2, 2, 2)],
    [(0, 1, 0), (1, 1, 0), (2, 1, 0)],
    [(2, 1, 2), (1, 1, 2), (0, 1, 2)],
    [(0, 0, 0), (0, 1, 0), (0, 2, 0)],
    [(0, 0, 2), (0, 1, 2), (0, 2, 2)],
    [(1, 0, 0), (1, 1, 0), (1, 2, 0)],
    [(1, 0, 2), (1, 1, 2), (1, 2, 2)],
    [(2, 0, 0), (2, 1, 0), (2, 2, 0)],
    [(2, 0, 2), (2, 1, 2), (2, 2, 2)],
    [(0, 0, 1), (1, 0, 1), (2, 0, 1)],
    [(2, 2, 1), (1, 2, 1), (0, 2, 1)],
]

# Variant amb diagonals: les cantonades dels tres quadrats formen línies
CORNERS = [(0, 0), (0, 2), (2, 0), (2, 2)]
DIAG_LINES = [[(0, r, c), (1, r, c), (2, r, c)] for r, c in CORNERS]


def _build_adjacency(diag):
  adj = {p: list(v) for p, v in ADJACENCY.items()}
  if diag:
    for r, c in CORNERS:
      for a, b in (((0, r, c), (1, r, c)), ((1, r, c), (2, r, c))):
        adj[a].append(b)
        adj[b].append(a)
  return adj


_RULE_TABLES = {
    False: (LINES_OF_THREE, _build_adjacency(False)),
    True: (LINES_OF_THREE + DIAG_LINES, _build_adjacency(True)),
}


class Rules:
  """Regles configurables de Tres en ratlla."""

  def __init__(self, pieces=7, fly=True, diag=False):
    self.pieces = pieces if pieces in (5, 7, 9) else 7
    self.fly = bool(fly)
    self.diag = bool(diag)

  @property
  def lines(self):
    return _RULE_TABLES[self.diag][0]

  @property
  def adj(self):
    return _RULE_TABLES[self.diag][1]

  def to_dict(self):
    return {"pieces": self.pieces, "fly": self.fly, "diag": self.diag}

  @staticmethod
  def from_dict(d):
    return Rules(d.get("pieces", 7), d.get("fly", True), d.get("diag", False))


def can_move_to(origin, target, board, rules):
  """Una fitxa pot anar de 'origin' a 'target' (que ha d'estar buit).

  Amb vol lliure, a qualsevol punt buit; si no, només als adjacents.
  """
  if board[target] is not None:
    return False
  if rules.fly:
    return True
  return target in rules.adj[origin]


# ---------------------------------------------------------------
# ONLINE
# ---------------------------------------------------------------


def check_firebase_state():
  if not HAS_JS:
    return None
  try:
    raw = js.window.latestGameState
    if raw and str(raw) != "null":
      return json.loads(str(raw))
  except Exception:
    pass
  return None


def push_firebase_state(data):
  if not HAS_JS:
    return
  try:
    js.window.sendGameState(json.dumps(data))
  except Exception:
    pass


def detect_online_role():
  """Mira la URL (també la de la pàgina contenidora): si hi surt 'black', jugues amb negres."""
  if not HAS_JS:
    return "W"

  try:
    js_detect_role = """
        (function() {
            try {
                var url = window.location.href + " " + window.location.hash;
                if (window.top) url += " " + window.top.location.href + " " + window.top.location.hash;
                if (window.parent) url += " " + window.parent.location.href + " " + window.parent.location.hash;
                return url;
            } catch(e) {
                return window.location.href;
            }
        })()
        """
    full_url = str(js.window.eval(js_detect_role)).lower()
    return "B" if "black" in full_url else "W"
  except Exception:
    return "W"


# ---------------------------------------------------------------
# TRES EN RATLLA: JOC
# ---------------------------------------------------------------


class Morris:

  def __init__(self, rules=None, track=False):
    self.rules = rules or Rules()
    self.board = {p: None for p in POINTS_CONFIG}
    self.turn = "W"
    self.unplaced = {"W": self.rules.pieces, "B": self.rules.pieces}
    self.selected_point = None
    self.winner = None
    self.winning_line = None
    self.blocked = False          # guanya perquè l'altre no pot moure
    self.move_count = 0           # versió, per evitar race conditions online
    self.last_move = None         # (origen|None, destí)
    self.track = track            # controla taules per repetició
    self.draw = False
    self.history = {}
    self.stack = []               # per desfer

  # ---------- online ----------
  def to_dict(self):
    last = None
    if self.last_move:
      src, dst = self.last_move
      last = [point_to_str(src) if src else "", point_to_str(dst)]
    return {
        "board": {
            point_to_str(k): v for k, v in self.board.items() if v is not None
        },
        "turn": self.turn,
        "unplaced": self.unplaced,
        "winner": self.winner,
        "winning_line": (
            [point_to_str(p) for p in self.winning_line]
            if self.winning_line else None
        ),
        "move_count": self.move_count,
        "last": last,
    }

  def from_dict(self, data):
    if not data or not isinstance(data, dict):
      return

    remote_count = int(data.get("move_count", 0))

    # Només actualitza si la dada rebuda és MÉS RECENT que la local
    if remote_count <= self.move_count and self.move_count > 0:
      return

    self.move_count = remote_count

    new_board = {p: None for p in POINTS_CONFIG}
    raw_board = data.get("board")
    if isinstance(raw_board, dict):
      for k, v in raw_board.items():
        pt = str_to_point(k)
        if pt in new_board:
          new_board[pt] = v
    self.board = new_board

    self.turn = data.get("turn", "W")
    if self.turn not in ("W", "B"):
      self.turn = "W"

    raw_unplaced = data.get("unplaced")
    n = self.rules.pieces
    if isinstance(raw_unplaced, dict):
      self.unplaced = {
          "W": int(raw_unplaced.get("W", n)),
          "B": int(raw_unplaced.get("B", n)),
      }
    else:
      self.unplaced = {"W": n, "B": n}

    self.winner = data.get("winner", None)
    if self.winner not in ("W", "B"):
      self.winner = None

    raw_w_line = data.get("winning_line")
    if isinstance(raw_w_line, list):
      parsed_line = [
          str_to_point(p) for p in raw_w_line if str_to_point(p) is not None
      ]
      self.winning_line = parsed_line if len(parsed_line) == 3 else None
    else:
      self.winning_line = None

    self.last_move = None
    raw_last = data.get("last")
    if isinstance(raw_last, list) and len(raw_last) == 2:
      dst = str_to_point(raw_last[1])
      src = str_to_point(raw_last[0]) if raw_last[0] else None
      if dst in self.board:
        self.last_move = (src, dst)

    self.selected_point = None

  # ---------- desfer ----------
  def snapshot(self):
    return dict(
        board=dict(self.board), turn=self.turn, unplaced=dict(self.unplaced),
        winner=self.winner, winning_line=self.winning_line,
        move_count=self.move_count, draw=self.draw,
        history=dict(self.history), last_move=self.last_move,
        blocked=self.blocked,
    )

  def undo_one(self):
    if not self.stack:
      return False
    s = self.stack.pop()
    self.board = s["board"]
    self.turn = s["turn"]
    self.unplaced = s["unplaced"]
    self.winner = s["winner"]
    self.winning_line = s["winning_line"]
    self.move_count = s["move_count"]
    self.draw = s["draw"]
    self.history = s["history"]
    self.last_move = s["last_move"]
    self.blocked = s["blocked"]
    self.selected_point = None
    return True

  # ---------- regles ----------
  def check_win(self, player):
    for line in self.rules.lines:
      if all(self.board[p] == player for p in line):
        self.winning_line = line
        return True
    return False

  def has_moves(self, player):
    if not any(v is None for v in self.board.values()):
      return False
    if self.unplaced[player] > 0:
      return True
    for p in POINTS_CONFIG:
      if self.board[p] == player:
        if self.rules.fly:
          return True
        if any(self.board[q] is None for q in self.rules.adj[p]):
          return True
    return False

  def register_position(self):
    """Compta les repeticions de posició i declara taules si cal."""
    if not self.track or self.winner:
      return
    key = (
        tuple(self.board[p] for p in POINTS_CONFIG),
        self.turn,
        self.unplaced["W"],
        self.unplaced["B"],
    )
    self.history[key] = self.history.get(key, 0) + 1
    if self.history[key] >= REPETITIONS_FOR_DRAW or self.move_count >= MAX_MOVES:
      self.draw = True

  def handle_click(self, point, my_role):
    if self.winner or self.draw or self.turn != my_role:
      return False

    snap = self.snapshot()
    opponent = "B" if self.turn == "W" else "W"
    moved = False
    src = None

    # FASE 1: COL·LOCACIÓ DE FITXES
    if self.unplaced[self.turn] > 0:
      if self.board[point] is None:
        self.board[point] = self.turn
        self.unplaced[self.turn] -= 1
        if self.check_win(self.turn):
          self.winner = self.turn
        else:
          self.turn = opponent
        moved = True

    # FASE 2: MOVIMENT DE FITXES
    else:
      if self.selected_point is None:
        if self.board[point] == self.turn:
          self.selected_point = point
      else:
        if point == self.selected_point:
          self.selected_point = None
        elif self.board[point] == self.turn:
          self.selected_point = point
        elif can_move_to(self.selected_point, point, self.board, self.rules):
          src = self.selected_point
          self.board[point] = self.turn
          self.board[src] = None
          self.selected_point = None
          if self.check_win(self.turn):
            self.winner = self.turn
          else:
            self.turn = opponent
          moved = True

    if moved:
      self.last_move = (src, point)
      if not self.winner and not self.has_moves(opponent):
        self.winner = my_role      # l'altre es queda bloquejat
        self.blocked = True
      self.move_count += 1
      self.stack.append(snap)
      self.register_position()

    return moved


# ---------------------------------------------------------------
# TRES EN RATLLA: BOT (minimax + alfa-beta + aprofundiment iteratiu)
# ---------------------------------------------------------------

IDX = {p: i for i, p in enumerate(POINTS_CONFIG)}
WIN = 10000
INF = 10 ** 9
_SYM = (None, "W", "B")
_IDX_CACHE = {}


def idx_tables(rules):
  if rules.diag not in _IDX_CACHE:
    lines = [tuple(IDX[p] for p in l) for l in rules.lines]
    lop = [[l for l in lines if i in l] for i in range(24)]
    adj = [[IDX[q] for q in rules.adj[p]] for p in POINTS_CONFIG]
    _IDX_CACHE[rules.diag] = (lines, lop, adj)
  return _IDX_CACHE[rules.diag]


class Timeout(Exception):
  pass


class Bot:
  """1 = blanques, 2 = negres.

  think: segons màxims de reflexió. max_depth: profunditat màxima.
  blunder: probabilitat de fer una jugada a l'atzar (nivells fàcils).
  """

  def __init__(self, think=0.8, max_depth=12, blunder=0.0):
    self.think = think
    self.max_depth = max_depth
    self.blunder = blunder
    self.b = [0] * 24
    self.unp = {1: 7, 2: 7}
    self.deadline = 0
    self.nodes = 0
    self.fly = True
    self.lines, self.lop, self.adj = idx_tables(Rules())

  # ---------- regles ----------
  def reachable(self, pl, e, line):
    if self.unp[pl] > 0 or self.fly:
      return True
    return any(self.b[n] == pl and n not in line for n in self.adj[e])

  def win_points(self, pl):
    """Punts buits on 'pl' completaria una línia el proper torn."""
    pts = set()
    b = self.b
    for line in self.lines:
      cnt, empty = 0, None
      for i in line:
        if b[i] == pl:
          cnt += 1
        elif b[i] == 0:
          empty = i
      if cnt == 2 and empty is not None and self.reachable(pl, empty, line):
        pts.add(empty)
    return pts

  def moves(self, pl, only=None):
    b = self.b
    empt = [i for i in range(24) if b[i] == 0 and (only is None or i == only)]
    if self.unp[pl] > 0:
      return [(None, d) for d in empt]
    res = []
    for s in range(24):
      if b[s] == pl:
        if self.fly:
          res.extend((s, d) for d in empt)
        else:
          res.extend((s, d) for d in self.adj[s]
                     if b[d] == 0 and (only is None or d == only))
    return res

  def apply(self, pl, m):
    s, d = m
    if s is None:
      self.unp[pl] -= 1
    else:
      self.b[s] = 0
    self.b[d] = pl
    return any(all(self.b[i] == pl for i in l) for l in self.lop[d])

  def undo(self, pl, m):
    s, d = m
    self.b[d] = 0
    if s is None:
      self.unp[pl] += 1
    else:
      self.b[s] = pl

  def key_after(self, pl, m):
    """Clau de posició (la mateixa que fa servir Morris.register_position)."""
    self.apply(pl, m)
    key = (
        tuple(_SYM[v] for v in self.b),
        "B" if pl == 1 else "W",
        self.unp[1],
        self.unp[2],
    )
    self.undo(pl, m)
    return key

  # ---------- heurística ----------
  def order(self, pl, m):
    s_, d = m
    sc = 0
    for l in self.lop[d]:
      a = o = 0
      for i in l:
        if i == s_:
          continue
        v = self.b[i]
        if v == pl:
          a += 1
        elif v:
          o += 1
      if o == 0:
        sc += (1, 4, 0)[a]
      elif a == 0:
        sc += (0, 2, 3)[o]
    return sc

  def evaluate(self, pl):
    s = 0
    b = self.b
    for l in self.lines:
      a = o = 0
      for i in l:
        v = b[i]
        if v == pl:
          a += 1
        elif v:
          o += 1
      if o == 0:
        s += (0, 2, 6, 0)[a]
      elif a == 0:
        s -= (0, 2, 6, 0)[o]
    return s

  # ---------- cerca ----------
  def nega(self, pl, depth, alpha, beta, ply):
    self.nodes += 1
    if self.nodes & 255 == 0 and time.time() > self.deadline:
      raise Timeout
    opp = 3 - pl
    if self.win_points(pl):
      return WIN - ply
    threats = self.win_points(opp)
    if len(threats) >= 2:
      return -(WIN - ply - 1)
    if depth == 0:
      return self.evaluate(pl)
    only = next(iter(threats)) if threats else None
    mv = self.moves(pl, only)
    if not mv:
      return -(WIN - ply - 1)
    mv.sort(key=lambda m: -self.order(pl, m))
    best = -INF
    for m in mv:
      self.apply(pl, m)
      sc = -self.nega(opp, depth - 1, -beta, -alpha, ply + 1)
      self.undo(pl, m)
      if sc > best:
        best = sc
        if sc > alpha:
          alpha = sc
          if alpha >= beta:
            break
    return best

  def choose(self, game, role):
    """Retorna (origen|None, destí) en índexs, o None si no pot moure."""
    pl = 1 if role == "W" else 2
    opp = 3 - pl
    self.fly = game.rules.fly
    self.lines, self.lop, self.adj = idx_tables(game.rules)
    self.b = [0] * 24
    for p, v in game.board.items():
      if v:
        self.b[IDX[p]] = 1 if v == "W" else 2
    self.unp = {1: game.unplaced["W"], 2: game.unplaced["B"]}

    mv = self.moves(pl)
    if not mv:
      return None
    random.shuffle(mv)                       # varietat entre jugades iguals
    for m in mv:                             # victòria immediata
      won = self.apply(pl, m)
      self.undo(pl, m)
      if won:
        return m
    if self.blunder and random.random() < self.blunder:
      return random.choice(mv)               # nivells fàcils: despistades
    threats = self.win_points(opp)
    if len(threats) == 1:                    # bloqueig obligat
      forced = [m for m in mv if m[1] in threats]
      if forced:
        mv = forced
    if len(mv) == 1:
      return mv[0]
    mv.sort(key=lambda m: -self.order(pl, m))

    # Evitar taules: una jugada que repeteix la posició per tercer cop
    # val DRAW_SCORE (negatiu), i les que s'hi acosten tenen una petita
    # penalització perquè el bot no es posi a fer voltes.
    hist = getattr(game, "history", {})
    pen = {}
    for m in mv:
      c = hist.get(self.key_after(pl, m), 0)
      pen[m] = None if c + 1 >= REPETITIONS_FOR_DRAW else c * 3

    best = mv[0]
    snap = (self.b[:], dict(self.unp))
    self.deadline = time.time() + self.think
    self.nodes = 0
    for depth in range(1, self.max_depth + 1):
      try:
        cur, cur_sc, alpha = None, -INF, -INF
        for m in mv:
          if pen[m] is None:
            sc = DRAW_SCORE
          else:
            self.apply(pl, m)
            sc = -self.nega(opp, depth - 1, -INF, -alpha, 1) - pen[m]
            self.undo(pl, m)
          if sc > cur_sc:
            cur_sc, cur = sc, m
            alpha = max(alpha, sc)
        best = cur
        mv.remove(cur)
        mv.insert(0, cur)                    # el millor primer a la següent profunditat
        if abs(cur_sc) >= WIN - 100:         # victòria/derrota forçada trobada
          break
      except Timeout:
        self.b, self.unp = snap
        break
    return best

  def play(self, game, role):
    m = self.choose(game, role)
    if m is None:
      return
    s, d = m
    if s is not None:
      game.handle_click(POINTS_CONFIG[s], role)   # selecciona la fitxa
    game.handle_click(POINTS_CONFIG[d], role)     # i la mou / col·loca


# ---------------------------------------------------------------
# 4 EN RATLLA: JOC
# ---------------------------------------------------------------

C4_COLS, C4_ROWS = 7, 6


class Connect4:
  """grid[col][fila], fila 0 = a baix. 1 = vermells (primer), 2 = grocs."""

  def __init__(self):
    self.grid = [[0] * C4_ROWS for _ in range(C4_COLS)]
    self.turn = 1
    self.winner = None
    self.win_cells = None
    self.draw = False
    self.move_count = 0
    self.last_move = None
    self.stack = []

  def snapshot(self):
    return dict(grid=[col[:] for col in self.grid], turn=self.turn,
                move_count=self.move_count, last_move=self.last_move)

  def undo_one(self):
    if not self.stack:
      return False
    s = self.stack.pop()
    self.grid = s["grid"]
    self.turn = s["turn"]
    self.move_count = s["move_count"]
    self.last_move = s["last_move"]
    self.winner = None
    self.win_cells = None
    self.draw = False
    return True

  def legal(self, c):
    return 0 <= c < C4_COLS and self.grid[c][C4_ROWS - 1] == 0

  def find_four(self, c, r, pl):
    for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
      cells = [(c, r)]
      for sgn in (1, -1):
        x, y = c + dc * sgn, r + dr * sgn
        while 0 <= x < C4_COLS and 0 <= y < C4_ROWS and self.grid[x][y] == pl:
          cells.append((x, y))
          x, y = x + dc * sgn, y + dr * sgn
      if len(cells) >= 4:
        return cells
    return None

  def drop(self, c, pl):
    if self.winner or self.draw or pl != self.turn or not self.legal(c):
      return False
    snap = self.snapshot()
    r = self.grid[c].index(0)
    self.grid[c][r] = pl
    self.last_move = (c, r)
    cells = self.find_four(c, r, pl)
    if cells:
      self.winner = pl
      self.win_cells = cells
    elif all(self.grid[x][C4_ROWS - 1] != 0 for x in range(C4_COLS)):
      self.draw = True
    else:
      self.turn = 3 - pl
    self.move_count += 1
    self.stack.append(snap)
    return True


# ---------------------------------------------------------------
# 4 EN RATLLA: BOT (bitboards + negamax + TT + aprofundiment iteratiu)
# ---------------------------------------------------------------

C4_H = C4_ROWS + 1
C4_ORDER = [3, 2, 4, 1, 5, 0, 6]
C4_COLMASK = [((1 << C4_H) - 1) << (c * C4_H) for c in range(C4_COLS)]
C4_WSCORE = (0, 1, 6, 30, 0)

try:
  _popcount = int.bit_count
except AttributeError:
  def _popcount(x):
    return bin(x).count("1")


def _c4_windows():
  res = []
  for c in range(C4_COLS):
    for r in range(C4_ROWS):
      for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
        cells = [(c + dc * k, r + dr * k) for k in range(4)]
        if all(0 <= x < C4_COLS and 0 <= y < C4_ROWS for x, y in cells):
          res.append(sum(1 << (x * C4_H + y) for x, y in cells))
  return res


C4_WINDOWS = _c4_windows()
C4_CENTER = sum(1 << (3 * C4_H + r) for r in range(C4_ROWS))


def c4_has4(p):
  m = p & (p >> C4_H)
  if m & (m >> (2 * C4_H)):
    return True
  m = p & (p >> (C4_H - 1))
  if m & (m >> (2 * (C4_H - 1))):
    return True
  m = p & (p >> (C4_H + 1))
  if m & (m >> (2 * (C4_H + 1))):
    return True
  m = p & (p >> 1)
  return bool(m & (m >> 2))


class C4Bot:

  def __init__(self, think=0.8, max_depth=14, blunder=0.0):
    self.think = think
    self.max_depth = max_depth
    self.blunder = blunder
    self.deadline = 0
    self.nodes = 0
    self.tt = {}

  def evaluate(self, me, opp):
    s = (_popcount(me & C4_CENTER) - _popcount(opp & C4_CENTER)) * 3
    for w in C4_WINDOWS:
      a = _popcount(me & w)
      o = _popcount(opp & w)
      if o == 0:
        s += C4_WSCORE[a]
      elif a == 0:
        s -= C4_WSCORE[o]
    return s

  def nega(self, me, opp, mask, depth, alpha, beta, ply):
    self.nodes += 1
    if self.nodes & 255 == 0 and time.time() > self.deadline:
      raise Timeout
    moves = []
    for c in C4_ORDER:
      if not ((mask >> (c * C4_H + C4_ROWS - 1)) & 1):
        b = (mask + (1 << (c * C4_H))) & C4_COLMASK[c]
        if c4_has4(me | b):
          return WIN - ply
        moves.append(b)
    if not moves:
      return 0
    if depth == 0:
      return self.evaluate(me, opp)

    key = (me, mask)
    alpha0 = alpha
    e = self.tt.get(key)
    if e is not None and e[0] >= depth:
      flag, val = e[1], e[2]
      if flag == 0:
        return val
      if flag == 1:
        alpha = max(alpha, val)
      else:
        beta = min(beta, val)
      if alpha >= beta:
        return val

    best = -INF
    for b in moves:
      sc = -self.nega(opp, me | b, mask | b, depth - 1, -beta, -alpha, ply + 1)
      if sc > best:
        best = sc
        if sc > alpha:
          alpha = sc
          if alpha >= beta:
            break
    if abs(best) < WIN - 100:
      flag = 2 if best <= alpha0 else (1 if best >= beta else 0)
      self.tt[key] = (depth, flag, best)
    return best

  def choose(self, game, pl):
    opp = 3 - pl
    p = [0, 0, 0]
    mask = 0
    for c in range(C4_COLS):
      for r in range(C4_ROWS):
        v = game.grid[c][r]
        if v:
          bit = 1 << (c * C4_H + r)
          p[v] |= bit
          mask |= bit

    moves = [c for c in C4_ORDER if game.legal(c)]
    if not moves:
      return None

    def bit_of(c):
      return (mask + (1 << (c * C4_H))) & C4_COLMASK[c]

    for c in moves:                          # victòria immediata
      if c4_has4(p[pl] | bit_of(c)):
        return c
    if self.blunder and random.random() < self.blunder:
      return random.choice(moves)
    for c in moves:                          # bloqueig obligat
      if c4_has4(p[opp] | bit_of(c)):
        return c
    if len(moves) == 1:
      return moves[0]

    self.tt = {}
    self.nodes = 0
    self.deadline = time.time() + self.think
    best = moves[0]
    for depth in range(1, self.max_depth + 1):
      try:
        cur, cur_sc, alpha = None, -INF, -INF
        for c in moves:
          b = bit_of(c)
          sc = -self.nega(p[opp], p[pl] | b, mask | b, depth - 1, -INF, -alpha, 1)
          if sc > cur_sc:
            cur_sc, cur = sc, c
            alpha = max(alpha, sc)
        best = cur
        moves.remove(cur)
        moves.insert(0, cur)
        if abs(cur_sc) >= WIN - 100:
          break
      except Timeout:
        break
    return best

  def play(self, game, pl):
    c = self.choose(game, pl)
    if c is not None:
      game.drop(c, pl)


BOT_PARAMS = {
    "morris": {
        "easy": dict(think=0.05, max_depth=1, blunder=0.4),
        "medium": dict(think=0.2, max_depth=3, blunder=0.1),
        "hard": dict(think=0.5 if HAS_JS else 0.8, max_depth=12),
        "impossible": dict(think=1.5 if HAS_JS else 3.0, max_depth=40),
    },
    "c4": {
        "easy": dict(think=0.05, max_depth=2, blunder=0.35),
        "medium": dict(think=0.2, max_depth=4, blunder=0.08),
        "hard": dict(think=0.5 if HAS_JS else 0.8, max_depth=14),
        "impossible": dict(think=1.5 if HAS_JS else 3.0, max_depth=42),
    },
    "chess": {
        "easy": dict(think=0.05, max_depth=1, blunder=0.35),
        "medium": dict(think=0.3, max_depth=2, blunder=0.08),
        "hard": dict(think=0.6 if HAS_JS else 1.0, max_depth=4),
        "impossible": dict(think=1.5 if HAS_JS else 3.0, max_depth=8),
    },
    "go": {
        "easy": dict(think=0, blunder=0.3, playouts=False),
        "medium": dict(think=0, blunder=0.06, playouts=False),
        "hard": dict(think=0.6 if HAS_JS else 1.0, blunder=0, playouts=True, top=6),
        "impossible": dict(think=1.5 if HAS_JS else 3.0, blunder=0, playouts=True, top=8),
    },
}

# La pista fa servir sempre el bot més fort, així és la millor jugada possible
HINT_PARAMS = {k: BOT_PARAMS[k]["impossible"] for k in BOT_PARAMS}


# ---------------------------------------------------------------
# ESCACS: JOC (regles completes, sense promoció triada: sempre dama)
# ---------------------------------------------------------------
# Tauler de 64 caselles: índex = fila * 8 + columna, fila 0 = dalt (negres).
# Peces: 1 peó, 2 cavall, 3 alfil, 4 torre, 5 dama, 6 rei.
# Positiu = blanques, negatiu = negres.

CH_KNIGHT = [[] for _ in range(64)]
CH_KING = [[] for _ in range(64)]
CH_BISHOP_RAYS = [[] for _ in range(64)]
CH_ROOK_RAYS = [[] for _ in range(64)]


def _init_chess_tables():
  for sq in range(64):
    r, c = sq >> 3, sq & 7
    for dr, dc in ((1, 2), (2, 1), (-1, 2), (-2, 1),
                   (1, -2), (2, -1), (-1, -2), (-2, -1)):
      rr, cc = r + dr, c + dc
      if 0 <= rr < 8 and 0 <= cc < 8:
        CH_KNIGHT[sq].append(rr * 8 + cc)
    for dr in (-1, 0, 1):
      for dc in (-1, 0, 1):
        if dr or dc:
          rr, cc = r + dr, c + dc
          if 0 <= rr < 8 and 0 <= cc < 8:
            CH_KING[sq].append(rr * 8 + cc)
    for rays, dirs in (
        (CH_BISHOP_RAYS, ((1, 1), (1, -1), (-1, 1), (-1, -1))),
        (CH_ROOK_RAYS, ((1, 0), (-1, 0), (0, 1), (0, -1)))):
      for dr, dc in dirs:
        ray = []
        rr, cc = r + dr, c + dc
        while 0 <= rr < 8 and 0 <= cc < 8:
          ray.append(rr * 8 + cc)
          rr += dr
          cc += dc
        if ray:
          rays[sq].append(ray)


_init_chess_tables()

CH_START = ([-4, -2, -3, -5, -6, -3, -2, -4] + [-1] * 8 + [0] * 32
            + [1] * 8 + [4, 2, 3, 5, 6, 3, 2, 4])

# drets d'enroc: 1 = rei blanc, 2 = dama blanca, 4 = rei negre, 8 = dama negra
CH_CMASK = [15] * 64
CH_CMASK[60] = 12
CH_CMASK[56] = 13
CH_CMASK[63] = 14
CH_CMASK[4] = 3
CH_CMASK[0] = 7
CH_CMASK[7] = 11

CH_VAL = (0, 100, 320, 330, 500, 900, 0)
CH_MATE = 100000
CH_LETTERS = {1: "P", 2: "C", 3: "A", 4: "T", 5: "D", 6: "R"}


def _build_pst():
  pst = {p: [0] * 64 for p in range(1, 7)}
  for sq in range(64):
    r, c = sq >> 3, sq & 7
    rr = 7 - r                                  # fila des del costat blanc
    cen = min(c, 7 - c) + min(rr, 7 - rr)       # 0..6: com de centrada
    pst[1][sq] = ((0, 0, 3, 8, 16, 28, 45, 0)[rr]
                  + (6 if c in (3, 4) and rr in (3, 4) else 0))
    pst[2][sq] = 8 * cen - 20
    pst[3][sq] = 4 * cen - 8
    pst[4][sq] = 10 if rr == 6 else 0
    pst[5][sq] = 2 * cen
    pst[6][sq] = (10 if c in (1, 2, 6) else 0) if rr == 0 else -15 * rr
  return pst


CH_PST_W = _build_pst()
CH_PST_B = {p: [t[sq ^ 56] for sq in range(64)] for p, t in CH_PST_W.items()}


class Chess:

  def __init__(self):
    self.board = list(CH_START)
    self.side = 1                  # 1 = blanques, -1 = negres
    self.castle = 15
    self.ep = -1                   # casella de captura al pas
    self.half = 0                  # semi-moviments sense captura ni peó
    self.kpos = [60, 4]            # reis: blanc, negre
    self.winner = None
    self.draw = False
    self.draw_reason = ""
    self.checkmate = False
    self.move_count = 0
    self.last_move = None          # (origen, destí)
    self.stack = []
    self.selected = None
    self.sel_moves = []
    self.history = {}
    self.register_position()

  @property
  def turn(self):
    return "W" if self.side == 1 else "B"

  @staticmethod
  def from_fen(fen):
    g = Chess()
    parts = fen.split()
    g.board = [0] * 64
    r = c = 0
    for ch in parts[0]:
      if ch == "/":
        r += 1
        c = 0
      elif ch.isdigit():
        c += int(ch)
      else:
        p = "pnbrqk".index(ch.lower()) + 1
        g.board[r * 8 + c] = p if ch.isupper() else -p
        if p == 6:
          g.kpos[0 if ch.isupper() else 1] = r * 8 + c
        c += 1
    g.side = 1 if parts[1] == "w" else -1
    cs = parts[2]
    g.castle = ((1 if "K" in cs else 0) | (2 if "Q" in cs else 0)
                | (4 if "k" in cs else 0) | (8 if "q" in cs else 0))
    g.ep = (-1 if parts[3] == "-"
            else (8 - int(parts[3][1])) * 8 + "abcdefgh".index(parts[3][0]))
    g.history = {}
    return g

  def clone(self):
    c = Chess.__new__(Chess)
    c.board = self.board[:]
    c.side = self.side
    c.castle = self.castle
    c.ep = self.ep
    c.half = self.half
    c.kpos = self.kpos[:]
    return c

  # ---------- atacs ----------
  def attacked(self, sq, by):
    """La casella 'sq' està atacada per les peces del color 'by' (1 / -1)?"""
    b = self.board
    c = sq & 7
    if by == 1:
      if sq < 56:
        if c > 0 and b[sq + 7] == 1:
          return True
        if c < 7 and b[sq + 9] == 1:
          return True
    else:
      if sq >= 8:
        if c > 0 and b[sq - 9] == -1:
          return True
        if c < 7 and b[sq - 7] == -1:
          return True
    n = 2 * by
    for t in CH_KNIGHT[sq]:
      if b[t] == n:
        return True
    k = 6 * by
    for t in CH_KING[sq]:
      if b[t] == k:
        return True
    bq, rq, qq = 3 * by, 4 * by, 5 * by
    for ray in CH_BISHOP_RAYS[sq]:
      for t in ray:
        q = b[t]
        if q:
          if q == bq or q == qq:
            return True
          break
    for ray in CH_ROOK_RAYS[sq]:
      for t in ray:
        q = b[t]
        if q:
          if q == rq or q == qq:
            return True
          break
    return False

  def in_check(self):
    return self.attacked(self.kpos[0 if self.side == 1 else 1], -self.side)

  # ---------- generació de moviments ----------
  def gen(self, caps=False):
    """Moviments pseudo-legals (f, t, promoció, marca). caps = només captures."""
    b = self.board
    s = self.side
    out = []
    for f in range(64):
      p = b[f]
      if p * s <= 0:
        continue
      a = p if p > 0 else -p
      if a == 1:
        d = -8 if s == 1 else 8
        pr_rank = 0 if s == 1 else 7
        t = f + d
        if b[t] == 0:
          if (t >> 3) == pr_rank:
            out.extend(((f, t, 5, 0), (f, t, 4, 0), (f, t, 3, 0), (f, t, 2, 0)))
          elif not caps:
            out.append((f, t, 0, 0))
            if (f >> 3) == (6 if s == 1 else 1) and b[t + d] == 0:
              out.append((f, t + d, 0, 4))
        c = f & 7
        for dc in (-1, 1):
          if (dc < 0 and c == 0) or (dc > 0 and c == 7):
            continue
          t = f + d + dc
          q = b[t]
          if q * s < 0:
            if (t >> 3) == pr_rank:
              out.extend(((f, t, 5, 0), (f, t, 4, 0), (f, t, 3, 0), (f, t, 2, 0)))
            else:
              out.append((f, t, 0, 0))
          elif t == self.ep:
            out.append((f, t, 0, 1))
      elif a == 2:
        for t in CH_KNIGHT[f]:
          q = b[t]
          if q * s <= 0 and not (caps and q == 0):
            out.append((f, t, 0, 0))
      elif a == 6:
        for t in CH_KING[f]:
          q = b[t]
          if q * s <= 0 and not (caps and q == 0):
            out.append((f, t, 0, 0))
        if not caps:
          if s == 1 and f == 60:
            if (self.castle & 1 and b[61] == 0 and b[62] == 0 and b[63] == 4
                and not self.attacked(60, -1) and not self.attacked(61, -1)
                and not self.attacked(62, -1)):
              out.append((60, 62, 0, 2))
            if (self.castle & 2 and b[59] == 0 and b[58] == 0 and b[57] == 0
                and b[56] == 4 and not self.attacked(60, -1)
                and not self.attacked(59, -1) and not self.attacked(58, -1)):
              out.append((60, 58, 0, 3))
          elif s == -1 and f == 4:
            if (self.castle & 4 and b[5] == 0 and b[6] == 0 and b[7] == -4
                and not self.attacked(4, 1) and not self.attacked(5, 1)
                and not self.attacked(6, 1)):
              out.append((4, 6, 0, 2))
            if (self.castle & 8 and b[3] == 0 and b[2] == 0 and b[1] == 0
                and b[0] == -4 and not self.attacked(4, 1)
                and not self.attacked(3, 1) and not self.attacked(2, 1)):
              out.append((4, 2, 0, 3))
      else:
        rl = []
        if a != 4:
          rl.append(CH_BISHOP_RAYS[f])
        if a != 3:
          rl.append(CH_ROOK_RAYS[f])
        for rays in rl:
          for ray in rays:
            for t in ray:
              q = b[t]
              if q == 0:
                if not caps:
                  out.append((f, t, 0, 0))
              else:
                if q * s < 0:
                  out.append((f, t, 0, 0))
                break
    return out

  def make(self, m):
    f, t, pr, fl = m
    b = self.board
    s = self.side
    piece = b[f]
    cap = b[t]
    capsq = t
    if fl == 1:                                  # captura al pas
      capsq = t + 8 if s == 1 else t - 8
      cap = b[capsq]
      b[capsq] = 0
    b[t] = pr * s if pr else piece
    b[f] = 0
    if fl == 2:                                  # enroc curt
      b[f + 1] = b[f + 3]
      b[f + 3] = 0
    elif fl == 3:                                # enroc llarg
      b[f - 1] = b[f - 4]
      b[f - 4] = 0
    rec = (m, piece, cap, capsq, self.castle, self.ep, self.half)
    self.castle &= CH_CMASK[f] & CH_CMASK[t]
    self.ep = (f + t) >> 1 if fl == 4 else -1
    self.half = 0 if (piece == 1 or piece == -1 or cap) else self.half + 1
    if piece == 6:
      self.kpos[0] = t
    elif piece == -6:
      self.kpos[1] = t
    self.side = -s
    return rec

  def unmake(self, rec):
    m, piece, cap, capsq, castle, ep, half = rec
    f, t, pr, fl = m
    b = self.board
    b[f] = piece
    if fl == 1:
      b[t] = 0
      b[capsq] = cap
    else:
      b[t] = cap
    if fl == 2:
      b[f + 3] = b[f + 1]
      b[f + 1] = 0
    elif fl == 3:
      b[f - 4] = b[f - 1]
      b[f - 1] = 0
    if piece == 6:
      self.kpos[0] = f
    elif piece == -6:
      self.kpos[1] = f
    self.castle, self.ep, self.half = castle, ep, half
    self.side = -self.side

  def legal_moves(self):
    s = self.side
    ki = 0 if s == 1 else 1
    res = []
    for m in self.gen():
      rec = self.make(m)
      if not self.attacked(self.kpos[ki], -s):
        res.append(m)
      self.unmake(rec)
    return res

  # ---------- estat de la partida ----------
  def key(self):
    return (tuple(self.board), self.side, self.castle, self.ep)

  def register_position(self):
    k = self.key()
    n = self.history.get(k, 0) + 1
    self.history[k] = n
    if n >= 3:
      self.draw = True
      self.draw_reason = "Repetició de posició"

  def insufficient(self):
    pcs = [(abs(p), sq) for sq, p in enumerate(self.board)
           if p and abs(p) != 6]
    if not pcs:
      return True
    if len(pcs) == 1 and pcs[0][0] in (2, 3):
      return True
    if all(k == 3 for k, _ in pcs):
      colors = {((sq >> 3) + (sq & 7)) & 1 for _, sq in pcs}
      return len(colors) == 1
    return False

  def update_status(self):
    if not self.legal_moves():
      if self.in_check():
        self.winner = "B" if self.side == 1 else "W"
        self.checkmate = True
        self.draw = False
      else:
        self.draw = True
        self.draw_reason = "Rei ofegat"
      return
    if self.draw:
      return
    if self.half >= 100:
      self.draw = True
      self.draw_reason = "Regla dels 50 moviments"
    elif self.insufficient():
      self.draw = True
      self.draw_reason = "Material insuficient"

  def snapshot(self):
    return dict(
        board=self.board[:], side=self.side, turn=self.turn,
        castle=self.castle, ep=self.ep, half=self.half, kpos=self.kpos[:],
        move_count=self.move_count, last_move=self.last_move,
        history=dict(self.history))

  def undo_one(self):
    if not self.stack:
      return False
    s = self.stack.pop()
    self.board = s["board"]
    self.side = s["side"]
    self.castle = s["castle"]
    self.ep = s["ep"]
    self.half = s["half"]
    self.kpos = s["kpos"]
    self.move_count = s["move_count"]
    self.last_move = s["last_move"]
    self.history = s["history"]
    self.winner = None
    self.checkmate = False
    self.draw = False
    self.draw_reason = ""
    self.selected = None
    self.sel_moves = []
    return True

  def play(self, m):
    snap = self.snapshot()
    self.make(m)
    self.stack.append(snap)
    self.last_move = (m[0], m[1])
    self.move_count += 1
    self.selected = None
    self.sel_moves = []
    self.register_position()
    self.update_status()

  def handle_click(self, sq, my_role):
    """Primer clic: tria la peça. Segon clic: la mou (si el moviment és legal)."""
    if self.winner or self.draw or self.turn != my_role:
      return False
    if self.selected is not None:
      for m in self.sel_moves:
        if m[1] == sq and m[2] in (0, 5):        # promoció automàtica a dama
          self.play(m)
          return True
    if sq == self.selected:
      self.selected = None
      self.sel_moves = []
    elif self.board[sq] * self.side > 0:
      self.selected = sq
      self.sel_moves = [m for m in self.legal_moves() if m[0] == sq]
    else:
      self.selected = None
      self.sel_moves = []
    return False


# ---------------------------------------------------------------
# ESCACS: BOT (negamax + alfa-beta + quiescence + aprofundiment iteratiu)
# ---------------------------------------------------------------


class ChessBot:

  def __init__(self, think=0.8, max_depth=4, blunder=0.0):
    self.think = think
    self.max_depth = max_depth
    self.blunder = blunder
    self.deadline = 0
    self.nodes = 0

  def evaluate(self, pos):
    sc = 0
    for sq, p in enumerate(pos.board):
      if p:
        if p > 0:
          sc += CH_VAL[p] + CH_PST_W[p][sq]
        else:
          sc -= CH_VAL[-p] + CH_PST_B[-p][sq]
    return sc if pos.side == 1 else -sc

  def order(self, pos, moves):
    b = pos.board

    def key(m):
      f, t, pr, fl = m
      v = b[t]
      sc = 0
      if v:
        sc = 10 * CH_VAL[abs(v)] - CH_VAL[abs(b[f])] // 10
      elif fl == 1:
        sc = 1000
      if pr:
        sc += CH_VAL[pr]
      return -sc

    return sorted(moves, key=key)

  def qs(self, pos, alpha, beta, ply):
    self.nodes += 1
    if self.nodes & 255 == 0 and time.time() > self.deadline:
      raise Timeout
    stand = self.evaluate(pos)
    if stand >= beta:
      return stand
    if stand > alpha:
      alpha = stand
    if ply >= 8:
      return stand
    s = pos.side
    ki = 0 if s == 1 else 1
    for m in self.order(pos, pos.gen(True)):
      rec = pos.make(m)
      if pos.attacked(pos.kpos[ki], -s):
        pos.unmake(rec)
        continue
      sc = -self.qs(pos, -beta, -alpha, ply + 1)
      pos.unmake(rec)
      if sc >= beta:
        return sc
      if sc > alpha:
        alpha = sc
    return alpha

  def nega(self, pos, depth, alpha, beta, ply):
    self.nodes += 1
    if self.nodes & 255 == 0 and time.time() > self.deadline:
      raise Timeout
    if pos.half >= 100:
      return 0
    s = pos.side
    ki = 0 if s == 1 else 1
    incheck = pos.attacked(pos.kpos[ki], -s)
    if incheck and ply < 12:
      depth += 1
    if depth <= 0:
      return self.qs(pos, alpha, beta, 0)
    best = -INF
    any_legal = False
    for m in self.order(pos, pos.gen()):
      rec = pos.make(m)
      if pos.attacked(pos.kpos[ki], -s):
        pos.unmake(rec)
        continue
      any_legal = True
      sc = -self.nega(pos, depth - 1, -beta, -alpha, ply + 1)
      pos.unmake(rec)
      if sc > best:
        best = sc
        if sc > alpha:
          alpha = sc
          if alpha >= beta:
            break
    if not any_legal:
      return -(CH_MATE - ply) if incheck else 0
    return best

  def choose(self, game, role=None):
    """Retorna el moviment (f, t, promoció, marca) o None si no n'hi ha."""
    pos = game.clone()
    moves = pos.legal_moves()
    if not moves:
      return None
    if len(moves) == 1:
      return moves[0]
    random.shuffle(moves)
    if self.blunder and random.random() < self.blunder:
      return random.choice(moves)
    moves = self.order(pos, moves)

    # Evitar taules per repetició quan no cal (com els altres bots)
    hist = getattr(game, "history", {})
    s = pos.side
    pen = {}
    for m in moves:
      rec = pos.make(m)
      c = hist.get((tuple(pos.board), pos.side, pos.castle, pos.ep), 0)
      pos.unmake(rec)
      pen[m] = None if c + 1 >= 3 else c * 20

    best = moves[0]
    self.deadline = time.time() + self.think
    self.nodes = 0
    for depth in range(1, self.max_depth + 1):
      try:
        cur, cur_sc, alpha = None, -INF, -INF
        for m in moves:
          if pen[m] is None:
            sc = 0
          else:
            rec = pos.make(m)
            sc = -self.nega(pos, depth - 1, -INF, -alpha, 1) - pen[m]
            pos.unmake(rec)
          if sc > cur_sc:
            cur_sc, cur = sc, m
            alpha = max(alpha, sc)
        best = cur
        moves.remove(cur)
        moves.insert(0, cur)
        if abs(cur_sc) >= CH_MATE - 100:
          break
      except Timeout:
        break
    return best

  def play(self, game, role=None):
    m = self.choose(game, role)
    if m is not None:
      game.play(m)


# ---------------------------------------------------------------
# GO 9x9: JOC (puntuació per àrees, komi 7,5, sense empats)
# ---------------------------------------------------------------

GO_N = 9
GO_NB = []
for _i in range(GO_N * GO_N):
  _r, _c = divmod(_i, GO_N)
  GO_NB.append([_r2 * GO_N + _c2 for _r2, _c2 in
                ((_r - 1, _c), (_r + 1, _c), (_r, _c - 1), (_r, _c + 1))
                if 0 <= _r2 < GO_N and 0 <= _c2 < GO_N])


def go_group(board, i):
  """Retorna (pedres del grup, llibertats) del grup que conté la pedra 'i'."""
  color = board[i]
  stack = [i]
  seen = {i}
  libs = set()
  while stack:
    x = stack.pop()
    for n in GO_NB[x]:
      v = board[n]
      if v == 0:
        libs.add(n)
      elif v == color and n not in seen:
        seen.add(n)
        stack.append(n)
  return seen, libs


def go_play(board, i, color):
  """Posa una pedra. Retorna (tauler nou, captures) o None si és suïcidi/ocupat."""
  if board[i]:
    return None
  b = board[:]
  b[i] = color
  opp = 3 - color
  cap = 0
  for n in GO_NB[i]:
    if b[n] == opp:
      grp, libs = go_group(b, n)
      if not libs:
        for x in grp:
          b[x] = 0
        cap += len(grp)
  grp, libs = go_group(b, i)
  if not libs:
    return None
  return b, cap


def go_area(board):
  """Punts per àrees: pedres + territori envoltat només per un color."""
  black = white = 0
  seen = set()
  for i, v in enumerate(board):
    if v == 1:
      black += 1
    elif v == 2:
      white += 1
    elif i not in seen:
      region = [i]
      seen.add(i)
      borders = set()
      k = 0
      while k < len(region):
        for n in GO_NB[region[k]]:
          nv = board[n]
          if nv == 0:
            if n not in seen:
              seen.add(n)
              region.append(n)
          else:
            borders.add(nv)
        k += 1
      if borders == {1}:
        black += len(region)
      elif borders == {2}:
        white += len(region)
  return black, white


class Go:
  KOMI = 7.5
  MAX_MOVES = 160            # si s'arriba aquí, la partida es puntua tal com està

  def __init__(self):
    self.board = [0] * (GO_N * GO_N)
    self.cur = 1               # 1 = negres (comencen), 2 = blanques
    self.passes = 0
    self.winner = None
    self.draw = False
    self.move_count = 0
    self.last_move = None      # índex de la casella (None = ha passat)
    self.caps = {1: 0, 2: 0}   # pedres capturades per cada color
    self.history = {tuple(self.board)}
    self.stack = []
    self.score_text = ""

  @property
  def turn(self):
    return "B" if self.cur == 1 else "W"

  def is_legal(self, i, color=None):
    res = go_play(self.board, i, color or self.cur)
    return res is not None and tuple(res[0]) not in self.history

  def snapshot(self):
    return dict(
        board=self.board[:], cur=self.cur, turn=self.turn,
        passes=self.passes, caps=dict(self.caps),
        history=set(self.history), move_count=self.move_count,
        last_move=self.last_move)

  def undo_one(self):
    if not self.stack:
      return False
    s = self.stack.pop()
    self.board = s["board"]
    self.cur = s["cur"]
    self.passes = s["passes"]
    self.caps = s["caps"]
    self.history = s["history"]
    self.move_count = s["move_count"]
    self.last_move = s["last_move"]
    self.winner = None
    self.score_text = ""
    return True

  def handle_click(self, i, role):
    if self.winner or self.turn != role:
      return False
    res = go_play(self.board, i, self.cur)
    if res is None or tuple(res[0]) in self.history:
      return False
    snap = self.snapshot()
    nb, cap = res
    self.board = nb
    self.caps[self.cur] += cap
    self.history.add(tuple(nb))
    self.passes = 0
    self.cur = 3 - self.cur
    self.move_count += 1
    self.last_move = i
    self.stack.append(snap)
    self.check_end()
    return True

  def pass_move(self, role):
    if self.winner or self.turn != role:
      return False
    snap = self.snapshot()
    self.passes += 1
    self.cur = 3 - self.cur
    self.move_count += 1
    self.last_move = None
    self.stack.append(snap)
    self.check_end()
    return True

  def check_end(self):
    if self.passes >= 2 or self.move_count >= self.MAX_MOVES:
      black, white = go_area(self.board)
      self.winner = "B" if black > white + self.KOMI else "W"
      self.score_text = (
          f"Negres {black}  -  Blanques {white} + {self.KOMI} de komi")


# ---------------------------------------------------------------
# GO: BOT (heurística tàctica + simulacions a l'atzar als nivells alts)
# ---------------------------------------------------------------


class GoBot:
  """Bot senzill de Go: captura, salva les seves pedres i evita els ulls propis.

  Als nivells alts prova les millors jugades amb partides a l'atzar.
  """

  def __init__(self, think=0.5, blunder=0.0, playouts=False, top=6):
    self.think = think
    self.blunder = blunder
    self.playouts = playouts
    self.top = top

  def heuristic(self, game, board, nb, cap, i, color):
    opp = 3 - color
    r, c = divmod(i, GO_N)
    s = 0.0
    nbs = GO_NB[i]
    if cap == 0 and all(board[n] == color for n in nbs):
      s -= 100                                   # omplir un ull propi
    grp, libs = go_group(nb, i)
    if cap == 0 and len(libs) == 1:
      s -= 12 + 8 * len(grp)                     # s'auto-posa en atari
    elif len(libs) == 2:
      s -= 2
    s += 12 * cap
    seen_opp = set()
    seen_own = set()
    for n in nbs:
      if nb[n] == opp and n not in seen_opp:
        g1, l1 = go_group(nb, n)
        seen_opp |= g1
        if len(l1) == 1:
          s += 6 + 2 * len(g1)                   # posa l'adversari en atari
        elif len(l1) == 2:
          s += 1
      elif board[n] == color and n not in seen_own:
        g0, l0 = go_group(board, n)
        seen_own |= g0
        if len(l0) == 1:                         # estava en atari: la salva?
          g2, l2 = go_group(nb, n)
          if len(l2) >= 2:
            s += 10 + 3 * len(g0)
    d = min(r, c, GO_N - 1 - r, GO_N - 1 - c)
    s += (-5, 0, 3, 4, 4)[d]
    lm = game.last_move
    if isinstance(lm, int):
      lr, lc = divmod(lm, GO_N)
      if abs(lr - r) + abs(lc - c) <= 2:
        s += 2
    return s + random.random() * 1.5

  def playout(self, board, to_move, me):
    """Partida a l'atzar fins al final. True si 'me' guanya."""
    b = board
    color = to_move
    passes = 0
    for _ in range(80):
      empt = [i for i in range(GO_N * GO_N) if b[i] == 0]
      random.shuffle(empt)
      moved = False
      for i in empt[:10]:
        if all(b[n] == color for n in GO_NB[i]):
          continue
        res = go_play(b, i, color)
        if res is not None:
          b = res[0]
          moved = True
          break
      if moved:
        passes = 0
      else:
        passes += 1
        if passes >= 2:
          break
      color = 3 - color
    black, white = go_area(b)
    return (black > white + Go.KOMI) == (me == 1)

  def choose(self, game, role):
    """Retorna l'índex de la casella, o None si el millor és passar."""
    color = 1 if role == "B" else 2
    board = game.board
    cands = []
    for i in range(GO_N * GO_N):
      if board[i]:
        continue
      res = go_play(board, i, color)
      if res is not None and tuple(res[0]) not in game.history:
        cands.append((i, res))
    if not cands:
      return None
    if game.passes >= 1:                         # l'altre ha passat: passa si guanyes
      black, white = go_area(board)
      mine, theirs = ((black, white + Go.KOMI) if color == 1
                      else (white + Go.KOMI, black))
      if mine > theirs:
        return None
    scored = sorted(
        ((self.heuristic(game, board, nb, cap, i, color), i, nb)
         for i, (nb, cap) in cands), reverse=True)
    if scored[0][0] < -40:
      return None                                # només queden jugades dolentes
    ok = [x for x in scored if x[0] > -40]
    if self.blunder and random.random() < self.blunder:
      return random.choice(ok)[1]
    if not self.playouts or len(ok) == 1:
      return ok[0][1]
    top = ok[:self.top]
    wins = [0] * len(top)
    tries = [0] * len(top)
    deadline = time.time() + self.think
    n = 0
    while time.time() < deadline:
      k = n % len(top)
      n += 1
      if self.playout(top[k][2], 3 - color, color):
        wins[k] += 1
      tries[k] += 1
    best = max(range(len(top)), key=lambda k: (
        top[k][0] * 0.6 + 30 * (wins[k] / tries[k] if tries[k] else 0.5)))
    return top[best][1]

  def play(self, game, role):
    i = self.choose(game, role)
    if i is None:
      game.pass_move(role)
    else:
      game.handle_click(i, role)


def make_bot(kind, params):
  return {"morris": Bot, "c4": C4Bot, "chess": ChessBot, "go": GoBot}[kind](**params)


# ---------------------------------------------------------------
# ANIMACIONS
# ---------------------------------------------------------------


class MoveAnim:
  """Fitxa de Tres en ratlla: llisca (src -> dst) o creix (col·locació)."""

  def __init__(self, owner, src_pos, dst_point, dur):
    self.owner = owner
    self.src = src_pos
    self.dst_point = dst_point
    self.dst = POINT_POSITIONS[dst_point]
    self.dur = dur
    self.start = time.time()

  def t(self):
    return min(1.0, (time.time() - self.start) / self.dur)

  def active(self):
    return time.time() - self.start < self.dur


class C4Anim:
  """Fitxa de 4 en ratlla caient."""

  def __init__(self, col, row, owner, dur):
    self.col = col
    self.row = row
    self.owner = owner
    self.dur = dur
    self.start = time.time()

  def t(self):
    return min(1.0, (time.time() - self.start) / self.dur)

  def active(self):
    return time.time() - self.start < self.dur


# ---------------------------------------------------------------
# MENÚS
# ---------------------------------------------------------------

NUM_KEYS = [
    (pygame.K_1, pygame.K_KP1),
    (pygame.K_2, pygame.K_KP2),
    (pygame.K_3, pygame.K_KP3),
    (pygame.K_4, pygame.K_KP4),
    (pygame.K_5, pygame.K_KP5),
    (pygame.K_6, pygame.K_KP6),
]
C4_KEYS = [
    (pygame.K_1, pygame.K_KP1), (pygame.K_2, pygame.K_KP2),
    (pygame.K_3, pygame.K_KP3), (pygame.K_4, pygame.K_KP4),
    (pygame.K_5, pygame.K_KP5), (pygame.K_6, pygame.K_KP6),
    (pygame.K_7, pygame.K_KP7),
]


def get_buttons(n):
  w = 460
  x = WIDTH // 2 - w // 2
  if n >= 5:                       # menú llarg: botons més compactes
    return [pygame.Rect(x, 215 + i * 72, w, 62) for i in range(n)]
  h = 80
  step = 110 if n <= 3 else 100
  return [pygame.Rect(x, 235 + i * step, w, h) for i in range(n)]


# ---------- cadenes i cadenat (nivell bloquejat) ----------

_LINK_CACHE = {}


def chain_link(kind, angle):
  """Una baula de cadena girada 'angle' graus (alternant planes i de cantó)."""
  key = (kind, round(angle))
  if key not in _LINK_CACHE:
    if kind == 0:
      s = pygame.Surface((32, 18), pygame.SRCALPHA)
      pygame.draw.ellipse(s, CHAIN_DARK, (0, 0, 32, 18), 5)
      pygame.draw.ellipse(s, CHAIN_LIGHT, (2, 2, 28, 14), 2)
    else:
      s = pygame.Surface((18, 18), pygame.SRCALPHA)
      pygame.draw.rect(s, CHAIN_DARK, (0, 5, 18, 8), border_radius=4)
      pygame.draw.rect(s, CHAIN_LIGHT, (2, 7, 14, 3), border_radius=2)
    _LINK_CACHE[key] = pygame.transform.rotate(s, -angle)
  return _LINK_CACHE[key]


def draw_chain(p1, p2):
  dx, dy = p2[0] - p1[0], p2[1] - p1[1]
  dist = math.hypot(dx, dy)
  if dist == 0:
    return
  angle = math.degrees(math.atan2(dy, dx))
  step = 22
  for i in range(int(dist // step) + 1):
    t = i * step / dist
    s = chain_link(i % 2, angle)
    SCREEN.blit(s, (p1[0] + dx * t - s.get_width() // 2,
                    p1[1] + dy * t - s.get_height() // 2))


def draw_padlock(cx, cy):
  # arc (nansa)
  pygame.draw.arc(SCREEN, CHAIN_DARK, (cx - 11, cy - 24, 22, 28), 0, math.pi, 5)
  pygame.draw.arc(SCREEN, CHAIN_LIGHT, (cx - 11, cy - 24, 22, 28), 0, math.pi, 2)
  # cos
  body = pygame.Rect(cx - 16, cy - 6, 32, 26)
  pygame.draw.rect(SCREEN, LOCK_GOLD, body, border_radius=5)
  pygame.draw.rect(SCREEN, (120, 85, 10), body, 3, border_radius=5)
  # forat de la clau
  pygame.draw.circle(SCREEN, (60, 40, 5), (cx, cy + 5), 4)
  pygame.draw.rect(SCREEN, (60, 40, 5), (cx - 2, cy + 6, 4, 8))


def draw_locked_overlay(rect):
  """Cadenes creuades i cadenat sobre un botó bloquejat."""
  prev_clip = SCREEN.get_clip()
  SCREEN.set_clip(rect)
  draw_chain((rect.x - 8, rect.y - 4), (rect.right + 8, rect.bottom + 4))
  draw_chain((rect.x - 8, rect.bottom + 4), (rect.right + 8, rect.y - 4))
  SCREEN.set_clip(prev_clip)
  draw_padlock(rect.x + 40, rect.centery - 2)


def draw_choice_menu(title, subtitle, opts, mouse_pos, hint):
  """opts: llista de (clau, text, descripció, activat[, bloquejat])."""
  SCREEN.fill(BG_COLOR)

  t = BIG_FONT.render(title, True, TEXT_COLOR)
  SCREEN.blit(t, (WIDTH // 2 - t.get_width() // 2, 110))

  sub = FONT.render(subtitle, True, SOFT_TEXT)
  SCREEN.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 180))

  for i, (rect, o) in enumerate(zip(get_buttons(len(opts)), opts)):
    key, label, desc, enabled = o[:4]
    locked = len(o) > 4 and o[4]
    hover = enabled and rect.collidepoint(mouse_pos)
    fill = (
        (255, 240, 205) if hover else (250, 232, 195)
    ) if enabled else (215, 200, 175)

    pygame.draw.rect(SCREEN, fill, rect, border_radius=14)
    pygame.draw.rect(
        SCREEN, HIGHLIGHT_COLOR if hover else LINE_COLOR, rect,
        5 if hover else 3, border_radius=14)

    color = TEXT_COLOR if enabled else (140, 130, 115)
    compact = rect.height < 80
    t1 = TITLE_FONT.render(f"{i + 1} - {label}", True, color)
    SCREEN.blit(t1, (rect.centerx - t1.get_width() // 2,
                     rect.y + (3 if compact else 10)))
    t2 = FONT.render(desc, True, color)
    SCREEN.blit(t2, (rect.centerx - t2.get_width() // 2,
                     rect.y + (rect.height - 27 if compact else 48)))

    if locked:
      draw_locked_overlay(rect)

  h = FONT.render(hint, True, SOFT_TEXT)
  SCREEN.blit(h, (WIDTH // 2 - h.get_width() // 2, HEIGHT - 60))


def menu_pick(opts, events):
  """Retorna la clau escollida, 'back' (ESC / M) o None."""
  rects = get_buttons(len(opts))
  for ev in events:
    if ev.type == pygame.KEYDOWN:
      if ev.key in (pygame.K_ESCAPE, pygame.K_m):
        return "back"
      for i, ks in enumerate(NUM_KEYS[:len(opts)]):
        if ev.key in ks and opts[i][3]:
          return opts[i][0]
    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
      for r, o in zip(rects, opts):
        if r.collidepoint(ev.pos) and o[3]:
          return o[0]
  return None


# ---------------------------------------------------------------
# TEXTOS COMUNS
# ---------------------------------------------------------------

FIRST = {"morris": "W", "c4": 1, "chess": "W", "go": "B"}
SECOND = {"morris": "B", "c4": 2, "chess": "B", "go": "W"}
SIDE_NAMES = {
    "morris": ("LES BLANQUES", "LES NEGRES"),
    "c4": ("ELS VERMELLS", "ELS GROCS"),
    "chess": ("LES BLANQUES", "LES NEGRES"),
    "go": ("LES NEGRES", "LES BLANQUES"),
}
SIDE_DESC = {
    "morris": ("les blanques", "les negres"),
    "c4": ("els vermells", "els grocs"),
    "chess": ("les blanques", "les negres"),
    "go": ("les negres", "les blanques"),
}
LOCAL_NAMES = {
    "morris": ("Blanques", "Negres"),
    "c4": ("Vermells", "Grocs"),
    "chess": ("Blanques", "Negres"),
    "go": ("Negres", "Blanques"),
}
GAME_TITLES = {"morris": "Tres en ratlla", "c4": "4 en ratlla",
               "chess": "Escacs", "go": "Go 9x9"}


def draw_text_for(g, kind):
  """Motiu de les taules."""
  if kind == "chess":
    return g.draw_reason or "Taules"
  if kind == "morris":
    return "Posició repetida o massa moviments"
  return "Tauler ple"


def side_label(kind, p):
  return SIDE_NAMES[kind][0 if p == FIRST[kind] else 1]


def record_text(app):
  if app.mode == "bot":
    w, l, d = SAVE["records"][app.kind][app.difficulty]
    return f"{LEVEL_INFO[app.difficulty][0].capitalize()}: {w}V  {l}D  {d}T"
  if app.mode == "local":
    a, b, c = SAVE["records"][app.kind]["local"]
    n1, n2 = LOCAL_NAMES[app.kind]
    return f"{n1} {a}  {n2} {b}  Taules {c}"
  return ""


def hint_cost(app):
  """Punts que costa una pista: depèn del nivell del bot (o local)."""
  return HINT_COST[app.difficulty if app.mode == "bot" else "local"]


def undo_cost(app):
  """Punts que costa desfer una jugada (menys que una pista)."""
  return UNDO_COST[app.difficulty if app.mode == "bot" else "local"]


def draw_hud(app):
  pts = SMALL.render(f"Punts: {SAVE['points']}", True, SOFT_TEXT)
  SCREEN.blit(pts, (20, 20))
  rec = record_text(app)
  if rec:
    r = SMALL.render(rec, True, SOFT_TEXT)
    SCREEN.blit(r, (WIDTH - 20 - r.get_width(), 20))


def status_text(app):
  g = app.game
  kind = app.kind
  if g.winner:
    if app.mode == "bot":
      base = "Has guanyat!!" if g.winner == app.me else "Ha guanyat l'ordinador"
    elif app.mode == "online":
      base = "Has guanyat!!" if g.winner == app.me else "Ha guanyat el rival"
    else:
      base = f"¡¡GUANYEN {side_label(kind, g.winner)}!!"
    if kind == "morris" and g.blocked:
      base += " (rival bloquejat)"
    elif kind == "chess":
      base += " (escac i mat)"
    return base
  if g.draw:
    return "TAULES"
  if app.mode == "bot" and g.turn == app.bot_role:
    return "L'ordinador està pensant..."
  who = side_label(kind, g.turn)
  if kind == "c4":
    return f"Torn: {who}"
  if kind == "chess":
    return f"Torn: {who}" + (" - ESCAC!" if g.in_check() else "")
  if kind == "go":
    return f"Torn: {who}" + (" (el rival ha passat)" if g.passes else "")
  left = g.unplaced.get(g.turn, 0)
  if left > 0:
    return f"Col·locació - Torn: {who} (Restants: {left})"
  if g.rules.fly:
    return f"Moviment lliure - Torn: {who} (a qualsevol lloc buit)"
  return f"Moviment - Torn: {who} (a un espai adjacent)"


def draw_button(rect, label, enabled=True, mouse=None, small=False):
  mouse = mouse or pygame.mouse.get_pos()
  hover = enabled and rect.collidepoint(mouse)
  if enabled:
    fill = (255, 240, 205) if hover else (245, 226, 185)
    border = HIGHLIGHT_COLOR if hover else LINE_COLOR
    color = TEXT_COLOR
  else:
    fill, border, color = (222, 208, 182), (170, 155, 130), (160, 148, 128)
  pygame.draw.rect(SCREEN, fill, rect, border_radius=10)
  pygame.draw.rect(SCREEN, border, rect, 3, border_radius=10)
  t = (SMALL if small else FONT).render(label, True, color)
  SCREEN.blit(t, (rect.centerx - t.get_width() // 2,
                  rect.centery - t.get_height() // 2))


def game_buttons(app):
  """Botons de la partida (per jugar des del mòbil): (rect, clau, activat)."""
  y, h = HEIGHT - 48, 40
  if app.mode == "online":
    items = [("restart", "Reiniciar", True), ("menu", "Menú", True)]
  else:
    items = [
        ("restart", "Reiniciar", True),
        ("menu", "Menú", True),
        ("undo", "Desfer", app.can_undo()),
        ("hint", "Pista", app.can_hint()),
    ]
    if app.kind == "go":
      items.append(("pass", "Passar", app.can_pass()))
  gap = 10
  w = (WIDTH - 2 * 30 - gap * (len(items) - 1)) // len(items)
  return [(pygame.Rect(30 + i * (w + gap), y, w, h), key, en)
          for i, (key, _label, en) in enumerate(items)], [i[1] for i in items]


def draw_footer(app):
  info = FONT.render(status_text(app), True, TEXT_COLOR)
  SCREEN.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT - 82))
  rects, labels = game_buttons(app)
  online = app.mode == "online"
  names = {"restart": "Reiniciar", "menu": "Menú",
           "undo": ("Desfer" if online else
                    f"Desfer (x{SAVE['items']['undos']})" if SAVE["items"]["undos"] > 0
                    else f"Desfer (-{undo_cost(app)})"),
           "hint": ("Pista" if online else
                    f"Pista (x{SAVE['items']['hints']})" if SAVE["items"]["hints"] > 0
                    else f"Pista (-{hint_cost(app)})"),
           "pass": "Passar"}
  for (rect, key, en) in rects:
    draw_button(rect, names[key], en, small=len(rects) > 4)


def back_button_rect():
  return pygame.Rect(15, 15, 120, 42)


# ---------------------------------------------------------------
# DIBUIX: TRES EN RATLLA
# ---------------------------------------------------------------


def current_style():
  return PIECE_STYLES[SAVE["equipped"]["pieces"]]


def draw_disc(pos, fill, border, deco, r):
  """Fitxa rodona amb l'estil escollit (llisa, amb anell o amb gemma)."""
  pos = (int(pos[0]), int(pos[1]))
  pygame.draw.circle(SCREEN, fill, pos, r)
  pygame.draw.circle(SCREEN, border, pos, r, 2)
  if deco == 1:
    pygame.draw.circle(SCREEN, border, pos, max(2, int(r * 0.62)), 2)
  elif deco == 2:
    pygame.draw.circle(SCREEN, _lighter(fill), pos, max(2, int(r * 0.38)))


def draw_piece(owner, pos, r=18):
  st = current_style()
  if owner == "W":
    fill, border = st["w"]
  elif owner == "B":
    fill, border = st["b"]
  else:
    return
  draw_disc(pos, fill, border, st["deco"], r)


def draw_turn_indicator(color_fill, color_border):
  x, y, radius = WIDTH - 45, 70, 16
  label = FONT.render("Torn:", True, TEXT_COLOR)
  SCREEN.blit(label, (x - radius - label.get_width() - 8, y - 10))
  pygame.draw.circle(SCREEN, color_fill, (x, y), radius)
  pygame.draw.circle(SCREEN, color_border, (x, y), radius, 2)


def draw_morris(app):
  g = app.game
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("Tres en ratlla", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
  draw_hud(app)

  if app.mode == "local":
    role = "Mode local"
  elif app.mode == "bot":
    me = "BLANQUES" if app.me == "W" else "NEGRES"
    role = f"Tu: {me}  -  Bot {LEVEL_INFO[app.difficulty][0].capitalize()}"
  else:
    role = f"Ets les: {'BLANQUES' if app.me == 'W' else 'NEGRES'}"
  SCREEN.blit(FONT.render(role, True, (0, 100, 200)), (20, 60))

  st = current_style()
  draw_turn_indicator(*(st["w"] if g.turn == "W" else st["b"]))

  counts = FONT.render(
      f"Per col·locar:  Blanques {g.unplaced['W']}   Negres {g.unplaced['B']}",
      True, SOFT_TEXT)
  SCREEN.blit(counts, (WIDTH // 2 - counts.get_width() // 2, 92))

  for layer in range(3):
    margin = 50 + layer * 70
    size = BOARD_SIZE - 2 * margin
    pygame.draw.rect(
        SCREEN, LINE_COLOR,
        (OFFSET_X + margin, OFFSET_Y + margin, size, size), 4)

  mid_lines = [
      ((0, 1, 0), (2, 1, 0)), ((0, 1, 2), (2, 1, 2)),
      ((0, 0, 1), (2, 0, 1)), ((0, 2, 1), (2, 2, 1)),
  ]
  if g.rules.diag:
    mid_lines += [((0, r, c), (2, r, c)) for r, c in CORNERS]
  for p1, p2 in mid_lines:
    pygame.draw.line(
        SCREEN, LINE_COLOR, POINT_POSITIONS[p1], POINT_POSITIONS[p2], 4)

  if g.winning_line and len(g.winning_line) == 3:
    p1 = POINT_POSITIONS.get(g.winning_line[0])
    p3 = POINT_POSITIONS.get(g.winning_line[2])
    if p1 and p3:
      pygame.draw.line(SCREEN, WIN_LINE_COLOR, p1, p3, 10)

  # últim moviment (sota les fitxes)
  if g.last_move:
    src, dst = g.last_move
    if src:
      pygame.draw.line(
          SCREEN, LAST_COLOR, POINT_POSITIONS[src], POINT_POSITIONS[dst], 3)
      pygame.draw.circle(SCREEN, LAST_COLOR, POINT_POSITIONS[src], 12, 3)

  # punts on es pot moure la fitxa seleccionada
  hints = []
  if g.selected_point is not None and not g.winner and not g.draw:
    hints = [p for p in POINTS_CONFIG
             if can_move_to(g.selected_point, p, g.board, g.rules)]

  anim = app.anim if (app.anim and app.anim.active()) else None

  for point, pos in POINT_POSITIONS.items():
    owner = g.board.get(point)
    pygame.draw.circle(SCREEN, LINE_COLOR, pos, 6)

    if point in hints:
      pygame.draw.circle(SCREEN, HINT_COLOR, pos, 11)
      pygame.draw.circle(SCREEN, WHITE_PIECE, pos, 11, 2)

    if point == g.selected_point:
      pygame.draw.circle(SCREEN, HIGHLIGHT_COLOR, pos, 22, 4)

    if anim and point == anim.dst_point:
      continue                      # aquesta fitxa s'està animant
    draw_piece(owner, pos)

  if anim:
    t = anim.t()
    if anim.src is None:
      e = 1 - (1 - t) ** 2
      draw_piece(anim.owner, anim.dst, max(3, int(18 * e)))
    else:
      e = 1 - (1 - t) ** 3
      x = anim.src[0] + (anim.dst[0] - anim.src[0]) * e
      y = anim.src[1] + (anim.dst[1] - anim.src[1]) * e
      draw_piece(anim.owner, (x, y))

  if g.last_move and not anim:
    pygame.draw.circle(SCREEN, LAST_COLOR, POINT_POSITIONS[g.last_move[1]], 24, 3)

  # pista
  if app.hint and not g.winner and not g.draw:
    s, d = app.hint
    if s is not None:
      pygame.draw.circle(SCREEN, TIP_COLOR, POINT_POSITIONS[POINTS_CONFIG[s]], 25, 4)
      pygame.draw.line(
          SCREEN, TIP_COLOR, POINT_POSITIONS[POINTS_CONFIG[s]],
          POINT_POSITIONS[POINTS_CONFIG[d]], 3)
    pygame.draw.circle(SCREEN, TIP_COLOR, POINT_POSITIONS[POINTS_CONFIG[d]], 25, 4)

  draw_footer(app)


# ---------------------------------------------------------------
# DIBUIX: 4 EN RATLLA
# ---------------------------------------------------------------

C4_CELL = 80
C4_X0 = 70
C4_Y0 = 150
_C4_SURF = []


def apply_theme():
  """Aplica el tauler escollit a la botiga (colors de fons, línies i 4 en ratlla)."""
  global BG_COLOR, LINE_COLOR, BOARD_BLUE, BOARD_DARK, LAST_COLOR
  t = BOARD_THEMES[SAVE["equipped"]["boards"]]
  LAST_COLOR = MARK_STYLES[SAVE["equipped"]["marks"]]["color"]
  BG_COLOR, LINE_COLOR = t["bg"], t["line"]
  BOARD_BLUE, BOARD_DARK = t["c4"], t["c4dark"]
  _C4_SURF.clear()                 # el tauler del 4 en ratlla es torna a dibuixar


def c4_board_surface():
  if not _C4_SURF:
    w, h = C4_COLS * C4_CELL, C4_ROWS * C4_CELL
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, BOARD_BLUE, (0, 0, w, h), border_radius=18)
    for c in range(C4_COLS):
      for r in range(C4_ROWS):
        center = (c * C4_CELL + 40, r * C4_CELL + 40)
        pygame.draw.circle(s, BOARD_DARK, center, 35)
        pygame.draw.circle(s, (0, 0, 0, 0), center, 32)
    _C4_SURF.append(s)
  return _C4_SURF[0]


def c4_cell_center(c, r):
  return (C4_X0 + c * C4_CELL + 40, C4_Y0 + (C4_ROWS - 1 - r) * C4_CELL + 40)


def c4_col_at(x):
  c = (x - C4_X0) // C4_CELL
  return c if 0 <= c < C4_COLS else None


def draw_c4_piece(owner, pos, r=32):
  st = current_style()
  fill, border = st["c%d" % owner]
  pos = (int(pos[0]), int(pos[1]))
  pygame.draw.circle(SCREEN, fill, pos, r)
  pygame.draw.circle(SCREEN, border, pos, r, 3)
  pygame.draw.circle(SCREEN, border, pos, r - 10, 2)
  if st["deco"] == 2:
    pygame.draw.circle(SCREEN, _lighter(fill), pos, max(2, r // 4))


def draw_c4(app):
  g = app.game
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("4 en ratlla", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
  draw_hud(app)

  if app.mode == "local":
    role = "Mode local"
  else:
    me = "VERMELLS" if app.me == 1 else "GROCS"
    role = f"Tu: {me}  -  Bot {LEVEL_INFO[app.difficulty][0].capitalize()}"
  SCREEN.blit(FONT.render(role, True, (0, 100, 200)), (20, 60))
  draw_turn_indicator(*current_style()["c%d" % g.turn])

  anim = app.anim if (app.anim and app.anim.active()) else None

  # fitxes (a sota del tauler, es veuen pels forats)
  for c in range(C4_COLS):
    for r in range(C4_ROWS):
      v = g.grid[c][r]
      if v and not (anim and anim.col == c and anim.row == r):
        draw_c4_piece(v, c4_cell_center(c, r))
  if anim:
    x, y1 = c4_cell_center(anim.col, anim.row)
    y0 = C4_Y0 - 50
    t = anim.t()
    draw_c4_piece(anim.owner, (x, y0 + (y1 - y0) * t * t))

  SCREEN.blit(c4_board_surface(), (C4_X0, C4_Y0))

  # últim moviment
  if g.last_move and not anim:
    pygame.draw.circle(SCREEN, (255, 255, 255), c4_cell_center(*g.last_move), 22, 3)

  # línia guanyadora
  if g.win_cells:
    for c, r in g.win_cells:
      pygame.draw.circle(SCREEN, (255, 255, 255), c4_cell_center(c, r), 36, 5)

  # pista
  if app.hint is not None and not g.winner and not g.draw:
    c = app.hint
    if g.legal(c):
      r = g.grid[c].index(0)
      pygame.draw.circle(SCREEN, TIP_COLOR, c4_cell_center(c, r), 36, 5)
      x = C4_X0 + c * C4_CELL + 40
      pygame.draw.polygon(
          SCREEN, TIP_COLOR, [(x - 12, C4_Y0 - 22), (x + 12, C4_Y0 - 22), (x, C4_Y0 - 6)])

  # fitxa de previsualització sobre la columna del ratolí
  can_play = (
      not g.winner and not g.draw and not app.result and anim is None
      and (app.mode == "local" or g.turn == app.me)
  )
  if can_play:
    col = c4_col_at(pygame.mouse.get_pos()[0])
    if col is not None and g.legal(col):
      draw_c4_piece(g.turn, (C4_X0 + col * C4_CELL + 40, 112), 28)

  for c in range(C4_COLS):
    n = SMALL.render(str(c + 1), True, SOFT_TEXT)
    SCREEN.blit(n, (C4_X0 + c * C4_CELL + 40 - n.get_width() // 2,
                    C4_Y0 + C4_ROWS * C4_CELL + 10))

  draw_footer(app)


# ---------------------------------------------------------------
# DIBUIX: ESCACS
# ---------------------------------------------------------------

CH_SQ = 64
CH_X0 = 94
CH_Y0 = 100


def _mix(a, b, t):
  return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def chess_pos(sq, flip):
  """Cantonada superior esquerra de la casella (el tauler es gira si portes negres)."""
  r, c = sq >> 3, sq & 7
  if flip:
    r, c = 7 - r, 7 - c
  return CH_X0 + c * CH_SQ, CH_Y0 + r * CH_SQ


def chess_sq_at(pos, flip):
  c = (pos[0] - CH_X0) // CH_SQ
  r = (pos[1] - CH_Y0) // CH_SQ
  if not (0 <= c < 8 and 0 <= r < 8):
    return None
  if flip:
    r, c = 7 - r, 7 - c
  return r * 8 + c


def draw_chess(app):
  g = app.game
  flip = app.chess_flip()
  st = current_style()
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("Escacs", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
  draw_hud(app)

  if app.mode == "local":
    role = "Mode local"
  else:
    me = "BLANQUES" if app.me == "W" else "NEGRES"
    role = f"Tu: {me}  -  Bot {LEVEL_INFO[app.difficulty][0].capitalize()}"
  SCREEN.blit(FONT.render(role, True, (0, 100, 200)), (20, 60))
  draw_turn_indicator(*(st["w"] if g.turn == "W" else st["b"]))

  light = _mix(BG_COLOR, (255, 255, 255), 0.45)
  dark = _mix(BG_COLOR, LINE_COLOR, 0.5)
  for sq in range(64):
    x, y = chess_pos(sq, flip)
    pygame.draw.rect(
        SCREEN, light if ((sq >> 3) + (sq & 7)) % 2 == 0 else dark,
        (x, y, CH_SQ, CH_SQ))
  pygame.draw.rect(
      SCREEN, LINE_COLOR, (CH_X0 - 3, CH_Y0 - 3, 8 * CH_SQ + 6, 8 * CH_SQ + 6), 3)

  files = "abcdefgh"
  for i in range(8):
    f = SMALL.render(files[7 - i if flip else i], True, SOFT_TEXT)
    SCREEN.blit(f, (CH_X0 + i * CH_SQ + CH_SQ // 2 - f.get_width() // 2,
                    CH_Y0 + 8 * CH_SQ + 6))
    n = SMALL.render(str(i + 1 if flip else 8 - i), True, SOFT_TEXT)
    SCREEN.blit(n, (CH_X0 - 20, CH_Y0 + i * CH_SQ + CH_SQ // 2 - n.get_height() // 2))

  # últim moviment i rei en escac
  if g.last_move:
    for sq in g.last_move:
      x, y = chess_pos(sq, flip)
      pygame.draw.rect(SCREEN, LAST_COLOR, (x + 2, y + 2, CH_SQ - 4, CH_SQ - 4), 4)
  if not g.draw and g.in_check():
    x, y = chess_pos(g.kpos[0 if g.side == 1 else 1], flip)
    pygame.draw.rect(SCREEN, COLOR_LOSE, (x + 1, y + 1, CH_SQ - 2, CH_SQ - 2), 5)

  # casella triada i destins possibles (punts a sota de les peces)
  if g.selected is not None:
    x, y = chess_pos(g.selected, flip)
    pygame.draw.rect(SCREEN, HIGHLIGHT_COLOR, (x, y, CH_SQ, CH_SQ), 5)
  targets = {m[1] for m in g.sel_moves}
  for t in targets:
    if g.board[t] == 0 and not (g.ep == t and abs(g.board[g.selected]) == 1):
      x, y = chess_pos(t, flip)
      pygame.draw.circle(
          SCREEN, HINT_COLOR, (x + CH_SQ // 2, y + CH_SQ // 2), 9)

  for sq, p in enumerate(g.board):
    if not p:
      continue
    x, y = chess_pos(sq, flip)
    cx, cy = x + CH_SQ // 2, y + CH_SQ // 2
    fill, border = st["w"] if p > 0 else st["b"]
    draw_disc((cx, cy), fill, border, st["deco"], 26)
    lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
    letter = TITLE_FONT.render(
        CH_LETTERS[abs(p)], True, (40, 40, 40) if lum > 150 else (245, 245, 245))
    SCREEN.blit(letter, (cx - letter.get_width() // 2, cy - letter.get_height() // 2))

  for t in targets:                      # captures: anell a sobre de la peça
    if g.board[t] != 0 or (g.ep == t and abs(g.board[g.selected]) == 1):
      x, y = chess_pos(t, flip)
      pygame.draw.circle(
          SCREEN, HINT_COLOR, (x + CH_SQ // 2, y + CH_SQ // 2), 30, 4)

  # pista
  if app.hint is not None and not g.winner and not g.draw:
    for sq in app.hint[:2]:
      x, y = chess_pos(sq, flip)
      pygame.draw.rect(SCREEN, TIP_COLOR, (x + 1, y + 1, CH_SQ - 2, CH_SQ - 2), 5)
    x1, y1 = chess_pos(app.hint[0], flip)
    x2, y2 = chess_pos(app.hint[1], flip)
    pygame.draw.line(
        SCREEN, TIP_COLOR, (x1 + CH_SQ // 2, y1 + CH_SQ // 2),
        (x2 + CH_SQ // 2, y2 + CH_SQ // 2), 3)

  draw_footer(app)


# ---------------------------------------------------------------
# DIBUIX: GO
# ---------------------------------------------------------------

GO_CELL = 56
GO_X0 = (WIDTH - GO_CELL * (GO_N - 1)) // 2
GO_Y0 = 160


def go_xy(i):
  return GO_X0 + (i % GO_N) * GO_CELL, GO_Y0 + (i // GO_N) * GO_CELL


def go_point_at(pos):
  c = round((pos[0] - GO_X0) / GO_CELL)
  r = round((pos[1] - GO_Y0) / GO_CELL)
  if not (0 <= c < GO_N and 0 <= r < GO_N):
    return None
  x, y = go_xy(r * GO_N + c)
  if math.hypot(pos[0] - x, pos[1] - y) > 27:
    return None
  return r * GO_N + c


def draw_go(app):
  g = app.game
  st = current_style()
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("Go 9x9", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))
  draw_hud(app)

  if app.mode == "local":
    role = "Mode local"
  else:
    me = "NEGRES" if app.me == "B" else "BLANQUES"
    role = f"Tu: {me}  -  Bot {LEVEL_INFO[app.difficulty][0].capitalize()}"
  SCREEN.blit(FONT.render(role, True, (0, 100, 200)), (20, 60))
  draw_turn_indicator(*(st["b"] if g.cur == 1 else st["w"]))

  caps = FONT.render(
      f"Captures:  Negres {g.caps[1]}   Blanques {g.caps[2]}", True, SOFT_TEXT)
  SCREEN.blit(caps, (WIDTH // 2 - caps.get_width() // 2, 92))

  size = GO_CELL * (GO_N - 1)
  panel = pygame.Rect(GO_X0 - 34, GO_Y0 - 34, size + 68, size + 68)
  pygame.draw.rect(SCREEN, _mix(BG_COLOR, (205, 160, 85), 0.65), panel, border_radius=10)
  pygame.draw.rect(SCREEN, LINE_COLOR, panel, 3, border_radius=10)
  for i in range(GO_N):
    pygame.draw.line(SCREEN, LINE_COLOR, (GO_X0, GO_Y0 + i * GO_CELL),
                     (GO_X0 + size, GO_Y0 + i * GO_CELL), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (GO_X0 + i * GO_CELL, GO_Y0),
                     (GO_X0 + i * GO_CELL, GO_Y0 + size), 2)
  for r, c in ((2, 2), (2, 6), (6, 2), (6, 6), (4, 4)):
    pygame.draw.circle(SCREEN, LINE_COLOR, go_xy(r * GO_N + c), 5)

  for i, v in enumerate(g.board):
    if v:
      fill, border = st["b"] if v == 1 else st["w"]
      draw_disc(go_xy(i), fill, border, st["deco"], 24)

  if isinstance(g.last_move, int):
    pygame.draw.circle(SCREEN, LAST_COLOR, go_xy(g.last_move), 9, 3)

  # pista (una casella, o passar)
  if app.hint is not None and not g.winner:
    if app.hint >= 0:
      pygame.draw.circle(SCREEN, TIP_COLOR, go_xy(app.hint), 28, 4)
    else:
      t = FONT.render("Pista: passa", True, TIP_COLOR)
      SCREEN.blit(t, (WIDTH // 2 - t.get_width() // 2, GO_Y0 + size + 40))

  # previsualització de la pedra sota el ratolí
  can_play = (not g.winner and not app.result
              and (app.mode == "local" or g.turn == app.me))
  if can_play:
    i = go_point_at(pygame.mouse.get_pos())
    if i is not None and g.board[i] == 0 and g.is_legal(i):
      fill, _border = st["b"] if g.cur == 1 else st["w"]
      pygame.draw.circle(SCREEN, fill, go_xy(i), 11)

  draw_footer(app)


# ---------------------------------------------------------------
# PANTALLA DE RESULTAT (victòria / derrota / taules)
# ---------------------------------------------------------------


def result_buttons():
  panel = pygame.Rect(WIDTH // 2 - 270, 215, 540, 330)
  again = pygame.Rect(panel.x + 30, panel.bottom - 70, 230, 48)
  menu = pygame.Rect(panel.right - 260, panel.bottom - 70, 230, 48)
  return panel, again, menu


def draw_result(app):
  res = app.result
  veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
  veil.fill((0, 0, 0, 120))
  SCREEN.blit(veil, (0, 0))
  if getattr(app, "fx", None):
    fx_draw(app.fx)

  panel, again, menu = result_buttons()
  pygame.draw.rect(SCREEN, (250, 232, 195), panel, border_radius=18)
  pygame.draw.rect(SCREEN, res["color"], panel, 6, border_radius=18)

  t = RES_FONT.render(res["title"], True, res["color"])
  SCREEN.blit(t, (panel.centerx - t.get_width() // 2, panel.y + 28))

  for i, line in enumerate(res["lines"][:6]):
    s = FONT.render(line, True, TEXT_COLOR)
    SCREEN.blit(s, (panel.centerx - s.get_width() // 2, panel.y + 90 + i * 28))

  mp = pygame.mouse.get_pos()
  for rect, label in ((again, "Torna a jugar (R)"), (menu, "Menú (M)")):
    hover = rect.collidepoint(mp)
    pygame.draw.rect(
        SCREEN, (255, 240, 205) if hover else (240, 220, 175), rect, border_radius=12)
    pygame.draw.rect(
        SCREEN, HIGHLIGHT_COLOR if hover else LINE_COLOR, rect, 3, border_radius=12)
    s = FONT.render(label, True, TEXT_COLOR)
    SCREEN.blit(s, (rect.centerx - s.get_width() // 2, rect.centery - s.get_height() // 2))


# ---------------------------------------------------------------
# APLICACIÓ
# ---------------------------------------------------------------


# ---------------------------------------------------------------
# BOTIGA (pantalla)
# ---------------------------------------------------------------

CONFETTI_COLORS = ((235, 70, 70), (70, 170, 240), (250, 200, 50),
                   (90, 200, 110), (200, 100, 230))


def fx_new(style, n=70, area=None):
  """Partícules per a la celebració. area = rectangle (per a la vista prèvia)."""
  x0, y0, w, h = ((0, 0, WIDTH, HEIGHT) if area is None
                  else (area.x, area.y, area.width, area.height))
  ps = []
  for _ in range(n):
    p = dict(x=x0 + random.random() * w, y=y0 + random.random() * h,
             ph=random.random() * 6.28, s=random.randint(6, 11),
             c=random.choice(CONFETTI_COLORS),
             vx=random.uniform(-40, 40), vy=random.uniform(110, 250))
    if style == "stars":
      p.update(s=random.randint(6, 15), vx=0, vy=random.uniform(-30, -6),
               c=(255, random.randint(200, 235), random.randint(60, 140)))
    elif style == "bubbles":
      p.update(s=random.randint(5, 16), vx=random.uniform(-15, 15),
               vy=-random.uniform(60, 140), c=(185, 228, 255))
    if area is None:                       # a pantalla completa, entren de fora
      if style == "confetti":
        p["y"] = y0 - random.random() * 500
      elif style == "bubbles":
        p["y"] = y0 + h + random.random() * 300
    ps.append(p)
  return dict(style=style, ps=ps, last=time.time(), box=(x0, y0, w, h))


def fx_draw(fx, animate=True):
  now = time.time()
  dt = min(0.1, now - fx["last"]) if animate else 0
  fx["last"] = now
  x0, y0, w, h = fx["box"]
  style = fx["style"]
  for p in fx["ps"]:
    p["x"] += p["vx"] * dt
    p["y"] += p["vy"] * dt
    if animate:
      if style == "confetti" and p["y"] > y0 + h + 20:
        p["y"] = y0 - 20
      elif style != "confetti" and p["y"] < y0 - 20:
        p["y"] = y0 + h + 20
    x, y = int(p["x"]), int(p["y"])
    if style == "confetti":
      pygame.draw.rect(SCREEN, p["c"], (x, y, p["s"], max(3, p["s"] * 2 // 3)))
    elif style == "stars":
      k = 0.6 + 0.4 * abs(math.sin(now * 3 + p["ph"]))
      r = p["s"] * k
      ri = r * 0.35
      pygame.draw.polygon(SCREEN, p["c"], [
          (x, y - r), (x + ri, y - ri), (x + r, y), (x + ri, y + ri),
          (x, y + r), (x - ri, y + ri), (x - r, y), (x - ri, y - ri)])
    else:
      pygame.draw.circle(SCREEN, p["c"], (x, y), p["s"], 2)


_FX_PREVIEW = {}


def fx_preview(style, area):
  """Vista prèvia estàtica d'una celebració dins d'un rectangle."""
  key = (style, area.x, area.y, area.width, area.height)
  if key not in _FX_PREVIEW:
    _FX_PREVIEW[key] = fx_new(style, 28, area)
  prev = SCREEN.get_clip()
  SCREEN.set_clip(area)
  fx_draw(_FX_PREVIEW[key], animate=False)
  SCREEN.set_clip(prev)


def draw_shop_scene(area, board_key, style_key, mark_key):
  """Mini tauler d'escacs amb el tauler, les fitxes i la marca indicats."""
  bt = BOARD_THEMES[board_key]
  st = PIECE_STYLES[style_key]
  mk = MARK_STYLES[mark_key]["color"]
  cols, rows = 8, 4
  s = min(area.width // cols, area.height // rows)
  ox = area.x + (area.width - s * cols) // 2
  oy = area.y + (area.height - s * rows) // 2
  light = _mix(bt["bg"], (255, 255, 255), 0.45)
  dark = _mix(bt["bg"], bt["line"], 0.5)
  for r in range(rows):
    for c in range(cols):
      pygame.draw.rect(SCREEN, light if (r + c) % 2 == 0 else dark,
                       (ox + c * s, oy + r * s, s, s))
  pygame.draw.rect(SCREEN, bt["line"], (ox, oy, s * cols, s * rows), 2)
  for c, r in ((2, 2), (2, 1)):                 # marca de l'última jugada
    pygame.draw.rect(SCREEN, mk, (ox + c * s + 1, oy + r * s + 1, s - 2, s - 2),
                     max(2, s // 9))
  pieces = ((2, 1, "w", "P"), (4, 1, "b", "C"), (5, 3, "w", "T"),
            (6, 0, "b", "R"), (0, 2, "w", "A"))
  for c, r, side, letter in pieces:
    fill, border = st[side]
    cx, cy = ox + c * s + s // 2, oy + r * s + s // 2
    draw_disc((cx, cy), fill, border, st["deco"], max(5, int(s * 0.4)))
    if s >= 30:
      lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
      t = SMALL.render(letter, True, (40, 40, 40) if lum > 150 else (245, 245, 245))
      SCREEN.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))


def draw_c4_mini(area, board_key, style_key):
  bt = BOARD_THEMES[board_key]
  st = PIECE_STYLES[style_key]
  cols, rows = 7, 5
  cell = min(area.width // cols, area.height // rows)
  w, h = cell * cols, cell * rows
  x0, y0 = area.x + (area.width - w) // 2, area.y + (area.height - h) // 2
  pygame.draw.rect(SCREEN, bt["c4"], (x0, y0, w, h), border_radius=8)
  discs = {(3, 4): 1, (3, 3): 2, (2, 4): 2, (4, 4): 1, (2, 3): 1}
  for r in range(rows):
    for c in range(cols):
      pos = (x0 + c * cell + cell // 2, y0 + r * cell + cell // 2)
      v = discs.get((c, r))
      if v:
        fill, border = st["c%d" % v]
        pygame.draw.circle(SCREEN, fill, pos, cell // 2 - 3)
        pygame.draw.circle(SCREEN, border, pos, cell // 2 - 3, 2)
      else:
        pygame.draw.circle(SCREEN, bt["c4dark"], pos, cell // 2 - 3)


def pack_keys(pack):
  """(tauler, fitxes, marca) que mostra un pack (el que no inclou, l'actual)."""
  d = dict(pack["items"])
  eq = SAVE["equipped"]
  return (d.get("boards", eq["boards"]), d.get("pieces", eq["pieces"]),
          d.get("marks", eq["marks"]))


def draw_item_visual(tab, key, area, big=False):
  """Vista prèvia d'un element de la botiga dins de 'area'."""
  item = shop_table(tab)[key]
  eq = SAVE["equipped"]
  if tab == "boards":
    draw_shop_scene(area, key, eq["pieces"], eq["marks"])
  elif tab == "pieces":
    draw_shop_scene(area, eq["boards"], key, eq["marks"])
  elif tab == "marks":
    draw_shop_scene(area, eq["boards"], eq["pieces"], key)
  elif tab == "packs":
    draw_shop_scene(area, *pack_keys(item))
  elif tab == "fx":
    pygame.draw.rect(SCREEN, (40, 36, 52), area, border_radius=8)
    if key == "none":
      t = FONT.render("Sense efectes", True, (200, 190, 210))
      SCREEN.blit(t, (area.centerx - t.get_width() // 2,
                      area.centery - t.get_height() // 2))
    else:
      fx_preview(key, area)
  else:                                         # extres
    pygame.draw.rect(SCREEN, (250, 240, 215), area, border_radius=8)
    t = (BIG_FONT if big else TITLE_FONT).render(item["big"], True, TEXT_COLOR)
    SCREEN.blit(t, (area.centerx - t.get_width() // 2, area.centery - t.get_height()))
    s = FONT.render(item["small"], True, SOFT_TEXT)
    SCREEN.blit(s, (area.centerx - s.get_width() // 2, area.centery + 4))


def shop_tab_rects():
  return [(pygame.Rect(23 + i * 110, 100, 104, 40), key, label)
          for i, (key, label) in enumerate(SHOP_TABS)]


def shop_cards(tab):
  cards = []
  for i, key in enumerate(shop_table(tab)):
    col, row = i % 3, i // 3
    cards.append((pygame.Rect(35 + col * 215, 160 + row * 205, 200, 190), key))
  return cards


def shop_modal_rects():
  panel = pygame.Rect(60, 110, 580, 490)
  primary = pygame.Rect(panel.x + 30, panel.bottom - 70, 270, 52)
  close = pygame.Rect(panel.right - 230, panel.bottom - 70, 200, 52)
  return panel, primary, close


def draw_shop_card(rect, tab, key, hover):
  item = shop_table(tab)[key]
  price, orig = price_of(tab, key)
  rar_name, rar_col = rarity(base_price(tab, key))
  owned = is_owned(tab, key)
  equipped = tab in COSMETIC_TABS and SAVE["equipped"][tab] == key
  if tab == "packs":
    locked = not owned and not pack_req(item)[0]
  else:
    locked = tab != "extras" and not owned and not req_check(item.get("req"))[0]

  pygame.draw.rect(SCREEN, (255, 240, 205) if hover else (250, 232, 195),
                   rect, border_radius=14)
  pygame.draw.rect(SCREEN, HIGHLIGHT_COLOR if equipped else LINE_COLOR, rect,
                   5 if equipped else 3, border_radius=14)
  pygame.draw.rect(SCREEN, rar_col, (rect.x + 16, rect.y + 8, rect.width - 32, 5),
                   border_radius=3)
  area = pygame.Rect(rect.x + 15, rect.y + 20, 170, 86)
  draw_item_visual(tab, key, area)
  if locked:
    draw_padlock(area.centerx, area.centery)
  if (tab, key) == deal_key() and orig:
    tag = pygame.Rect(area.x + 4, area.y + 4, 46, 20)
    pygame.draw.rect(SCREEN, COLOR_LOSE, tag, border_radius=6)
    s = SMALL.render("-30%", True, (255, 255, 255))
    SCREEN.blit(s, (tag.centerx - s.get_width() // 2, tag.centery - s.get_height() // 2))

  name = FONT.render(item["name"], True, TEXT_COLOR)
  SCREEN.blit(name, (rect.centerx - name.get_width() // 2, rect.y + 112))
  if equipped:
    txt, col = "EQUIPAT", COLOR_WIN
  elif owned:
    txt, col = ("Ja el tens", COLOR_WIN) if tab == "packs" else ("Clica per equipar", (0, 100, 200))
  elif locked:
    txt, col = "Bloquejat", COLOR_LOSE
  elif orig:
    txt, col = f"{price} (abans {orig})", COLOR_LOSE
  else:
    txt, col = f"{price} punts", (TEXT_COLOR if SAVE["points"] >= price else COLOR_LOSE)
  s = SMALL.render(txt, True, col)
  SCREEN.blit(s, (rect.centerx - s.get_width() // 2, rect.y + 146))
  r = SMALL.render(rar_name, True, rar_col)
  SCREEN.blit(r, (rect.centerx - r.get_width() // 2, rect.y + 167))


def draw_shop_detail(app):
  tab, key = app.shop_sel
  item = shop_table(tab)[key]
  panel, primary, close = shop_modal_rects()
  price, orig = price_of(tab, key)
  rar_name, rar_col = rarity(base_price(tab, key))
  mouse = pygame.mouse.get_pos()

  veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
  veil.fill((0, 0, 0, 150))
  SCREEN.blit(veil, (0, 0))
  pygame.draw.rect(SCREEN, (250, 232, 195), panel, border_radius=18)
  pygame.draw.rect(SCREEN, rar_col, panel, 6, border_radius=18)

  t = TITLE_FONT.render(item["name"], True, TEXT_COLOR)
  SCREEN.blit(t, (panel.x + 30, panel.y + 18))
  r = FONT.render(rar_name, True, rar_col)
  SCREEN.blit(r, (panel.right - 30 - r.get_width(), panel.y + 22))

  area = pygame.Rect(panel.x + 30, panel.y + 66, 520, 160)
  eq = SAVE["equipped"]
  if tab in ("boards", "pieces", "marks", "packs"):
    scene = pygame.Rect(area.x, area.y, 320, 160)
    if tab == "packs":
      bk, pk, _mk = pack_keys(item)
    else:
      bk = key if tab == "boards" else eq["boards"]
      pk = key if tab == "pieces" else eq["pieces"]
    draw_item_visual(tab, key, scene, big=True)
    draw_c4_mini(pygame.Rect(area.x + 340, area.y, 180, 160), bk, pk)
  else:
    draw_item_visual(tab, key, area, big=True)

  y = panel.y + 240
  for line in wrap_text(item["desc"], SMALL, 520)[:3]:
    SCREEN.blit(SMALL.render(line, True, TEXT_COLOR), (panel.x + 30, y))
    y += 21

  y = panel.y + 312
  pts = SAVE["points"]
  owned = is_owned(tab, key)
  if tab == "packs":
    names = ", ".join(shop_table(t2)[k2]["name"] for t2, k2 in item["items"])
    for line in wrap_text(f"Inclou: {names}", SMALL, 520)[:2]:
      SCREEN.blit(SMALL.render(line, True, SOFT_TEXT), (panel.x + 30, y))
      y += 21
    ok, why = pack_req(item)
    if not owned and not ok:
      for line in wrap_text(why, SMALL, 520)[:2]:
        SCREEN.blit(SMALL.render(line, True, COLOR_LOSE), (panel.x + 30, y))
        y += 21
  elif tab == "extras":
    stock = SAVE["items"][item["field"]]
    SCREEN.blit(SMALL.render(f"Ara en tens: {stock}", True, SOFT_TEXT), (panel.x + 30, y))
    y += 21
  elif not owned:
    ok, why = req_check(item.get("req"))
    if not ok:
      SCREEN.blit(SMALL.render(why, True, COLOR_LOSE), (panel.x + 30, y))
      y += 21
  if not owned or tab == "extras":
    ptxt = f"Preu: {price} punts" + (f"  (abans {orig}, oferta del dia)" if orig else "")
    SCREEN.blit(FONT.render(ptxt, True, TEXT_COLOR), (panel.x + 30, panel.y + 372))
    if pts < price:
      miss = SMALL.render(f"Et falten {price - pts} punts", True, COLOR_LOSE)
      SCREEN.blit(miss, (panel.right - 30 - miss.get_width(), panel.y + 376))
  if app.shop_msg and time.time() - app.shop_msg[2] < 2.5:
    m = FONT.render(app.shop_msg[0], True, app.shop_msg[1])
    SCREEN.blit(m, (panel.centerx - m.get_width() // 2, panel.y + 404))

  label, enabled = shop_primary(tab, key)
  for rect, text, en in ((primary, label, enabled), (close, "Tanca", True)):
    hover = en and rect.collidepoint(mouse)
    fill = ((255, 240, 205) if hover else (245, 226, 185)) if en else (222, 208, 182)
    pygame.draw.rect(SCREEN, fill, rect, border_radius=12)
    pygame.draw.rect(SCREEN, HIGHLIGHT_COLOR if hover else (LINE_COLOR if en else (170, 155, 130)),
                     rect, 4 if hover else 3, border_radius=12)
    s = FONT.render(text, True, TEXT_COLOR if en else (160, 148, 128))
    SCREEN.blit(s, (rect.centerx - s.get_width() // 2, rect.centery - s.get_height() // 2))


def draw_shop(app):
  SCREEN.fill(BG_COLOR)

  t = BIG_FONT.render("Botiga", True, TEXT_COLOR)
  SCREEN.blit(t, (WIDTH // 2 - t.get_width() // 2, 25))
  pts = FONT.render(f"Punts: {SAVE['points']}", True, TEXT_COLOR)
  SCREEN.blit(pts, (WIDTH - 20 - pts.get_width(), 30))

  mouse = pygame.mouse.get_pos()
  modal = app.shop_sel is not None
  for rect, key, label in shop_tab_rects():
    sel = key == app.shop_tab
    hover = not modal and rect.collidepoint(mouse)
    pygame.draw.rect(SCREEN, (255, 240, 205) if (sel or hover) else (245, 226, 185),
                     rect, border_radius=10)
    pygame.draw.rect(SCREEN, HIGHLIGHT_COLOR if sel else LINE_COLOR, rect,
                     4 if sel else 3, border_radius=10)
    s = SMALL.render(label, True, TEXT_COLOR)
    SCREEN.blit(s, (rect.centerx - s.get_width() // 2, rect.centery - s.get_height() // 2))

  for rect, key in shop_cards(app.shop_tab):
    draw_shop_card(rect, app.shop_tab, key, not modal and rect.collidepoint(mouse))

  # peu: oferta del dia, estoc i ajuda
  dt, dk = deal_key()
  dname = shop_table(dt)[dk]["name"]
  deal = SMALL.render(
      f"Oferta del dia: {TAB_NAMES[dt]} {dname} amb un 30% de descompte", True, COLOR_LOSE)
  SCREEN.blit(deal, (WIDTH // 2 - deal.get_width() // 2, 580))
  it = SAVE["items"]
  stock = SMALL.render(
      f"Tens: {it['hints']} pistes  -  {it['undos']} desfer  -  x2 en {it['double']} victòries",
      True, SOFT_TEXT)
  SCREEN.blit(stock, (WIDTH // 2 - stock.get_width() // 2, 606))
  w = SMALL.render(f"Victòries contra el bot: {total_wins()}", True, SOFT_TEXT)
  SCREEN.blit(w, (WIDTH // 2 - w.get_width() // 2, 632))

  h = FONT.render("Clica un element per veure'n el detall", True, SOFT_TEXT)
  SCREEN.blit(h, (WIDTH // 2 - h.get_width() // 2, HEIGHT - 60))
  draw_button(back_button_rect(), "< Enrere")

  if modal:
    draw_shop_detail(app)


def point_at(mouse_pos):
  mx, my = mouse_pos
  for point, pos in POINT_POSITIONS.items():
    if math.hypot(mx - pos[0], my - pos[1]) <= 20:
      return point
  return None


class App:

  def __init__(self):
    self.running = True
    self.state = "main"        # main, modes, diff, side, settings, play
    self.kind = "morris"       # morris | c4
    self.mode = "local"        # local | bot | online
    self.difficulty = SAVE["difficulty"]
    self.rules = Rules.from_dict(SAVE["rules"])
    self.human_first = True
    self.game = None
    self.bot = None
    self.me = None
    self.bot_role = None
    self.bot_due = None
    self.hint = None
    self.assisted = False      # ha usat desfer o pista
    self.hinted = False        # ha usat alguna pista
    self.result = None
    self.over_time = None
    self.anim = None
    self.anim_key = None
    self.shop_tab = "boards"   # boards | pieces | marks | fx | extras | packs
    self.shop_sel = None       # (pestanya, clau) de la finestra de detall oberta
    self.shop_msg = None       # (text, color, instant)
    self.fx = None             # celebració de victòria en marxa
    apply_theme()

  # ---------- menús ----------
  def menu_def(self):
    s = self.state
    if s == "main":
      return ("Jocs de taula", f"Punts totals: {SAVE['points']}", [
          ("morris", "TRES EN RATLLA", "Tauler de tres quadrats", True),
          ("c4", "4 EN RATLLA", "Fitxes que cauen", True),
          ("chess", "ESCACS", "Amb enroc i captura al pas", True),
          ("go", "GO 9x9", "Captura territori amb pedres", True),
          ("shop", "BOTIGA", "Taulers i fitxes a canvi de punts", True),
          ("settings", "REGLES", "Variants de Tres en ratlla", True),
      ], "Clica una opció o prem 1 - 6")
    if s == "modes":
      online_ok = self.kind == "morris" and HAS_JS
      if self.kind != "morris":
        online_desc = "Només a Tres en ratlla"
      elif not HAS_JS:
        online_desc = "Només disponible al navegador"
      else:
        online_desc = "Regles estàndard, 2 dispositius"
      return (GAME_TITLES[self.kind], "Tria el mode de joc", [
          ("local", "JUGAR EN LOCAL", "Dos jugadors a la mateixa pantalla", True),
          ("bot", "CONTRA L'ORDINADOR", "Guanya punts per cada victòria", True),
          ("online", "JUGAR ONLINE", online_desc, online_ok),
      ], "Clica una opció o prem 1 / 2 / 3   -   M = enrere")
    if s == "diff":
      opts = []
      for k in LEVELS:
        locked = is_locked(k)
        if locked:
          desc = f"Et falten {UNLOCK_POINTS - SAVE['points']} punts per desbloquejar"
        else:
          desc = f"{LEVEL_INFO[k][1]} (+{POINTS[k]} punts)"
        opts.append((k, LEVEL_INFO[k][0], desc, not locked, locked))
      return ("Dificultat", "Com de fort vols el bot?", opts,
              "Clica una opció o prem 1 / 2 / 3 / 4   -   M = enrere")
    if s == "side":
      a, b = SIDE_DESC[self.kind]
      return ("Qui comença?", "El primer jugador comença la partida", [
          ("first", "COMENCES TU", f"Tu portes {a}", True),
          ("second", "COMENÇA L'ORDINADOR", f"Tu portes {b}", True),
          ("random", "A L'ATZAR", "Es decideix a sort", True),
      ], "Clica una opció o prem 1 / 2 / 3   -   M = enrere")
    r = self.rules
    return ("Regles", "Tres en ratlla (es desen soles)", [
        ("pieces", f"FITXES: {r.pieces}", "Prem per canviar (5 / 7 / 9)", True),
        ("fly", f"MOVIMENT: {'LLIURE' if r.fly else 'ADJACENT'}",
         "Quan no queden fitxes per col·locar", True),
        ("diag", f"DIAGONALS: {'SÍ' if r.diag else 'NO'}",
         "Línies de tres per les cantonades", True),
        ("back", "TORNA", "", True),
    ], "L'online sempre usa les regles estàndard")

  def process_menu(self, events):
    title, sub, opts, hint = self.menu_def()
    pick = menu_pick(opts, events)
    if pick is None and self.state in ("modes", "diff", "side"):
      for ev in events:
        if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
            and back_button_rect().collidepoint(ev.pos)):
          pick = "back"
    if pick is None:
      return
    s = self.state
    if s == "main":
      if pick in GAMES:
        self.kind = pick
        self.state = "modes"
      elif pick == "shop":
        self.state = "shop"
        self.shop_msg = None
        self.shop_sel = None
      elif pick == "settings":
        self.state = "settings"
    elif s == "modes":
      if pick == "back":
        self.state = "main"
      else:
        self.mode = pick
        if pick == "bot":
          self.state = "diff"
        else:
          self.start_game()
    elif s == "diff":
      if pick == "back":
        self.state = "modes"
      elif is_locked(pick):
        return                    # nivell bloquejat: no es pot triar
      else:
        self.difficulty = pick
        SAVE["difficulty"] = pick
        write_save()
        self.state = "side"
    elif s == "side":
      if pick == "back":
        self.state = "diff"
      else:
        self.human_first = (
            random.random() < 0.5 if pick == "random" else pick == "first")
        self.start_game()
    elif s == "settings":
      if pick == "back":
        self.state = "main"
        return
      if pick == "pieces":
        self.rules.pieces = {5: 7, 7: 9, 9: 5}[self.rules.pieces]
      elif pick == "fly":
        self.rules.fly = not self.rules.fly
      elif pick == "diag":
        self.rules.diag = not self.rules.diag
      SAVE["rules"] = self.rules.to_dict()
      write_save()

  # ---------- escacs / go ----------
  def chess_flip(self):
    """Si portes negres contra el bot, el tauler es gira."""
    return self.kind == "chess" and self.mode == "bot" and self.me == "B"

  def board_click(self, target):
    g = self.game
    if target is None or self.result:
      return
    if self.mode == "bot" and g.turn != self.me:
      return
    role = g.turn if self.mode == "local" else self.me
    if g.handle_click(target, role):
      self.hint = None

  def can_pass(self):
    g = self.game
    if g.winner or self.result:
      return False
    return self.mode == "local" or g.turn == self.me

  def go_pass(self):
    if not self.can_pass():
      return
    g = self.game
    role = g.turn if self.mode == "local" else self.me
    if g.pass_move(role):
      self.hint = None

  # ---------- botiga ----------
  def process_shop(self, events):
    for ev in events:
      if ev.type == pygame.QUIT:
        self.running = False
        return
      if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_m):
        if self.shop_sel:
          self.shop_sel = None
        else:
          self.state = "main"
        return
      if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        if self.shop_sel:
          panel, primary, close = shop_modal_rects()
          tab, key = self.shop_sel
          if close.collidepoint(ev.pos) or not panel.collidepoint(ev.pos):
            self.shop_sel = None
          elif primary.collidepoint(ev.pos) and shop_primary(tab, key)[1]:
            self.shop_action(tab, key)
          return
        if back_button_rect().collidepoint(ev.pos):
          self.state = "main"
          return
        for rect, key, _label in shop_tab_rects():
          if rect.collidepoint(ev.pos):
            self.shop_tab = key
            self.shop_msg = None
            return
        for rect, key in shop_cards(self.shop_tab):
          if rect.collidepoint(ev.pos):
            self.shop_sel = (self.shop_tab, key)
            self.shop_msg = None
            return

  def shop_say(self, text, ok=True):
    self.shop_msg = (text, COLOR_WIN if ok else COLOR_LOSE, time.time())

  def shop_action(self, tab, key):
    """Compra (o equipa) l'element obert a la finestra de detall."""
    item = shop_table(tab)[key]
    price, _orig = price_of(tab, key)
    if tab == "extras":
      if SAVE["points"] < price:
        return self.shop_say(f"Et falten {price - SAVE['points']} punts", False)
      field = item["field"]
      if SAVE["items"][field] + item["amount"] > STOCK_MAX:
        return self.shop_say("Ja en tens molts", False)
      SAVE["points"] -= price
      SAVE["items"][field] += item["amount"]
      msg = f"Comprat: {item['name']}!"
    elif tab == "packs":
      if not pack_unowned(item):
        return self.shop_say("Ja tens tot el pack", False)
      ok, why = pack_req(item)
      if not ok:
        return self.shop_say(why, False)
      if SAVE["points"] < price:
        return self.shop_say(f"Et falten {price - SAVE['points']} punts", False)
      SAVE["points"] -= price
      for t, k in item["items"]:
        if k not in SAVE["owned"][t]:
          SAVE["owned"][t].append(k)
        SAVE["equipped"][t] = k            # el pack s'equipa sencer
      msg = f"Pack comprat i equipat: {item['name']}!"
    elif key in SAVE["owned"][tab]:
      SAVE["equipped"][tab] = key
      msg = "Equipat!"
    else:
      ok, why = req_check(item.get("req"))
      if not ok:
        return self.shop_say(why, False)
      if SAVE["points"] < price:
        return self.shop_say(f"Et falten {price - SAVE['points']} punts", False)
      SAVE["points"] -= price
      SAVE["owned"][tab].append(key)
      SAVE["equipped"][tab] = key
      msg = f"Comprat: {item['name']}!"
    apply_theme()
    write_save()
    self.shop_say(msg)

  # ---------- inici / final de partida ----------
  def start_game(self):
    firsts = (FIRST[self.kind], SECOND[self.kind])
    if self.kind == "morris":
      rules = Rules() if self.mode == "online" else self.rules
      self.game = Morris(rules, track=(self.mode != "online"))
    elif self.kind == "c4":
      self.game = Connect4()
    elif self.kind == "chess":
      self.game = Chess()
    else:
      self.game = Go()

    # seguretat: sense 2000 punts no es pot jugar l'impossible
    if self.mode == "bot" and is_locked(self.difficulty):
      self.difficulty = "hard"

    self.me = self.bot_role = self.bot = None
    if self.mode == "bot":
      self.me = firsts[0] if self.human_first else firsts[1]
      self.bot_role = firsts[1] if self.human_first else firsts[0]
      params = BOT_PARAMS[self.kind][self.difficulty]
      self.bot = make_bot(self.kind, params)
    elif self.mode == "online":
      start_online_engine()
      self.me = detect_online_role()
    self.reset_view()
    self.assisted = False
    self.hinted = False
    self.state = "play"

  def reset_view(self):
    self.fx = None
    self.hint = None
    self.result = None
    self.over_time = None
    self.bot_due = None
    self.reset_anim()

  def reset_anim(self):
    self.anim = None
    if self.game:
      self.anim_key = (self.game.move_count, self.game.last_move)

  def restart(self):
    if self.mode == "online":
      new_count = self.game.move_count + 1
      self.game = Morris(Rules(), track=False)
      self.game.move_count = new_count
      push_firebase_state(self.game.to_dict())
      self.reset_view()
      self.assisted = False
      self.hinted = False
    else:
      self.start_game()

  def leave(self):
    self.state = "main"
    self.reset_view()

  def finish(self):
    g, kind, mode = self.game, self.kind, self.mode
    winner, draw = g.winner, g.draw
    res = dict(title="", lines=[], color=COLOR_DRAW)
    lines = res["lines"]
    blocked = kind == "morris" and g.blocked and winner

    if mode == "bot":
      rec = SAVE["records"][kind][self.difficulty]
      base = POINTS[self.difficulty]
      if winner == self.me:
        if self.hinted:
          pts = 1                       # amb pista: només 1 punt
        elif self.assisted:
          pts = max(1, base // 2)       # amb desfer: la meitat
        else:
          pts = base
        doubled = SAVE["items"]["double"] > 0
        if doubled:                     # multiplicador x2 de la botiga
          pts *= 2
          SAVE["items"]["double"] -= 1
        rec[0] += 1
        res["title"], res["color"] = "HAS GUANYAT!", COLOR_WIN
        if blocked:
          lines.append("L'ordinador s'ha quedat sense moviments")
        lines.append(f"+{pts} punts")
        if self.hinted:
          lines.append("(només 1 punt per haver usat la pista)")
        elif self.assisted:
          lines.append("(meitat de punts per haver usat desfer)")
        if doubled:
          lines.append(f"Multiplicador x2! (en queden {SAVE['items']['double']})")
      elif draw:
        pts = max(1, base // 5)
        if self.hinted:
          pts = 1
        elif self.assisted:
          pts = max(1, pts // 2)
        rec[2] += 1
        res["title"], res["color"] = "TAULES", COLOR_DRAW
        lines.append(draw_text_for(g, kind))
        lines.append(f"+{pts} punts")
      else:
        pts = 0
        rec[1] += 1
        res["title"], res["color"] = "HAS PERDUT...", COLOR_LOSE
        if blocked:
          lines.append("T'has quedat sense moviments")
        lines.append("Torna-ho a provar!")
      was_locked = is_locked("impossible")
      SAVE["points"] += pts
      if SAVE["points"] >= UNLOCK_POINTS:
        SAVE["unlocked"] = True              # ja queda desbloquejat per sempre
      lines.append(f"Total: {SAVE['points']} punts")
      if was_locked and SAVE["unlocked"]:
        lines.append("Has desbloquejat el nivell IMPOSSIBLE!")

    elif mode == "local":
      rec = SAVE["records"][kind]["local"]
      if draw:
        rec[2] += 1
        res["title"] = "TAULES"
        lines.append(draw_text_for(g, kind))
      else:
        rec[0 if winner == FIRST[kind] else 1] += 1
        res["title"], res["color"] = f"GUANYEN {side_label(kind, winner)}!", COLOR_WIN
        if blocked:
          lines.append("L'adversari s'ha quedat sense moviments")

    else:
      if winner == self.me:
        res["title"], res["color"] = "HAS GUANYAT!", COLOR_WIN
      else:
        res["title"], res["color"] = "HAS PERDUT...", COLOR_LOSE

    if kind == "go" and g.score_text:
      lines.insert(0, g.score_text)
    if res["color"] == COLOR_WIN and SAVE["equipped"]["fx"] != "none":
      self.fx = fx_new(SAVE["equipped"]["fx"])      # celebració de la botiga
    self.result = res
    write_save()

  # ---------- ajudes ----------
  def can_undo(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return False
    if SAVE["items"]["undos"] <= 0 and SAVE["points"] < undo_cost(self):
      return False                          # ni estoc ni punts
    if self.mode == "local":
      return bool(g.stack)
    return any(s["turn"] == self.me for s in g.stack)

  def can_hint(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return False
    if self.hint is not None:               # ja n'hi ha una pista a la pantalla
      return False
    if SAVE["items"]["hints"] <= 0 and SAVE["points"] < hint_cost(self):
      return False                          # ni estoc ni punts
    return self.mode != "bot" or g.turn == self.me

  def press(self, key):
    if key == "restart":
      self.restart()
    elif key == "menu":
      self.leave()
    elif key == "undo":
      self.do_undo()
    elif key == "hint":
      self.do_hint()
    elif key == "pass":
      self.go_pass()

  def do_undo(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return
    if SAVE["items"]["undos"] <= 0 and SAVE["points"] < undo_cost(self):
      return
    changed = False
    if self.mode == "local":
      changed = g.undo_one()
    elif any(s["turn"] == self.me for s in g.stack):
      while g.stack:
        g.undo_one()
        changed = True
        if g.turn == self.me:
          break
    if changed:
      if SAVE["items"]["undos"] > 0:         # primer es gasta l'estoc del pack
        SAVE["items"]["undos"] -= 1
      else:
        SAVE["points"] -= undo_cost(self)    # si no, desfer costa punts
      self.assisted = True
      self.hint = None
      self.bot_due = None
      self.reset_anim()
      write_save()

  def do_hint(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return
    if self.mode == "bot" and g.turn != self.me:
      return
    if self.anim and self.anim.active():
      return
    if self.hint is not None:
      return
    if SAVE["items"]["hints"] <= 0 and SAVE["points"] < hint_cost(self):
      return
    # la pista usa el bot més fort: sempre és la millor jugada que sap trobar
    h = make_bot(self.kind, HINT_PARAMS[self.kind]).choose(g, g.turn)
    if self.kind == "go" and h is None:
      h = -1                                # la millor jugada és passar
    if h is None:
      return
    self.hint = h
    if SAVE["items"]["hints"] > 0:          # primer es gasta l'estoc del pack
      SAVE["items"]["hints"] -= 1
    else:
      SAVE["points"] -= hint_cost(self)     # si no, la pista costa punts
    self.assisted = True
    self.hinted = True
    write_save()

  # ---------- entrada ----------
  def process(self, events):
    for ev in events:
      if ev.type == pygame.QUIT:
        self.running = False
        return
    if self.state == "play":
      self.process_play(events)
    elif self.state == "shop":
      self.process_shop(events)
    else:
      self.process_menu(events)

  def c4_click(self, col):
    g = self.game
    if col is None or (self.anim and self.anim.active()):
      return
    if self.mode == "bot" and g.turn != self.me:
      return
    role = g.turn if self.mode == "local" else self.me
    if g.drop(col, role):
      self.hint = None

  def process_play(self, events):
    for ev in events:
      if ev.type == pygame.KEYDOWN:
        k = ev.key
        if k in (pygame.K_m, pygame.K_ESCAPE):
          self.leave()
          return
        if k == pygame.K_r:
          self.restart()
        elif k == pygame.K_z:
          self.do_undo()
        elif k == pygame.K_h:
          self.do_hint()
        elif k == pygame.K_p and self.kind == "go":
          self.go_pass()
        elif self.kind == "c4" and not self.result:
          for i, ks in enumerate(C4_KEYS):
            if k in ks:
              self.c4_click(i)

      elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        if self.result:
          _, again, menu = result_buttons()
          if again.collidepoint(ev.pos):
            self.restart()
          elif menu.collidepoint(ev.pos):
            self.leave()
            return
          continue
        rects, _ = game_buttons(self)
        pressed = False
        for rect, key, en in rects:
          if rect.collidepoint(ev.pos):
            pressed = True
            if en:
              self.press(key)
            break
        if pressed:
          if self.state != "play":
            return
          continue
        g = self.game
        if self.kind == "morris":
          point = point_at(ev.pos)
          if point is None:
            continue
          if self.mode == "local":
            ok = g.handle_click(point, g.turn)
          elif self.mode == "bot":
            ok = g.turn == self.me and g.handle_click(point, self.me)
          else:
            ok = g.handle_click(point, self.me)
            if ok:
              push_firebase_state(g.to_dict())
          if ok:
            self.hint = None
        elif self.kind == "c4":
          if 90 <= ev.pos[1] <= C4_Y0 + C4_ROWS * C4_CELL + 20:
            self.c4_click(c4_col_at(ev.pos[0]))
        elif self.kind == "chess":
          self.board_click(chess_sq_at(ev.pos, self.chess_flip()))
        else:
          self.board_click(go_point_at(ev.pos))

  # ---------- actualització ----------
  def sync_anim(self):
    g = self.game
    key = (g.move_count, g.last_move)
    if key == self.anim_key:
      return
    self.anim_key = key
    self.anim = None
    if self.kind in ("chess", "go"):
      return                      # sense animació en aquests jocs
    lm = g.last_move
    if not lm:
      return
    if self.kind == "morris":
      src, dst = lm
      owner = g.board.get(dst)
      if owner is None:
        return
      self.anim = MoveAnim(
          owner, POINT_POSITIONS[src] if src else None, dst, 0.3 if src else 0.18)
    else:
      c, r = lm
      self.anim = C4Anim(c, r, g.grid[c][r], 0.2 + 0.06 * (C4_ROWS - 1 - r))

  def update(self):
    if self.state != "play":
      return
    g = self.game
    if self.mode == "online":
      remote = check_firebase_state()
      if remote:
        g.from_dict(remote)
    self.sync_anim()

    over = bool(g.winner or g.draw)
    if self.result and not over:
      self.result = None
      self.over_time = None
    if over and self.result is None:
      if self.over_time is None:
        self.over_time = time.time()
      elif (time.time() - self.over_time > 0.8
            and not (self.anim and self.anim.active())):
        self.finish()

  def bot_step(self):
    """Torn del bot: després del flip, perquè 'pensant...' ja s'hagi dibuixat."""
    if self.state != "play" or self.mode != "bot" or self.result:
      return
    g = self.game
    if g.winner or g.draw or g.turn != self.bot_role:
      self.bot_due = None
      return
    if self.anim and self.anim.active():
      self.bot_due = None
      return
    now = pygame.time.get_ticks()
    if self.bot_due is None:
      self.bot_due = now + 250
    elif now >= self.bot_due:
      self.bot.play(g, self.bot_role)
      self.bot_due = None
      self.hint = None

  # ---------- dibuix ----------
  def draw(self):
    if self.state == "play":
      {"morris": draw_morris, "c4": draw_c4,
       "chess": draw_chess, "go": draw_go}[self.kind](self)
      if self.result:
        draw_result(self)
    elif self.state == "shop":
      draw_shop(self)
    else:
      title, sub, opts, hint = self.menu_def()
      draw_choice_menu(title, sub, opts, pygame.mouse.get_pos(), hint)
      if self.state in ("modes", "diff", "side"):
        draw_button(back_button_rect(), "< Enrere")


async def main():
  clock = pygame.time.Clock()
  app = App()

  while app.running:
    clock.tick(60)
    events = pygame.event.get()
    app.process(events)
    app.update()
    app.draw()
    pygame.display.flip()
    app.bot_step()
    await asyncio.sleep(0)

  pygame.quit()
  sys.exit()


if __name__ == "__main__":
  asyncio.run(main())
