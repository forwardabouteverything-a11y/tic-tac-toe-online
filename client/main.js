const cells = document.querySelectorAll('.cell');
const lobby_status = document.getElementById('lobby-status')
const game_screen = document.getElementById('game-screen')
const lobby_screen = document.getElementById('lobby-screen')
const lobby_id_text = document.getElementById('lobby_id_shown')

let myRole = null;        
let currentTurn = 'X'; 
let myLobbyId = null;     
let gameActive = true;   

let win_conditions = [[0, 1, 2], [3, 4, 5], [6, 7, 8],
                      [0, 3, 6], [1, 4, 7], [2, 5, 8],
                      [0, 4, 8], [6, 4, 2]]

const websocket = new WebSocket('ws://127.0.0.1:8001/ws');

// Очередь сообщений, которые ждут открытия соединения
let messageQueue = [];

websocket.onopen = () => {
    console.log("Соединение установлено!");
    // Отправляем всё, что накопилось в очереди
    messageQueue.forEach(msg => websocket.send(msg));
    messageQueue = [];
};

// Универсальная функция отправки
function sendMessage(obj) {
    const msg = JSON.stringify(obj);
    if (websocket.readyState === WebSocket.OPEN) {
        websocket.send(msg);
    } else {
        messageQueue.push(msg); // Если не открыто — кладем в очередь
    }
}

function checkWin()
{
    for (const condition of win_conditions)
    {
        const [a, b, c] = condition

        if (isCellMine(a) && isCellMine(b) && isCellMine(c))
        {
            return true
        }
    }

    return false
}

cells.forEach((cell, index) => {
    cell.addEventListener('click', () => {
        if (cell.textContent !== '' || !gameActive || myRole !== currentTurn) return;
        const event = {
            action: 'move', 
            lobby_id: myLobbyId,
            role: myRole, 
            cell_id: index
        };
        sendMessage(event);
    });
});

document.getElementById('btn-create').addEventListener('click', () => {
    sendMessage({ action: 'create_lobby' });
});

document.getElementById('btn-join').addEventListener('click', () => {
    const lobbyId = document.getElementById('input-join').value.trim();
    if (lobbyId) {
        sendMessage({ action: 'join_lobby', lobby_id: lobbyId });
    }
});

websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.action === 'lobby_created')
    {
        myRole = data.role
        myLobbyId = data.lobby_id
        lobby_status.textContent = 'Лобби создано. Ожидание 2 игрока...'
        lobby_id_text.textContent = myLobbyId;
    }

    if (data.action === 'lobby_joined')
    {
        myRole = data.role
        myLobbyId = data.lobby_id
        lobby_status.textContent = 'Подключено!'
        startGame()
    }

    if (data.action === 'won') {
        gameActive = false;
        lobby_status.textContent = `Игра окончена! Победили ${data.role === 'X' ? 'Крестики' : 'Нолики'}!`;
        endGame()
    }

    if (data.action === 'draw')
    {
        gameActive = false;
        lobby_status.textContent = 'Ничья!'
        endGame()
    }

    if (data.action === 'error') {
        alert(data.message);
    }

    if (data.action === 'moved') {
        if (lobby_screen.style.display !== 'none') {
            startGame(); 
        }

        cells[data.cell_id].textContent = data.role;
        
        currentTurn = data.next_role;
    }

    if (data.action === 'player_joined')
    {
        lobby_status.textContent = data.message
        startGame()
    }
}

function startGame() {
    lobby_screen.style.display = 'none';
    game_screen.style.display = 'block';
    gameActive = true;
}

function endGame()
{
    lobby_screen.style.display = 'block';
    game_screen.style.display = 'flex';
    lobby_id_text.textContent = ''
    document.getElementById('input-join').value = ''
}

setInterval(() => 
{
    if (websocket.readyState !== WebSocket.OPEN)
    {
        lobby_status.textContent = 'not connected...'
    }
}, 50)