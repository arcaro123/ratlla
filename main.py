import asyncio
import json
import math
import sys
import pygame
import websockets

# Inicialització de Pygame
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 700, 750
BOARD_SIZE = 550
OFFSET_X = (WIDTH - BOARD_SIZE) // 2
OFFSET_Y = 100

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tres en ratlla Online")

# Configuració de servidors (Exemple amb un servidor WebSocket)
SERVER_URL = "wss://el-teu-servidor.onrender.com"  # O la URL del teu servidor en línia

# [Mantenim colors, POINTS_CONFIG, POINT_POSITIONS, ADJACENCY, LINES_OF_THREE iguals]
# ...

class NetworkClient:
    def __init__(self):
        self.websocket = None
        self.player_color = None  # 'W' o 'B'
        self.connected = False

    async def connect(self):
        try:
            self.websocket = await websockets.connect(SERVER_URL)
            self.connected = True
            # Rebre el color assignat (Jugador 1 = 'W', Jugador 2 = 'B')
            init_data = await self.websocket.recv()
            msg = json.loads(init_data)
            self.player_color = msg.get("color")
        except Exception as e:
            print(f"Error de connexió: {e}")

    async def send_move(self, point_from, point_to):
        if self.connected and self.websocket:
            data = json.dumps({"type": "move", "from": point_from, "to": point_to})
            await self.websocket.send(data)

async def main():
    clock = pygame.time.Clock()
    game = TicTacToeMolino()
    network = NetworkClient()
    
    # Intentar connectar al servidor en línia
    await network.connect()

    running = True
    while running:
        clock.tick(30)

        # Escolta de missatges de l'altre jugador de manera asíncrona
        if network.connected:
            try:
                # Comprovar si hi ha moviments de l'altre jugador sense bloquejar
                message = await asyncio.wait_for(network.websocket.recv(), timeout=0.001)
                data = json.loads(message)
                if data.get("type") == "move":
                    # Aplicar el moviment de l'altre jugador al tauler local
                    game.apply_remote_move(data["from"], data["to"])
            except asyncio.TimeoutError:
                pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Només permetre clicar si és el teu torn i el teu color
                if game.turn == network.player_color:
                    mx, my = event.pos
                    for point, pos in POINT_POSITIONS.items():
                        dist = math.hypot(mx - pos[0], my - pos[1])
                        if dist <= 20:
                            prev_selected = game.selected_point
                            game.handle_click(point)
                            # Si s'ha fet un moviment, enviar-lo
                            if game.last_move:
                                await network.send_move(game.last_move['from'], game.last_move['to'])
                            break

        draw_board(game)
        
        # Mostrar el teu color assignat a la pantalla
        if network.player_color:
            role_text = FONT.render(f"Ets les: {'BLANQUES' if network.player_color == 'W' else 'NEGRES'}", True, (0, 100, 200))
            SCREEN.blit(role_text, (20, 35))

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())
