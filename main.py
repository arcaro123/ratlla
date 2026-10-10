import math
import sys
import pygame

# Inicialització de Pygame
pygame.init()
pygame.font.init()

# Configuració de la pantalla
WIDTH, HEIGHT = 700, 750
BOARD_SIZE = 550
OFFSET_X = (WIDTH - BOARD_SIZE) // 2
OFFSET_Y = 100

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tres en ratlla")

# Colors
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

# Coordenades lògiques dels 24 punts: (capa 0-2, fila 0-2, col 0-2)
POINTS_CONFIG = [
    # Capa exterior (0)
    (0, 0, 0), (0, 0, 1), (0, 0, 2),
    (0, 1, 2), (0, 2, 2), (0, 2, 1),
    (0, 2, 0), (0, 1, 0),
    # Capa mitjana (1)
    (1, 0, 0), (1, 0, 1), (1, 0, 2),
    (1, 1, 2), (1, 2, 2), (1, 2, 1),
    (1, 2, 0), (1, 1, 0),
    # Capa interior (2)
    (2, 0, 0), (2, 0, 1), (2, 0, 2),
    (2, 1, 2), (2, 2, 2), (2, 2, 1),
    (2, 2, 0), (2, 1, 0)
]


def get_screen_coords(point):
    """Converteix coordenades lògiques a píxels a la pantalla."""
    layer, r, c = point
    margin = 50 + layer * 70
    size = BOARD_SIZE - 2 * margin
    x = OFFSET_X + margin + c * (size // 2)
    y = OFFSET_Y + margin + r * (size // 2)
    return int(x), int(y)


POINT_POSITIONS = {p: get_screen_coords(p) for p in POINTS_CONFIG}

# Adjacències per moure fitxes
ADJACENCY = {
    # Capa exterior
    (0, 0, 0): [(0, 0, 1), (0, 1, 0)],
    (0, 0, 1): [(0, 0, 0), (0, 0, 2), (1, 0, 1)],
    (0, 0, 2): [(0, 0, 1), (0, 1, 2)],
    (0, 1, 2): [(0, 0, 2), (0, 2, 2), (1, 1, 2)],
    (0, 2, 2): [(0, 1, 2), (0, 2, 1)],
    (0, 2, 1): [(0, 2, 2), (0, 2, 0), (1, 2, 1)],
    (0, 2, 0): [(0, 2, 1), (0, 1, 0)],
    (0, 1, 0): [(0, 2, 0), (0, 0, 0), (1, 1, 0)],

    # Capa mitjana
    (1, 0, 0): [(1, 0, 1), (1, 1, 0)],
    (1, 0, 1): [(1, 0, 0), (1, 0, 2), (0, 0, 1), (2, 0, 1)],
    (1, 0, 2): [(1, 0, 1), (1, 1, 2)],
    (1, 1, 2): [(1, 0, 2), (1, 2, 2), (0, 1, 2), (2, 1, 2)],
    (1, 2, 2): [(1, 1, 2), (1, 2, 1)],
    (1, 2, 1): [(1, 2, 2), (1, 2, 0), (0, 2, 1), (2, 2, 1)],
    (1, 2, 0): [(1, 2, 1), (1, 1, 0)],
    (1, 1, 0): [(1, 2, 0), (1, 0, 0), (0, 1, 0), (2, 1, 0)],

    # Capa interior
    (2, 0, 0): [(2, 0, 1), (2, 1, 0)],
    (2, 0, 1): [(2, 0, 0), (2, 0, 2), (1, 0, 1)],
    (2, 0, 2): [(2, 0, 1), (2, 1, 2)],
    (2, 1, 2): [(2, 0, 2), (2, 2, 2), (1, 1, 2)],
    (2, 2, 2): [(2, 1, 2), (2, 2, 1)],
    (2, 2, 1): [(2, 2, 2), (2, 2, 0), (1, 2, 1)],
    (2, 2, 0): [(2, 2, 1), (2, 1, 0)],
    (2, 1, 0): [(2, 2, 0), (2, 0, 0), (1, 1, 0)],
}

# Totes les línies possibles de 3 en ratlla
LINES_OF_THREE = [
    # Horitzontals
    [(0, 0, 0), (0, 0, 1), (0, 0, 2)], [(0, 2, 0), (0, 2, 1), (0, 2, 2)],
    [(1, 0, 0), (1, 0, 1), (1, 0, 2)], [(1, 2, 0), (1, 2, 1), (1, 2, 2)],
    [(2, 0, 0), (2, 0, 1), (2, 0, 2)], [(2, 2, 0), (2, 2, 1), (2, 2, 2)],
    [(0, 1, 0), (1, 1, 0), (2, 1, 0)], [(2, 1, 2), (1, 1, 2), (0, 1, 2)],
    # Verticals
    [(0, 0, 0), (0, 1, 0), (0, 2, 0)], [(0, 0, 2), (0, 1, 2), (0, 2, 2)],
    [(1, 0, 0), (1, 1, 0), (1, 2, 0)], [(1, 0, 2), (1, 1, 2), (1, 2, 2)],
    [(2, 0, 0), (2, 1, 0), (2, 2, 0)], [(2, 0, 2), (2, 1, 2), (2, 2, 2)],
    [(0, 0, 1), (1, 0, 1), (2, 0, 1)], [(2, 2, 1), (1, 2, 1), (0, 2, 1)]
]


class TicTacToeMolino:
    def __init__(self):
        self.board = {p: None for p in POINTS_CONFIG}  # None, 'W' o 'B'
        self.turn = 'W'  # 'W' (Blanques) o 'B' (Negres)
        self.unplaced = {'W': 7, 'B': 7}  # 7 fitxes per jugador
        self.selected_point = None
        self.winner = None
        self.winning_line = None

    def check_win(self, player):
        """Comprova si el jugador té alguna línia de 3 completa."""
        for line in LINES_OF_THREE:
            if all(self.board[p] == player for p in line):
                self.winning_line = line
                return True
        return False

    def handle_click(self, point):
        if self.winner:
            return

        opponent = 'B' if self.turn == 'W' else 'W'

        # FASE 1: COL·LOCACIÓ DE FITXES
        if self.unplaced[self.turn] > 0:
            if self.board[point] is None:
                self.board[point] = self.turn
                self.unplaced[self.turn] -= 1

                if self.check_win(self.turn):
                    self.winner = self.turn
                else:
                    self.turn = opponent
            return

        # FASE 2: MOVIMENT DE FITXES
        if self.selected_point is None:
            if self.board[point] == self.turn:
                self.selected_point = point
        else:
            if point == self.selected_point:
                self.selected_point = None  # Deseleccionar
            elif self.board[point] == self.turn:
                self.selected_point = point  # Canvi directe de selecció
            elif self.board[point] is None:
                # Moure només si el punt destí és adjacent
                if point in ADJACENCY[self.selected_point]:
                    self.board[point] = self.turn
                    self.board[self.selected_point] = None
                    self.selected_point = None

                    if self.check_win(self.turn):
                        self.winner = self.turn
                    else:
                        self.turn = opponent


def draw_board(game):
    SCREEN.fill(BG_COLOR)

    # Títol a dalt (només "Tres en ratlla")
    title = TITLE_FONT.render("Tres en ratlla", True, TEXT_COLOR)
    SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 25))

    # Indicador de torn a la cantonada superior dreta
    indicator_x = WIDTH - 45
    indicator_y = 35
    radius = 18

    turn_label = FONT.render("Torn:", True, TEXT_COLOR)
    SCREEN.blit(turn_label, (indicator_x - radius - turn_label.get_width() - 8, indicator_y - 12))

    if game.turn == 'W':
        pygame.draw.circle(SCREEN, WHITE_PIECE, (indicator_x, indicator_y), radius)
        pygame.draw.circle(SCREEN, WHITE_BORDER, (indicator_x, indicator_y), radius, 2)
    else:
        pygame.draw.circle(SCREEN, BLACK_PIECE, (indicator_x, indicator_y), radius)
        pygame.draw.circle(SCREEN, BLACK_BORDER, (indicator_x, indicator_y), radius, 2)

    # Dibuixar quadrats concentrics
    for layer in range(3):
        margin = 50 + layer * 70
        size = BOARD_SIZE - 2 * margin
        rect = (OFFSET_X + margin, OFFSET_Y + margin, size, size)
        pygame.draw.rect(SCREEN, LINE_COLOR, rect, 4)

    # Dibuixar línies intermèdies
    mid_lines = [
        ((0, 1, 0), (2, 1, 0)),
        ((0, 1, 2), (2, 1, 2)),
        ((0, 0, 1), (2, 0, 1)),
        ((0, 2, 1), (2, 2, 1))
    ]
    for p1, p2 in mid_lines:
        pygame.draw.line(SCREEN, LINE_COLOR, POINT_POSITIONS[p1], POINT_POSITIONS[p2], 4)

    # Ressaltar la línia guanyadora en verd
    if game.winning_line:
        p1 = POINT_POSITIONS[game.winning_line[0]]
        p3 = POINT_POSITIONS[game.winning_line[2]]
        pygame.draw.line(SCREEN, WIN_LINE_COLOR, p1, p3, 10)

    # Dibuixar punts i fitxes
    for point, pos in POINT_POSITIONS.items():
        owner = game.board[point]

        # Punt base de la intersecció
        pygame.draw.circle(SCREEN, LINE_COLOR, pos, 6)

        # Ressaltar fitxa seleccionada per moure
        if point == game.selected_point:
            pygame.draw.circle(SCREEN, HIGHLIGHT_COLOR, pos, 22, 4)

        # Fitxes
        if owner == 'W':
            pygame.draw.circle(SCREEN, WHITE_PIECE, pos, 18)
            pygame.draw.circle(SCREEN, WHITE_BORDER, pos, 18, 2)
        elif owner == 'B':
            pygame.draw.circle(SCREEN, BLACK_PIECE, pos, 18)
            pygame.draw.circle(SCREEN, BLACK_BORDER, pos, 18, 2)

    # Text d'estat a la part inferior
    turn_str = "BLANQUES" if game.turn == 'W' else "NEGRES"

    if game.winner:
        status_text = f"¡¡GUANYEN LES {'BLANQUES' if game.winner == 'W' else 'NEGRES'}!!"
    elif game.unplaced[game.turn] > 0:
        status_text = f" Torn: {turn_str} (Restants: {game.unplaced[game.turn]})"
    else:
        status_text = f"Moviment - Torn: {turn_str} (Selecciona i mou a un espai adjacent)"

    info_surface = FONT.render(status_text, True, TEXT_COLOR)
    SCREEN.blit(info_surface, (WIDTH // 2 - info_surface.get_width() // 2, HEIGHT - 45))

    restart_text = FONT.render("L'espai per reiniciar", True, (120, 100, 80))
    SCREEN.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT - 22))


def main():
    clock = pygame.time.Clock()
    game = TicTacToeMolino()

    running = True
    while running:
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for point, pos in POINT_POSITIONS.items():
                    dist = math.hypot(mx - pos[0], my - pos[1])
                    if dist <= 20:
                        game.handle_click(point)
                        break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:  # Reiniciar amb la tecla 'R'
                    game = TicTacToeMolino()

        draw_board(game)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()