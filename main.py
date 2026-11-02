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
POINTS = {"easy": 10, "medium": 30, "hard": 100}

LEVELS = ("easy", "medium", "hard")
LEVEL_INFO = {
    "easy": ("FÀCIL", "Es despista sovint"),
    "medium": ("MITJÀ", "Veu unes quantes jugades"),
    "hard": ("DIFÍCIL", "Molt difícil de guanyar"),
}

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
# DESAT (localStorage al navegador, fitxer a l'ordinador)
# ---------------------------------------------------------------

SAVE_KEY = "jocs_de_taula_save_v1"
SAVE_FILE = os.path.join(os.path.expanduser("~"), ".jocs_de_taula.json")
GAMES = ("morris", "c4")


def default_save():
  return {
      "points": 0,
      "difficulty": "hard",
      "rules": {"pieces": 7, "fly": True, "diag": False},
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
  except Exception:
    pass
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
    },
    "c4": {
        "easy": dict(think=0.05, max_depth=2, blunder=0.35),
        "medium": dict(think=0.2, max_depth=4, blunder=0.08),
        "hard": dict(think=0.5 if HAS_JS else 0.8, max_depth=14),
    },
}


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
]
C4_KEYS = [
    (pygame.K_1, pygame.K_KP1), (pygame.K_2, pygame.K_KP2),
    (pygame.K_3, pygame.K_KP3), (pygame.K_4, pygame.K_KP4),
    (pygame.K_5, pygame.K_KP5), (pygame.K_6, pygame.K_KP6),
    (pygame.K_7, pygame.K_KP7),
]


def get_buttons(n):
  w, h = 460, 80
  x = WIDTH // 2 - w // 2
  step = 110 if n <= 3 else 100
  return [pygame.Rect(x, 235 + i * step, w, h) for i in range(n)]


def draw_choice_menu(title, subtitle, opts, mouse_pos, hint):
  """opts: llista de (clau, text, descripció, activat)."""
  SCREEN.fill(BG_COLOR)

  t = BIG_FONT.render(title, True, TEXT_COLOR)
  SCREEN.blit(t, (WIDTH // 2 - t.get_width() // 2, 110))

  sub = FONT.render(subtitle, True, SOFT_TEXT)
  SCREEN.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 180))

  for i, (rect, (key, label, desc, enabled)) in enumerate(
      zip(get_buttons(len(opts)), opts)):
    hover = enabled and rect.collidepoint(mouse_pos)
    fill = (
        (255, 240, 205) if hover else (250, 232, 195)
    ) if enabled else (215, 200, 175)

    pygame.draw.rect(SCREEN, fill, rect, border_radius=14)
    pygame.draw.rect(
        SCREEN, HIGHLIGHT_COLOR if hover else LINE_COLOR, rect,
        5 if hover else 3, border_radius=14)

    color = TEXT_COLOR if enabled else (140, 130, 115)
    t1 = TITLE_FONT.render(f"{i + 1} - {label}", True, color)
    SCREEN.blit(t1, (rect.centerx - t1.get_width() // 2, rect.y + 10))
    t2 = FONT.render(desc, True, color)
    SCREEN.blit(t2, (rect.centerx - t2.get_width() // 2, rect.y + 48))

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

FIRST = {"morris": "W", "c4": 1}
SIDE_NAMES = {
    "morris": ("LES BLANQUES", "LES NEGRES"),
    "c4": ("ELS VERMELLS", "ELS GROCS"),
}
GAME_TITLES = {"morris": "Tres en ratlla", "c4": "4 en ratlla"}


def side_label(kind, p):
  return SIDE_NAMES[kind][0 if p == FIRST[kind] else 1]


def record_text(app):
  if app.mode == "bot":
    w, l, d = SAVE["records"][app.kind][app.difficulty]
    return f"{LEVEL_INFO[app.difficulty][0].capitalize()}: {w}V  {l}D  {d}T"
  if app.mode == "local":
    a, b, c = SAVE["records"][app.kind]["local"]
    n1, n2 = ("Blanques", "Negres") if app.kind == "morris" else ("Vermells", "Grocs")
    return f"{n1} {a}  {n2} {b}  Taules {c}"
  return ""


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
    return base
  if g.draw:
    return "TAULES"
  if app.mode == "bot" and g.turn == app.bot_role:
    return "L'ordinador està pensant..."
  who = side_label(kind, g.turn)
  if kind == "c4":
    return f"Torn: {who}"
  left = g.unplaced.get(g.turn, 0)
  if left > 0:
    return f"Col·locació - Torn: {who} (Restants: {left})"
  if g.rules.fly:
    return f"Moviment lliure - Torn: {who} (a qualsevol lloc buit)"
  return f"Moviment - Torn: {who} (a un espai adjacent)"


def draw_button(rect, label, enabled=True, mouse=None):
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
  t = FONT.render(label, True, color)
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
  gap = 10
  w = (WIDTH - 2 * 30 - gap * (len(items) - 1)) // len(items)
  return [(pygame.Rect(30 + i * (w + gap), y, w, h), key, en)
          for i, (key, _label, en) in enumerate(items)], [i[1] for i in items]


def draw_footer(app):
  info = FONT.render(status_text(app), True, TEXT_COLOR)
  SCREEN.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT - 82))
  rects, labels = game_buttons(app)
  names = {"restart": "Reiniciar", "menu": "Menú", "undo": "Desfer", "hint": "Pista"}
  for (rect, key, en) in rects:
    draw_button(rect, names[key], en)


def back_button_rect():
  return pygame.Rect(15, 15, 120, 42)


# ---------------------------------------------------------------
# DIBUIX: TRES EN RATLLA
# ---------------------------------------------------------------


def draw_piece(owner, pos, r=18):
  pos = (int(pos[0]), int(pos[1]))
  if owner == "W":
    pygame.draw.circle(SCREEN, WHITE_PIECE, pos, r)
    pygame.draw.circle(SCREEN, WHITE_BORDER, pos, r, 2)
  elif owner == "B":
    pygame.draw.circle(SCREEN, BLACK_PIECE, pos, r)
    pygame.draw.circle(SCREEN, BLACK_BORDER, pos, r, 2)


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

  if g.turn == "W":
    draw_turn_indicator(WHITE_PIECE, WHITE_BORDER)
  else:
    draw_turn_indicator(BLACK_PIECE, BLACK_BORDER)

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
  fill, border = C4_COLORS[owner]
  pos = (int(pos[0]), int(pos[1]))
  pygame.draw.circle(SCREEN, fill, pos, r)
  pygame.draw.circle(SCREEN, border, pos, r, 3)
  pygame.draw.circle(SCREEN, border, pos, r - 10, 2)


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
  draw_turn_indicator(*C4_COLORS[g.turn])

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
# PANTALLA DE RESULTAT (victòria / derrota / taules)
# ---------------------------------------------------------------


def result_buttons():
  panel = pygame.Rect(WIDTH // 2 - 270, 230, 540, 280)
  again = pygame.Rect(panel.x + 30, panel.bottom - 70, 230, 48)
  menu = pygame.Rect(panel.right - 260, panel.bottom - 70, 230, 48)
  return panel, again, menu


def draw_result(app):
  res = app.result
  veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
  veil.fill((0, 0, 0, 120))
  SCREEN.blit(veil, (0, 0))

  panel, again, menu = result_buttons()
  pygame.draw.rect(SCREEN, (250, 232, 195), panel, border_radius=18)
  pygame.draw.rect(SCREEN, res["color"], panel, 6, border_radius=18)

  t = RES_FONT.render(res["title"], True, res["color"])
  SCREEN.blit(t, (panel.centerx - t.get_width() // 2, panel.y + 28))

  for i, line in enumerate(res["lines"][:4]):
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
    self.assisted = False
    self.result = None
    self.over_time = None
    self.anim = None
    self.anim_key = None

  # ---------- menús ----------
  def menu_def(self):
    s = self.state
    if s == "main":
      return ("Jocs de taula", f"Punts totals: {SAVE['points']}", [
          ("morris", "TRES EN RATLLA", "Tauler de tres quadrats", True),
          ("c4", "4 EN RATLLA", "Fitxes que cauen", True),
          ("settings", "REGLES", "Variants de Tres en ratlla", True),
      ], "Clica una opció o prem 1 / 2 / 3")
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
      opts = [(k, LEVEL_INFO[k][0], f"{LEVEL_INFO[k][1]} (+{POINTS[k]} punts)", True)
              for k in LEVELS]
      return ("Dificultat", "Com de fort vols el bot?", opts,
              "Clica una opció o prem 1 / 2 / 3   -   M = enrere")
    if s == "side":
      a, b = ("les blanques", "les negres") if self.kind == "morris" else ("els vermells", "els grocs")
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

  # ---------- inici / final de partida ----------
  def start_game(self):
    firsts = (FIRST[self.kind], 2 if self.kind == "c4" else "B")
    if self.kind == "morris":
      rules = Rules() if self.mode == "online" else self.rules
      self.game = Morris(rules, track=(self.mode != "online"))
    else:
      self.game = Connect4()

    self.me = self.bot_role = self.bot = None
    if self.mode == "bot":
      self.me = firsts[0] if self.human_first else firsts[1]
      self.bot_role = firsts[1] if self.human_first else firsts[0]
      params = BOT_PARAMS[self.kind][self.difficulty]
      self.bot = Bot(**params) if self.kind == "morris" else C4Bot(**params)
    elif self.mode == "online":
      start_online_engine()
      self.me = detect_online_role()
    self.reset_view()
    self.assisted = False
    self.state = "play"

  def reset_view(self):
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
        pts = max(1, base // 2) if self.assisted else base
        rec[0] += 1
        res["title"], res["color"] = "HAS GUANYAT!", COLOR_WIN
        if blocked:
          lines.append("L'ordinador s'ha quedat sense moviments")
        lines.append(f"+{pts} punts")
        if self.assisted:
          lines.append("(meitat de punts per haver usat ajudes)")
      elif draw:
        pts = max(1, base // 5)
        if self.assisted:
          pts = max(1, pts // 2)
        rec[2] += 1
        res["title"], res["color"] = "TAULES", COLOR_DRAW
        lines.append("Posició repetida o massa moviments" if kind == "morris" else "Tauler ple")
        lines.append(f"+{pts} punts")
      else:
        pts = 0
        rec[1] += 1
        res["title"], res["color"] = "HAS PERDUT...", COLOR_LOSE
        if blocked:
          lines.append("T'has quedat sense moviments")
        lines.append("Torna-ho a provar!")
      SAVE["points"] += pts
      lines.append(f"Total: {SAVE['points']} punts")

    elif mode == "local":
      rec = SAVE["records"][kind]["local"]
      if draw:
        rec[2] += 1
        res["title"] = "TAULES"
        lines.append("Posició repetida o massa moviments" if kind == "morris" else "Tauler ple")
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

    self.result = res
    write_save()

  # ---------- ajudes ----------
  def can_undo(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return False
    if self.mode == "local":
      return bool(g.stack)
    return any(s["turn"] == self.me for s in g.stack)

  def can_hint(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return False
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

  def do_undo(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
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
      self.assisted = True
      self.hint = None
      self.bot_due = None
      self.reset_anim()

  def do_hint(self):
    g = self.game
    if self.mode == "online" or g.winner or g.draw or self.result:
      return
    if self.mode == "bot" and g.turn != self.me:
      return
    if self.anim and self.anim.active():
      return
    if self.kind == "morris":
      self.hint = Bot(think=0.4, max_depth=12).choose(g, g.turn)
    else:
      self.hint = C4Bot(think=0.4, max_depth=14).choose(g, g.turn)
    self.assisted = True

  # ---------- entrada ----------
  def process(self, events):
    for ev in events:
      if ev.type == pygame.QUIT:
        self.running = False
        return
    if self.state != "play":
      self.process_menu(events)
    else:
      self.process_play(events)

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
        else:
          if 90 <= ev.pos[1] <= C4_Y0 + C4_ROWS * C4_CELL + 20:
            self.c4_click(c4_col_at(ev.pos[0]))

  # ---------- actualització ----------
  def sync_anim(self):
    g = self.game
    key = (g.move_count, g.last_move)
    if key == self.anim_key:
      return
    self.anim_key = key
    self.anim = None
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
      if self.kind == "morris":
        draw_morris(self)
      else:
        draw_c4(self)
      if self.result:
        draw_result(self)
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
