import asyncio
import json
import math
import sys
import js
import pygame

# Inicialització de Pygame
pygame.init()
pygame.font.init()

# CONFIGURACIÓ DE LA PANTALLA
WIDTH, HEIGHT = 700, 750
BOARD_SIZE = 550
OFFSET_X = (WIDTH - BOARD_SIZE) // 2
OFFSET_Y = 100

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tres en ratlla Online")

# LA TEVA URL DE FIREBASE
FIREBASE_URL = (
    "https://arnau-2-default-rtdb.europe-west1.firebasedatabase.app/game.json"
)

# Injectar funcions JavaScript de connexió netes i segures
js.eval("""
window.fb_get = async function(url) {
    try {
        let res = await fetch(url);
        return await res.text();
    } catch(e) {
        return null;
    }
};
window.fb_put = async function(url, jsonString) {
    try {
        await fetch(url, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: jsonString
        });
    } catch(e) {}
};
""")

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

FONT = pygame.font.SysFont("arial", 20, bold=True)
TITLE_FONT = pygame.font.SysFont("arial", 32, bold=True)

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
  parts = s.split("_")
  return (int(parts[0]), int(parts[1]), int(parts[2]))


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


async def firebase_get():
  try:
    res = await js.window.fb_get(FIREBASE_URL)
    if res and str(res) != "null":
      return json.loads(str(res))
  except Exception as e:
    print("Error llegint de Firebase:", e)
  return None


async def firebase_put(data):
  try:
    await js.window.fb_put(FIREBASE_URL, json.dumps(data))
  except Exception as e:
    print("Error escrivint a Firebase:", e)


class TicTacToeOnline:

  def __init__(self):
    self.board = {p: None for p in POINTS_CONFIG}
    self.turn = "W"
    self.unplaced = {"W": 7, "B": 7}
    self.selected_point = None
    self.winner = None
    self.winning_line = None

  def to_dict(self):
    return {
        "board": {point_to_str(k): v for k, v in self.board.items()},
        "turn": self.turn,
        "unplaced": self.unplaced,
        "winner": self.winner,
        "winning_line": (
            [point_to_str(p) for p in self.winning_line]
            if self.winning_line
            else None
        ),
    }

  def from_dict(self, data):
    if not data or not isinstance(data, dict):
      return
    if "board" in data and data["board"]:
      self.board = {str_to_point(k): v for k, v in data["board"].items()}
    self.turn = data.get("turn", "W")
    self.unplaced = data.get("unplaced", {"W": 7, "B": 7})
    self.winner = data.get("winner", None)
    w_line = data.get("winning_line", None)
    self.winning_line = [str_to_point(p) for p in w_line] if w_line else None

  def check_win(self, player):
    for line in LINES_OF_THREE:
      if all(self.board[p] == player for p in line):
        self.winning_line = line
        return True
    return False

  def handle_click(self, point, my_role):
    # Si ja hi ha guanyador o no és el teu torn, ignora el clic
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

    return moved


def draw_board(game, my_role):
  SCREEN.fill(BG_COLOR)

  title = TITLE_FONT.render("Tres en ratlla Online", True, TEXT_COLOR)
  SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 25))

  # Indicador del teu color
  role_str = "BLANQUES" if my_role == "W" else "NEGRES"
  role_surface = FONT.render(f"Ets les: {role_str}", True, (0, 100, 200))
  SCREEN.blit(role_surface, (20, 25))

  # Indicador de quin torn és
  indicator_x = WIDTH - 45
  indicator_y = 35
  radius = 18

  turn_label = FONT.render("Torn:", True, TEXT_COLOR)
  SCREEN.blit(
      turn_label,
      (indicator_x - radius - turn_label.get_width() - 8, indicator_y - 12),
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

  if game.winning_line:
    p1 = POINT_POSITIONS[game.winning_line[0]]
    p3 = POINT_POSITIONS[game.winning_line[2]]
    pygame.draw.line(SCREEN, WIN_LINE_COLOR, p1, p3, 10)

  for point, pos in POINT_POSITIONS.items():
    owner = game.board[point]
    pygame.draw.circle(SCREEN, LINE_COLOR, pos, 6)

    if point == game.selected_point:
      pygame.draw.circle(SCREEN, HIGHLIGHT_COLOR, pos, 22, 4)

    if owner == "W":
      pygame.draw.circle(SCREEN, WHITE_PIECE, pos, 18)
      pygame.draw.circle(SCREEN, WHITE_BORDER, pos, 18, 2)
    elif owner == "B":
      pygame.draw.circle(SCREEN, BLACK_PIECE, pos, 18)
      pygame.draw.circle(SCREEN, BLACK_BORDER, pos, 18, 2)

  turn_str = "BLANQUES" if game.turn == "W" else "NEGRES"

  if game.winner:
    status_text = f"¡¡GUANYEN LES {'BLANQUES' if game.winner == 'W' else 'NEGRES'}!!"
  elif game.unplaced[game.turn] > 0:
    status_text = (
        f"Col·locació - Torn: {turn_str} (Restants: {game.unplaced[game.turn]})"
    )
  else:
    status_text = f"Moviment - Torn: {turn_str} (Selecciona i mou a un espai adjacent)"

  info_surface = FONT.render(status_text, True, TEXT_COLOR)
  SCREEN.blit(
      info_surface, (WIDTH // 2 - info_surface.get_width() // 2, HEIGHT - 45)
  )

  restart_text = FONT.render(
      "Prem 'R' per reiniciar la partida", True, (120, 100, 80)
  )
  SCREEN.blit(
      restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT - 22)
  )


async def main():
  clock = pygame.time.Clock()
  game = TicTacToeOnline()

  # DETECCIÓ DE ROL PER LA URL
  try:
    href = str(js.window.location.href)
    my_role = "B" if "#black" in href else "W"
  except Exception:
    my_role = "W"

  # Carregar estat inicial de Firebase
  initial_state = await firebase_get()
  if initial_state:
    game.from_dict(initial_state)

  poll_counter = 0
  running = True

  while running:
    clock.tick(30)
    poll_counter += 1

    # Comprovar si hi ha canvis a Firebase cada ~0.5s
    if poll_counter % 15 == 0:
      remote_state = await firebase_get()
      if remote_state:
        game.from_dict(remote_state)

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

      elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        mx, my = event.pos
        for point, pos in POINT_POSITIONS.items():
          dist = math.hypot(mx - pos[0], my - pos[1])
          if dist <= 20:
            if game.handle_click(point, my_role):
              await firebase_put(game.to_dict())
            break

      elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_r:  # Prem 'R' per reiniciar el tauler
          game = TicTacToeOnline()
          await firebase_put(game.to_dict())

    draw_board(game, my_role)
    pygame.display.flip()
    await asyncio.sleep(0)

  pygame.quit()
  sys.exit()


if __name__ == "__main__":
  asyncio.run(main())
