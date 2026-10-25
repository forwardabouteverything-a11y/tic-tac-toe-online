import os
import json
import random
import string
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

app = FastAPI()

# --- УМНЫЕ ПУТИ ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_DIR = os.path.join(os.path.dirname(BASE_DIR), "client")

# --- ГЛОБАЛЬНЫЕ ДАННЫЕ ---
lobbies: dict[str, dict] = {}
win_conditions = [[0, 1, 2], [3, 4, 5], [6, 7, 8],
                  [0, 3, 6], [1, 4, 7], [2, 5, 8],
                  [0, 4, 8], [6, 4, 2]]

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def generate_lobby_id():
    while True:
        res = ''.join(random.choices(string.ascii_uppercase, k=5))
        if res not in lobbies:
            return res

def check_win(lobby_id, role):
    for a, b, c in win_conditions:
        board = lobbies[lobby_id]['board']
        if board[a] == role and board[b] == role and board[c] == role:
            return True
    return False

def check_draw(lobby_id):
    return '.' not in lobbies[lobby_id]['board']

def is_move_valid(cell_id, lobby_id):
    return lobbies[lobby_id]['board'][cell_id] == '.'

# --- HTTP ЭНДПОИНТЫ ---
@app.get("/")
async def get_index():
    return FileResponse(os.path.join(CLIENT_DIR, "index.html"))

@app.get("/style.css")
async def get_style():
    return FileResponse(os.path.join(CLIENT_DIR, "style.css"))

@app.get("/main.js")
async def get_js():
    return FileResponse(os.path.join(CLIENT_DIR, "main.js"))

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            action = data.get('action')

            # 1. СОЗДАНИЕ ЛОББИ
            if action == 'create_lobby':
                lobby_id = generate_lobby_id()
                lobbies[lobby_id] = {
                    'players': [websocket],
                    'board': ['.'] * 9,
                    'turn': 'X'
                }
                await websocket.send_text(json.dumps({
                    'action': 'lobby_created',
                    'lobby_id': lobby_id,
                    'role': 'X'
                }))

            # 2. ПОДКЛЮЧЕНИЕ К ЛОББИ
            elif action == 'join_lobby':
                lobby_id = data.get('lobby_id')
                if lobbies.get(lobby_id):
                    if len(lobbies[lobby_id]['players']) >= 2:
                        await websocket.send_text(json.dumps({'action': 'error', 'message': 'Лобби заполнено'}))
                    else:
                        lobbies[lobby_id]['players'].append(websocket)
                        await websocket.send_text(json.dumps({
                            'action': 'lobby_joined',
                            'lobby_id': lobby_id,
                            'role': 'O',
                            'board': lobbies[lobby_id]['board'],
                            'turn': lobbies[lobby_id]['turn']
                        }))
                        await lobbies[lobby_id]['players'][0].send_text(json.dumps({
                            'action': 'player_joined',
                            'lobby_id': lobby_id
                        }))
                else:
                    await websocket.send_text(json.dumps({'action': 'error', 'message': 'Лобби не найдено'}))

            # 3. ХОД
            elif action == 'move':
                lobby_id = data.get('lobby_id')
                role = data.get('role')
                try:
                    cell_id = int(data.get('cell_id'))
                except (TypeError, ValueError):
                    continue

                lobby = lobbies.get(lobby_id)
                if lobby and len(lobby['players']) == 2:
                    if is_move_valid(cell_id, lobby_id) and role == lobby['turn']:
                        lobby['board'][cell_id] = role
                        win = check_win(lobby_id, role)
                        draw = check_draw(lobby_id)
                        lobby['turn'] = 'O' if role == 'X' else 'X'
                        
                        for player in lobby['players']:
                            await player.send_text(json.dumps({
                                'action': 'moved',
                                'lobby_id': lobby_id,
                                'role': role,
                                'cell_id': cell_id,
                                'next_role': lobby['turn']
                            }))
                            if win:
                                await player.send_text(json.dumps({'action': 'won', 'role': role}))
                            elif draw:
                                await player.send_text(json.dumps({'action': 'draw'}))
                        
                        if win or draw:
                            del lobbies[lobby_id]

    except WebSocketDisconnect:
        pass # Игрок просто закрыл вкладку