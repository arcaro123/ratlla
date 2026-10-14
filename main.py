import asyncio
import json
import math
import sys

import pygame

# "js" només existeix al navegador (pygbag). A l'ordinador no, i el mode
# local funciona igualment.
try:
  import js
  HAS_JS = True
except ImportError:
  js = None
  HAS_JS = False

# Inicialització de Pygame
pygame.init()
pygame.font.init()

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

  def __init__(self):
    self.board = {p: None for p in POINTS_CONFIG}
    self.turn = "W"
    self.unplaced = {"W": 7, "B": 7}
    self.selected_point = None
    self.winner = None
    self.winning_line = None
    self.move_count = 0  # Comptador de versió per evitar race conditions

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

  def handle_click(self, point, my_role):
    if self.winner or self.turn != my_role:
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
        elif self.board[point] is None:
          if point in ADJACENCY[self.selected_point]:
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

    return moved


# ---------------------------------------------------------------
# MENÚ: LOCAL (mateixa pantalla) o ONLINE
# ---------------------------------------------------------------


def get_menu_buttons():
  w, h = 460, 80
  x = WIDTH // 2 - w // 2
  return {
      "local": pygame.Rect(x, 270, w, h),
      "online": pygame.Rect(x, 390, w, h),
  }


def draw_menu(mouse_pos):
  SCREEN.fill(BG_COLOR)

  title = BIG_FONT.render("Tres en ratlla", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))

  sub = FONT.render("Tria com vols jugar", True, (120, 100, 80))
  SCREEN.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 190))

  buttons = get_menu_buttons()

  options = (
      ("local", "1 - JUGAR EN LOCAL", "Dos jugadors a la mateixa pantalla", True),
      (
          "online",
          "2 - JUGAR ONLINE",
          "Cada jugador des del seu dispositiu"
          if HAS_JS
          else "Només disponible al navegador",
          HAS_JS,
      ),
  )

  for key, label, desc, enabled in options:
    rect = buttons[key]
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

  hint = FONT.render(
      "Clica una opció o prem 1 / 2", True, (120, 100, 80)
  )
  SCREEN.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 60))


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


def draw_board(game, my_role, mode):
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("Tres en ratlla", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 15))

  if mode == "local":
    role_surface = FONT.render("Mode local", True, (0, 100, 200))
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

  # punts on es pot moure la fitxa seleccionada
  hints = []
  if game.selected_point is not None and not game.winner:
    hints = [
        p for p in ADJACENCY[game.selected_point] if game.board[p] is None
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

  if game.winner:
    status_text = f"¡¡GUANYEN LES {'BLANQUES' if game.winner == 'W' else 'NEGRES'}!!"
  elif unplaced_count > 0:
    status_text = (
        f"Col·locació - Torn: {turn_str} (Restants: {unplaced_count})"
    )
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

  mode = "menu"          # "menu", "local" o "online"
  my_role = "W"

  running = True

  while running:
    clock.tick(30)

    # ----------------------------- MENÚ -----------------------------
    if mode == "menu":

      draw_menu(pygame.mouse.get_pos())

      choice = None

      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          running = False

        elif event.type == pygame.KEYDOWN:
          if event.key in (pygame.K_1, pygame.K_KP1, pygame.K_l):
            choice = "local"
          elif event.key in (pygame.K_2, pygame.K_KP2, pygame.K_o):
            choice = "online"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
          for key, rect in get_menu_buttons().items():
            if rect.collidepoint(event.pos):
              choice = key

      if choice == "local":
        game = TicTacToeOnline()
        mode = "local"

      elif choice == "online" and HAS_JS:
        start_online_engine()
        game = TicTacToeOnline()
        my_role = detect_online_role()
        mode = "online"

    # ------------------------ PARTIDA (local/online) ------------------------
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

            elif game.handle_click(point, my_role):
              push_firebase_state(game.to_dict())

        elif event.type == pygame.KEYDOWN:

          if event.key == pygame.K_r:
            if mode == "local":
              game = TicTacToeOnline()
            else:
              new_count = game.move_count + 1
              game = TicTacToeOnline()
              game.move_count = new_count
              push_firebase_state(game.to_dict())

          elif event.key == pygame.K_m:
            game = TicTacToeOnline()
            mode = "menu"

      if mode != "menu":
        draw_board(game, my_role, mode)

    pygame.display.flip()
    await asyncio.sleep(0)

  pygame.quit()
  sys.exit()


if __name__ == "__main__":
  asyncio.run(main())
