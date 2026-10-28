import asyncio
import json
import math
import random
import sys
import time

import pygame

# "js" només existeix al navegador (pygbag). A l'ordinador no, i el mode
# local i el mode contra l'ordinador funcionen igualment.
try:
  import js
  HAS_JS = True
except ImportError:
  js = None
  HAS_JS = False

# Inicialització de Pygame
pygame.init()
pygame.font.init()

# REGLA: quan a un jugador ja no li queden fitxes per col·locar, pot moure
# QUALSEVOL de les seves fitxes a QUALSEVOL punt buit del tauler.
# Posa-ho a False per tornar a la regla antiga (només a punts adjacents).
FLY_WHEN_NO_PIECES_LEFT = True

# Taules: si la mateixa posició (amb el mateix torn) es repeteix aquest
# nombre de cops, la partida s'acaba en empat (només local i contra el bot).
REPETITIONS_FOR_DRAW = 3

# CONFIGURACIÓ DE LA PANTALLA
WIDTH, HEIGHT = 700, 750
BOARD_SIZE = 550
OFFSET_X = (WIDTH - BOARD_SIZE) // 2
OFFSET_Y = 110

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tres en ratlla")

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
WHITE_PIECE = (240, 240, 240)
WHITE_BORDER = (100, 100, 100)
BLACK_PIECE = (40, 40, 40)
BLACK_BORDER = (0, 0, 0)
HIGHLIGHT_COLOR = (0, 220, 100)
WIN_LINE_COLOR = (30, 200, 80)
HINT_COLOR = (0, 190, 90)

FONT = pygame.font.SysFont("arial", 20, bold=True)
TITLE_FONT = pygame.font.SysFont("arial", 28, bold=True)
BIG_FONT = pygame.font.SysFont("arial", 44, bold=True)

# Coordenades lògiques dels 24 punts
POINTS_CONFIG = [
    (0, 0, 0),
    (0, 0, 1),
    (0, 0, 2),
    (0, 1, 2),
    (0, 2, 2),
    (0, 2, 1),
    (0, 2, 0),
    (0, 1, 0),
    (1, 0, 0),
    (1, 0, 1),
    (1, 0, 2),
    (1, 1, 2),
    (1, 2, 2),
    (1, 2, 1),
    (1, 2, 0),
    (1, 1, 0),
    (2, 0, 0),
    (2, 0, 1),
    (2, 0, 2),
    (2, 1, 2),
    (2, 2, 2),
    (2, 2, 1),
    (2, 2, 0),
    (2, 1, 0),
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


def can_move_to(origin, target, board):
  """Diu si una fitxa pot anar de 'origin' a 'target' (que ha d'estar buit).

  Amb FLY_WHEN_NO_PIECES_LEFT activat, pot anar a qualsevol punt buit.
  Si no, només als punts adjacents.
  """
  if board[target] is not None:
    return False
  if FLY_WHEN_NO_PIECES_LEFT:
    return True
  return target in ADJACENCY[origin]


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


class TicTacToeOnline:

  def __init__(self, track_draws=False):
    self.board = {p: None for p in POINTS_CONFIG}
    self.turn = "W"
    self.unplaced = {"W": 7, "B": 7}
    self.selected_point = None
    self.winner = None
    self.winning_line = None
    self.move_count = 0  # Comptador de versió per evitar race conditions
    # taules (només local / bot, no es sincronitza online)
    self.track_draws = track_draws
    self.draw = False
    self.history = {}

  def to_dict(self):
    return {
        "board": {
            point_to_str(k): v
            for k, v in self.board.items()
            if v is not None
        },
        "turn": self.turn,
        "unplaced": self.unplaced,
        "winner": self.winner,
        "winning_line": (
            [point_to_str(p) for p in self.winning_line]
            if self.winning_line
            else None
        ),
        "move_count": self.move_count,
    }

  def from_dict(self, data):
    if not data or not isinstance(data, dict):
      return

    remote_count = int(data.get("move_count", 0))

    # Només actualitza si la dades rebuda és MÉS RECENT que la local
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
    if isinstance(raw_unplaced, dict):
      self.unplaced = {
          "W": int(raw_unplaced.get("W", 7)),
          "B": int(raw_unplaced.get("B", 7)),
      }
    else:
      self.unplaced = {"W": 7, "B": 7}

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

    self.selected_point = None

  def check_win(self, player):
    for line in LINES_OF_THREE:
      if all(self.board[p] == player for p in line):
        self.winning_line = line
        return True
    return False

  def register_position(self):
    """Compta les repeticions de posició i declara taules si cal."""
    if not self.track_draws or self.winner:
      return
    key = (
        tuple(self.board[p] for p in POINTS_CONFIG),
        self.turn,
        self.unplaced["W"],
        self.unplaced["B"],
    )
    self.history[key] = self.history.get(key, 0) + 1
    if self.history[key] >= REPETITIONS_FOR_DRAW:
      self.draw = True

  def handle_click(self, point, my_role):
    if self.winner or self.draw or self.turn != my_role:
      return False

    opponent = "B" if self.turn == "W" else "W"
    moved = False

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

    # FASE 2: MOVIMENT DE FITXES (quan s'acaben les fitxes, a qualsevol lloc)
    else:
      if self.selected_point is None:
        if self.board[point] == self.turn:
          self.selected_point = point
      else:
        if point == self.selected_point:
          self.selected_point = None
        elif self.board[point] == self.turn:
          self.selected_point = point
        elif can_move_to(self.selected_point, point, self.board):
          self.board[point] = self.turn
          self.board[self.selected_point] = None
          self.selected_point = None
          if self.check_win(self.turn):
            self.winner = self.turn
          else:
            self.turn = opponent
          moved = True

    if moved:
      self.move_count += 1
      self.register_position()

    return moved


# ---------------------------------------------------------------
# BOT (minimax + alfa-beta + aprofundiment iteratiu)
# ---------------------------------------------------------------

IDX = {p: i for i, p in enumerate(POINTS_CONFIG)}
LINES_IDX = [tuple(IDX[p] for p in l) for l in LINES_OF_THREE]
LINES_OF_POINT = [[l for l in LINES_IDX if i in l] for i in range(24)]
ADJ_IDX = [[IDX[q] for q in ADJACENCY[p]] for p in POINTS_CONFIG]

WIN = 10000
INF = 10 ** 9


class Timeout(Exception):
  pass


class Bot:
  """1 = blanques, 2 = negres.

  think: segons màxims de reflexió. max_depth: profunditat màxima.
  blunder: probabilitat de fer una jugada a l'atzar (per als nivells fàcils).
  """

  def __init__(self, think=0.8, max_depth=12, blunder=0.0):
    self.think = think
    self.max_depth = max_depth
    self.blunder = blunder
    self.b = [0] * 24
    self.unp = {1: 7, 2: 7}
    self.deadline = 0
    self.nodes = 0

  # ---------- regles ----------
  def reachable(self, pl, e, line):
    if self.unp[pl] > 0 or FLY_WHEN_NO_PIECES_LEFT:
      return True
    return any(self.b[n] == pl and n not in line for n in ADJ_IDX[e])

  def win_points(self, pl):
    """Punts buits on 'pl' completaria una línia el proper torn."""
    pts = set()
    b = self.b
    for line in LINES_IDX:
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
        if FLY_WHEN_NO_PIECES_LEFT:
          res.extend((s, d) for d in empt)
        else:
          res.extend((s, d) for d in ADJ_IDX[s]
                     if b[d] == 0 and (only is None or d == only))
    return res

  def apply(self, pl, m):
    s, d = m
    if s is None:
      self.unp[pl] -= 1
    else:
      self.b[s] = 0
    self.b[d] = pl
    return any(all(self.b[i] == pl for i in l) for l in LINES_OF_POINT[d])

  def undo(self, pl, m):
    s, d = m
    self.b[d] = 0
    if s is None:
      self.unp[pl] += 1
    else:
      self.b[s] = pl

  # ---------- heurística ----------
  def order(self, pl, m):
    s_, d = m
    sc = 0
    for l in LINES_OF_POINT[d]:
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
    for l in LINES_IDX:
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

    best = mv[0]
    snap = (self.b[:], dict(self.unp))
    self.deadline = time.time() + self.think
    self.nodes = 0
    for depth in range(1, self.max_depth + 1):
      try:
        cur, cur_sc, alpha = None, -INF, -INF
        for m in mv:
          self.apply(pl, m)
          sc = -self.nega(opp, depth - 1, -INF, -alpha, 1)
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


# nom, descripció, paràmetres del bot
DIFFICULTIES = {
    "easy": ("FÀCIL", "Es despista sovint", dict(think=0.05, max_depth=1, blunder=0.4)),
    "medium": ("MITJÀ", "Veu unes quantes jugades", dict(think=0.2, max_depth=3, blunder=0.1)),
    "hard": ("DIFÍCIL", "Molt difícil de guanyar", dict(think=0.5 if HAS_JS else 0.8, max_depth=12)),
}


# ---------------------------------------------------------------
# MENÚS
# ---------------------------------------------------------------


def get_buttons(n):
  w, h = 460, 80
  x = WIDTH // 2 - w // 2
  return [pygame.Rect(x, 240 + i * 110, w, h) for i in range(n)]


def draw_choice_menu(title, subtitle, options, mouse_pos, hint):
  """options: llista de (clau, text, descripció, activat)."""
  SCREEN.fill(BG_COLOR)

  t = BIG_FONT.render(title, True, TEXT_COLOR)
  SCREEN.blit(t, (WIDTH // 2 - t.get_width() // 2, 120))

  sub = FONT.render(subtitle, True, (120, 100, 80))
  SCREEN.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 190))

  for rect, (key, label, desc, enabled) in zip(get_buttons(len(options)), options):
    hover = enabled and rect.collidepoint(mouse_pos)

    fill = (
        (255, 240, 205) if hover else (250, 232, 195)
    ) if enabled else (215, 200, 175)

    pygame.draw.rect(SCREEN, fill, rect, border_radius=14)
    pygame.draw.rect(
        SCREEN,
        HIGHLIGHT_COLOR if hover else LINE_COLOR,
        rect,
        5 if hover else 3,
        border_radius=14,
    )

    color = TEXT_COLOR if enabled else (140, 130, 115)

    t1 = TITLE_FONT.render(label, True, color)
    SCREEN.blit(t1, (rect.centerx - t1.get_width() // 2, rect.y + 10))

    t2 = FONT.render(desc, True, color)
    SCREEN.blit(t2, (rect.centerx - t2.get_width() // 2, rect.y + 48))

  h = FONT.render(hint, True, (120, 100, 80))
  SCREEN.blit(h, (WIDTH // 2 - h.get_width() // 2, HEIGHT - 60))


def main_menu_options():
  return [
      ("local", "1 - JUGAR EN LOCAL", "Dos jugadors a la mateixa pantalla", True),
      ("bot", "2 - CONTRA L'ORDINADOR", "Tu portes les blanques", True),
      (
          "online",
          "3 - JUGAR ONLINE",
          "Cada jugador des del seu dispositiu"
          if HAS_JS
          else "Només disponible al navegador",
          HAS_JS,
      ),
  ]


def difficulty_options():
  return [
      (k, f"{i + 1} - {v[0]}", v[1], True)
      for i, (k, v) in enumerate(DIFFICULTIES.items())
  ]


# ---------------------------------------------------------------
# DIBUIX DEL TAULER
# ---------------------------------------------------------------


def draw_piece(owner, pos):
  if owner == "W":
    pygame.draw.circle(SCREEN, WHITE_PIECE, pos, 18)
    pygame.draw.circle(SCREEN, WHITE_BORDER, pos, 18, 2)
  elif owner == "B":
    pygame.draw.circle(SCREEN, BLACK_PIECE, pos, 18)
    pygame.draw.circle(SCREEN, BLACK_BORDER, pos, 18, 2)


def draw_board(game, my_role, mode, difficulty=None):
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("Tres en ratlla", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))

  if mode == "local":
    role_surface = FONT.render("Mode local", True, (0, 100, 200))
  elif mode == "bot":
    name = DIFFICULTIES[difficulty][0].capitalize()
    role_surface = FONT.render(
        f"Tu: BLANQUES - Bot: NEGRES ({name})", True, (0, 100, 200)
    )
  else:
    role_str = "BLANQUES" if my_role == "W" else "NEGRES"
    role_surface = FONT.render(f"Ets les: {role_str}", True, (0, 100, 200))
  SCREEN.blit(role_surface, (20, 60))

  indicator_x = WIDTH - 45
  indicator_y = 70
  radius = 16

  turn_label = FONT.render("Torn:", True, TEXT_COLOR)
  SCREEN.blit(
      turn_label,
      (indicator_x - radius - turn_label.get_width() - 8, indicator_y - 10),
  )

  if game.turn == "W":
    pygame.draw.circle(SCREEN, WHITE_PIECE, (indicator_x, indicator_y), radius)
    pygame.draw.circle(
        SCREEN, WHITE_BORDER, (indicator_x, indicator_y), radius, 2
    )
  else:
    pygame.draw.circle(SCREEN, BLACK_PIECE, (indicator_x, indicator_y), radius)
    pygame.draw.circle(
        SCREEN, BLACK_BORDER, (indicator_x, indicator_y), radius, 2
    )

  # fitxes que queden per col·locar de cada jugador
  counts = FONT.render(
      f"Per col·locar:  Blanques {game.unplaced['W']}   Negres {game.unplaced['B']}",
      True,
      (120, 100, 80),
  )
  SCREEN.blit(counts, (WIDTH // 2 - counts.get_width() // 2, 92))

  for layer in range(3):
    margin = 50 + layer * 70
    size = BOARD_SIZE - 2 * margin
    rect = (OFFSET_X + margin, OFFSET_Y + margin, size, size)
    pygame.draw.rect(SCREEN, LINE_COLOR, rect, 4)

  mid_lines = [
      ((0, 1, 0), (2, 1, 0)),
      ((0, 1, 2), (2, 1, 2)),
      ((0, 0, 1), (2, 0, 1)),
      ((0, 2, 1), (2, 2, 1)),
  ]
  for p1, p2 in mid_lines:
    pygame.draw.line(
        SCREEN, LINE_COLOR, POINT_POSITIONS[p1], POINT_POSITIONS[p2], 4
    )

  if game.winning_line and len(game.winning_line) == 3:
    p1 = POINT_POSITIONS.get(game.winning_line[0])
    p3 = POINT_POSITIONS.get(game.winning_line[2])
    if p1 and p3:
      pygame.draw.line(SCREEN, WIN_LINE_COLOR, p1, p3, 10)

  # punts on es pot moure la fitxa seleccionada (tots els buits si pot volar)
  hints = []
  if game.selected_point is not None and not game.winner and not game.draw:
    hints = [
        p
        for p in POINTS_CONFIG
        if can_move_to(game.selected_point, p, game.board)
    ]

  for point, pos in POINT_POSITIONS.items():
    owner = game.board.get(point)
    pygame.draw.circle(SCREEN, LINE_COLOR, pos, 6)

    if point in hints:
      pygame.draw.circle(SCREEN, HINT_COLOR, pos, 11)
      pygame.draw.circle(SCREEN, WHITE_PIECE, pos, 11, 2)

    if point == game.selected_point:
      pygame.draw.circle(SCREEN, HIGHLIGHT_COLOR, pos, 22, 4)

    draw_piece(owner, pos)

  turn_str = "BLANQUES" if game.turn == "W" else "NEGRES"
  unplaced_count = game.unplaced.get(game.turn, 0)

  if mode == "bot" and game.turn == "B" and not game.winner and not game.draw:
    status_text = "L'ordinador està pensant..."
  elif game.winner:
    if mode == "bot":
      status_text = (
          "Has guanyat!!" if game.winner == "W" else "Ha guanyat l'ordinador"
      )
    else:
      status_text = f"¡¡GUANYEN LES {'BLANQUES' if game.winner == 'W' else 'NEGRES'}!!"
  elif game.draw:
    status_text = "TAULES (posició repetida)"
  elif unplaced_count > 0:
    status_text = (
        f"Col·locació - Torn: {turn_str} (Restants: {unplaced_count})"
    )
  elif FLY_WHEN_NO_PIECES_LEFT:
    status_text = f"Moviment lliure - Torn: {turn_str} (mou una fitxa a qualsevol lloc buit)"
  else:
    status_text = f"Moviment - Torn: {turn_str} (Selecciona i mou a un espai adjacent)"

  info_surface = FONT.render(status_text, True, TEXT_COLOR)
  SCREEN.blit(
      info_surface, (WIDTH // 2 - info_surface.get_width() // 2, HEIGHT - 45)
  )

  restart_text = FONT.render(
      "R = reiniciar la partida    M = menú", True, (120, 100, 80)
  )
  SCREEN.blit(
      restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT - 22)
  )


def point_at(mouse_pos):
  mx, my = mouse_pos
  for point, pos in POINT_POSITIONS.items():
    if math.hypot(mx - pos[0], my - pos[1]) <= 20:
      return point
  return None


async def main():
  clock = pygame.time.Clock()

  game = TicTacToeOnline()

  mode = "menu"          # "menu", "diff", "local", "bot" o "online"
  my_role = "W"
  difficulty = "hard"
  bot = Bot(**DIFFICULTIES[difficulty][2])
  bot_due = None

  running = True

  while running:
    clock.tick(30)

    # ----------------------------- MENÚ PRINCIPAL -----------------------------
    if mode == "menu":

      opts = main_menu_options()
      draw_choice_menu(
          "Tres en ratlla",
          "Tria com vols jugar",
          opts,
          pygame.mouse.get_pos(),
          "Clica una opció o prem 1 / 2 / 3",
      )

      choice = None

      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False

        elif event.type == pygame.KEYDOWN:
          if event.key in (pygame.K_1, pygame.K_KP1, pygame.K_l):
            choice = "local"
          elif event.key in (pygame.K_2, pygame.K_KP2, pygame.K_b):
            choice = "bot"
          elif event.key in (pygame.K_3, pygame.K_KP3, pygame.K_o):
            choice = "online"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
          for rect, o in zip(get_buttons(len(opts)), opts):
            if rect.collidepoint(event.pos):
              choice = o[0]

      if choice == "local":
        game = TicTacToeOnline(track_draws=True)
        mode = "local"

      elif choice == "bot":
        mode = "diff"

      elif choice == "online" and HAS_JS:
        start_online_engine()
        game = TicTacToeOnline()
        my_role = detect_online_role()
        mode = "online"

    # ----------------------------- DIFICULTAT -----------------------------
    elif mode == "diff":

      opts = difficulty_options()
      draw_choice_menu(
          "Dificultat",
          "Tu portes les blanques i comences",
          opts,
          pygame.mouse.get_pos(),
          "Clica una opció o prem 1 / 2 / 3   -   M = enrere",
      )

      picked = None
      keys = (
          (pygame.K_1, pygame.K_KP1),
          (pygame.K_2, pygame.K_KP2),
          (pygame.K_3, pygame.K_KP3),
      )

      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False

        elif event.type == pygame.KEYDOWN:
          if event.key in (pygame.K_m, pygame.K_ESCAPE):
            mode = "menu"
          else:
            for o, ks in zip(opts, keys):
              if event.key in ks:
                picked = o[0]

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
          for rect, o in zip(get_buttons(len(opts)), opts):
            if rect.collidepoint(event.pos):
              picked = o[0]

      if picked:
        difficulty = picked
        bot = Bot(**DIFFICULTIES[difficulty][2])
        game = TicTacToeOnline(track_draws=True)
        bot_due = None
        mode = "bot"

    # ------------------------ PARTIDA (local/bot/online) ------------------------
    else:

      if mode == "online":
        remote_state = check_firebase_state()
        if remote_state:
          game.from_dict(remote_state)

      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
          point = point_at(event.pos)

          if point is not None:

            if mode == "local":
              # a la mateixa pantalla juga sempre qui té el torn
              game.handle_click(point, game.turn)

            elif mode == "bot":
              if game.turn == "W":
                game.handle_click(point, "W")

            elif game.handle_click(point, my_role):
              push_firebase_state(game.to_dict())

        elif event.type == pygame.KEYDOWN:

          if event.key == pygame.K_r:
            if mode in ("local", "bot"):
              game = TicTacToeOnline(track_draws=True)
              bot_due = None
            else:
              new_count = game.move_count + 1
              game = TicTacToeOnline()
              game.move_count = new_count
              push_firebase_state(game.to_dict())

          elif event.key == pygame.K_m:
            game = TicTacToeOnline()
            bot_due = None
            mode = "menu"

      if mode != "menu":
        draw_board(game, my_role, mode, difficulty)

    pygame.display.flip()

    # Torn del bot: després del flip, perquè el missatge "pensant..."
    # ja s'hagi dibuixat abans que la cerca bloquegi un moment.
    if mode == "bot" and game.turn == "B" and not game.winner and not game.draw:
      now = pygame.time.get_ticks()
      if bot_due is None:
        bot_due = now + 300
      elif now >= bot_due:
        bot.play(game, "B")
        bot_due = None

    await asyncio.sleep(0)

  pygame.quit()
  sys.exit()


if __name__ == "__main__":
  asyncio.run(main())
