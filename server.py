# -*- coding: utf-8 -*-
'''
    Код сервера для совместной игры разных агентов в различных средах
    
    Требования к средам (наличие методов):
        add_player(player_id) - пытается добавить игрока в среду, возвращает True в случае успеха, иначе False
        is_ready() - проверяет, что игра готова к запуску, возвращает True в случае успеха, иначе False
        reset() - возвращает среду к начальному состоянию 
        process_action(player_action) - сохраняет действие игрока для дальнейшего исполнения и проверяет что все игроки походили, 
                                        возвращает True в случае успеха, иначе False
        step() - выполняет тик игры на основе сохраненных действий игроков 
        
    Добавить свою среду можно аналогично среде Snake2D 
    
    TODO:
        0) Добавить очистку переменных agent2env и running_envs после окончания игры и отключения игроков
        1) Объединить методы process_action и step
        2) Добавить автоматическое подтягивание существующих сред из папки envs
'''

from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from envs.snake2d import Snake2D


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Чтобы можно было разные компы между собой соединять (в данном случае через хамачи) прописываем CORS
socketio = SocketIO(app, cors_allowed_origins=['http://127.0.0.1:5500', 'http://25.40.163.238:5500'])
CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", 'http://25.40.163.238:5500']}}, methods=["GET", "POST"], allow_headers=["Access-Control-Allow-Origin", "*"])

# Переменная в которой хранится информация к какой среде подключен агент (для быстроты доступа)
agent2env = {
    
    }

# Тут хранятся инстансы всех запущенные среды по id
running_envs = {

    }



# Функция которая запускает игру если набралось нужное кол-во игроков
def start(env_id):
    print('Tring to start env')
    if running_envs[env_id]['env'].is_ready():
        print('Success!')
        # Команда reset сбрасывает состояние среды к начальной позиции и инициирует первый тик
        obs, t = running_envs[env_id]['env'].reset()
        # Отсылаем всем подключенным агентам их зону видимости с просьбой прислать действие 
        for e in running_envs[env_id]['connected']:
            emit('get_action', obs[e['id']], to=e['sid'])
    else:
        print('Not enough players...')


@socketio.on('connect')
def connect():
    print('connected:', request.sid)
    
    
@socketio.on('disconnect')
def disconnect():
    print('disconnected')
    
    
# Обработка запроса от агента на подключение к среде
@socketio.on('join')
def join(json):
    print('join triggered', request.sid)
    print(json)
    flag=False
    # Перебираем уже запущенные среды
    for env_id in running_envs.keys():
        # Если это нужная среда, пытаемся подключиться (add_player вернёт True если были свободные слоты)
        if running_envs[env_id]['env'].name == json['env'] and running_envs[env_id]['env'].add_player(json['id']):
            print(f"{request.sid} with inner id {json['id']} joined existed env {env_id}")
            flag = True
            agent2env[json['id']] = env_id
            running_envs[env_id]['connected'].append({'sid':request.sid, 'id': json['id']})
            start(env_id)
    
    # Если ничего не нашли
    if not flag:
        print('No specific env found, trying create new one:')
        # Проверяем запрашиваемое название среды
        if json['env'] == 'Snake2D':
            print('\tSnake2D')
            # Генерируем id новой среды
            if len(running_envs.keys()) == 0:
                env_id = 0
                print('Envs is empty')
            else:
                env_id = max(running_envs.keys())+1
            # Создаем среду и записываем в переменную
            running_envs[env_id] = {'env': Snake2D(), 'connected': []}
            # Подключаем к ней агента
            if running_envs[env_id]['env'].add_player(json['id']):
                running_envs[env_id]['connected'].append({'sid':request.sid, 'id': json['id']})
                agent2env[json['id']] = env_id
                print(f"Agent {request.sid} with inner id {json['id']} joined env with id {env_id}")
                start(env_id)
            else:
                print('Failed to connect to new env')
                emit('error', 'game name is correct but can\'t join')
                
    
# Функция обработки действия от агента
@socketio.on('action')
def process(json):
    # Проверяем что данный агент зарегистрирован и подключен к какой-то среде
    if json['id'] in agent2env.keys():
        # Вытаскиваем id среды из переменной
        env_id = agent2env[json['id']]
        # Игра записывает дейсвия данного агента
        if running_envs[env_id]['env'].process_action(json):
            # Если походили все агенты, выполняется тик игры
            obs, t = running_envs[env_id]['env'].step()
            print(running_envs[env_id]['env'].tick)
            # Отрисовка поля в консоль для отладки
            running_envs[env_id]['env'].test_render()
            # Если игра закончилась отсылаем ивент game_over
            # Вместе с полным состоянием (чтобы к примеру можно было посчитать reward и обучать RL)
            if t:
                for e in running_envs[env_id]['connected']: 
                    emit('game_over', obs, to=e['sid'])
                print(obs)
            # Если игра не закончилась, отсылаем агентам их область видимости + запрашиваем действие
            else:
                for e in running_envs[env_id]['connected']: 
                    emit('get_action', obs[e['id']], to=e['sid'])
    # Если агент не зарегистрирован, он должен сначала отправить ивент join 
    else:
        print(request.sid, 'id not registred!')



                

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5500)
    
    
