# -*- coding: utf-8 -*-
'''
    Пример клиенты для Snake2D
    Требования к клиентам: 
        отправка ивента join для присоединения к среде в формате {'id':'N', 'env': 'EnvName'}
        обработка ивентов get_action, game_over
        отправка ивента action в формате {'id':'N', 'actions':{...according to env doc...}}
        
    TODO:
        Сделать универсальный клиент и код агентов отдельно
'''

import socketio
from time import sleep

def mdist(v1, v2):
    return abs(v2[0]-v1[0]) + abs(v2[1]-v1[1])

def strategy(obs, _id):
    snakes = obs['snakes']
    food = [{'pos':f} for f in obs['food']]
    actions = {'id':_id, 'actions':{}}
    for snake_id in snakes.keys():
        sn = snakes[snake_id]
        for f in food:
            f['dist'] = mdist(sn['geometry'][0], f['pos'])
        target = sorted(food, key=lambda d: d['dist'])[0]
        target_dir = [0,0]
        sign = lambda x: -1 if x < 0 else 1 if x != 0 else 0
        target_dir[0] = sign(target['pos'][0]-sn['geometry'][0][0])
        if target_dir[0] == 0:
            target_dir[1] = sign(target['pos'][1]-sn['geometry'][0][1])
        actions['actions'][int(snake_id)] = target_dir
    return actions
        

sio = socketio.SimpleClient()

sio.connect('http://127.0.0.1:5500')

sio.emit('join', {'id':'2', 'env': 'Snake2D'})
event = None
while True:
    event = sio.receive()
    if event[0] != 'get_action':
        print(event[0])
        break
    actions = strategy(event[1], '2')
    print(actions)
    sio.emit('action', actions)

sleep(1)

sio.disconnect()