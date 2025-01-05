# -*- coding: utf-8 -*-
'''
    Код среды Snake2D
    Содержит баги и неоптимальные решения!
    
    Для корректной работы действия игроков должны иметь формат:
        {'id': 'player_id', 'actions': {'snake_id_1': [dir_y, dir_x], 'snake_id_2': [dir_y, dir_x]}}
        [dir_y, dir_x] должно быть одно из [[-1,0], [0,-1], [0,1], [1,0]]
        змейки длиной более 1 клетки не могут поворачивать на 180
'''


import numpy as np
from copy import copy


class Snake2D:
    def __init__(self):
        self.name = 'Snake2D'
        self.n_players = 2
        self.snakes_per_player = 2
        self.field_size = (30,30)
        self.field = [[]]
        self.food = []
        self.n_food = max(self.field_size[0]*self.field_size[1]//20, 1)
        self.fences = []
        self.fences_arr = [[]]
        self.n_fences = 0#max(self.field_size[0]*self.field_size[1]//10, 1)
        self.snakes = {}
        self.tick = 0
        self.snake_id_counter = 0
        self.actions = {}
        self.points = {}
        self.history = []
        self.possible_directions = [[-1,0], [0,-1], [0,1], [1,0]]
        self.errors = {}
        
    
    # Функция добавляющая нового игрока в среду и возвращающая успешность данного действия 
    def add_player(self, player):
        if len(self.snakes.keys()) < self.n_players and not player in self.snakes.keys():
            self.snakes[player] = {}
            return True
        return False
    
    # Функция проверяющая что все игроки готовы и можно начинать игру
    def is_ready(self):
        if len(self.snakes.keys()) == self.n_players:
            return True
        return False
      
    # Функция проверяющая конечное состояние игры (в данном случае игра завершается на 100 тике)
    def is_teminate_state(self):
        if self.tick >= 100:
            return True
        return False
        
        
    # Здесь формируются области видимости для каждого игрока, в случае если в будущем они будут ограничены радиусом обзора
    # Информация о агентах противника анонимизируется (змеек противника нельзя различить между собой)
    def get_players_obs(self):
        player_ids = self.snakes.keys()
        data = {}
        for _id in player_ids:
            data[_id] = {'points': self.points[_id] ,'snakes': self.snakes[_id], 'enemies':[], 'food':self.food, 'fences':self.fences, 'errors':[]}
            if _id in self.errors:
                data[_id]['errors'] = self.errors[_id]
            for enemy_id in player_ids:
                if _id != enemy_id:
                    for enemy_snake_id in self.snakes[enemy_id].keys():
                        data[_id]['enemies'].append(self.snakes[enemy_id][enemy_snake_id])
        return data
    
    
    # Функиция отрисовывающая игровую область в матрице, которая используется для некоторых проверок и рендера в консоль
    def refresh_field(self):
        self.field = [['.' for j in range(self.field_size[1])] for i in range(self.field_size[0])]
        for fence in self.fences:
            self.field[fence[0]][fence[1]] = '#'
        for food in self.food:
            self.field[food[0]][food[1]] = '0'
        for player in list(self.snakes.keys()):
            for snake in list(self.snakes[player].keys()):
                for cell in self.snakes[player][snake]['geometry']:
                    self.field[cell[0]][cell[1]] = player
        
    
    # Рендер в консоль
    def test_render(self):
        for row in self.field:
            print(''.join(row))
            
        
    # Функция задающее начальное (стартовое) состояние игры
    def reset(self):
        self.fences_arr = [[False for j in range(self.field_size[1])] for i in range(self.field_size[0])]
        self.tick = 0
        # Генерируем уникальные начальные позиции всех элементов на поле
        initital_positions = np.random.choice(self.field_size[0]*self.field_size[1],
                                              self.n_fences+self.n_food+self.n_players*self.snakes_per_player,
                                              replace=False)
        self.points = {}
        n_all = 0
        # Далее поочередно присваиваем их элементам
        for n in range(self.n_fences):
            # Сразу конвертируем в обычный int т.к np.int32 не передается в json
            i = int(initital_positions[n]//self.field_size[0])
            j = int(initital_positions[n]%self.field_size[1])
            self.fences.append([i,j])
            self.fences_arr[i][j] = True
        
        n_all += self.n_fences
        for n in range(n_all, n_all+self.n_food):
            i = int(initital_positions[n]//self.field_size[0])
            j = int(initital_positions[n]%self.field_size[1])
            self.food.append([i,j])

        n_all += self.n_food
        player_ids = list(self.snakes.keys())
        self.snake_id_counter = 0
        for p in range(self.n_players):
            self.points[player_ids[p]] = 0
            for s in range(self.snakes_per_player):
                n = n_all+p*self.snakes_per_player + s
                i = int(initital_positions[n]//self.field_size[0])
                j = int(initital_positions[n]%self.field_size[1])
                
                self.snakes[player_ids[p]][str(self.snake_id_counter)] = {'geometry': [[i,j]], 'points':0, 'direction':self.possible_directions[0]}
                self.snake_id_counter+=1
        self.refresh_field()
        # возвращаем индивидуальные наблюдения для агентов + проверку на конечное состояние (аналогично step)
        return self.get_players_obs(), self.is_teminate_state()
    
    

    # Функция записывающая действия одного агента когда они передаются с сервера
    def process_action(self, action):
        print(action)
        self.actions[action['id']] = action['actions']
        if len(self.actions.keys()) == self.n_players:
            return True
        return False
    
          
    # Основная функция игры обрабатывающая действия агентов и все события на поле
    def step(self):
        # actions в данный момент содержит действия всех агентов по ключам
        actions = self.actions
        # Переотрисовываем поле чтобы иметь актуальную информацию
        self.refresh_field()
        # Здесь сохраняем возникающие ошибки исполнения команд, чтобы передать их игрокам в качестве логов
        self.errors = {}
        # Массив для хранения информации от игроках чьи змейке врезались во что-то и нуждаются в респавне
        to_respawn = []
        player_ids = list(self.snakes.keys())
        # Переменная для костыльного хитрожопого способа проверить что 2 змеи ходят в одну клетку
        # Скорее всего надо будет переделать, я уже сплавился когда этот кринж дописывал
        wanted = {}
                
        print(self.actions)
        # Сначала проверяем что змейки ходят корректно и ни во что не врезаются
        # А если врезаются, то удаляем их
        for player_id in player_ids:
            for snake_id in list(self.snakes[player_id].keys()):
                print([player_id, snake_id])
                action = actions[player_id][snake_id]
                current_dir = self.snakes[player_id][snake_id]['direction']
                geometry = self.snakes[player_id][snake_id]['geometry']
                # Невозможное действие: некорректный формат или разворот на 180 при длине > 1
                if not action in self.possible_directions or (len(self.snakes[player_id][snake_id]['geometry']) > 1 and
                                                              (action[0]==-current_dir[0] or action[1]==-current_dir[1])):
                    if not player_id in self.errors:
                        self.errors[player_id] = []
                    print('Некорректное действие', action, current_dir)
                    self.errors[player_id].append(f'Невозможное действие: {action} для змеи с id {snake_id}')
                # Если всё корректно, обновляем текущее направление движения змейки
                else:
                    self.snakes[player_id][snake_id]['direction'] = action
                    
                current_dir = self.snakes[player_id][snake_id]['direction']
                print('Попытка хода в ячейку:', geometry[0][0]+current_dir[0], geometry[0][1]+current_dir[1])
                # Выход за границы поля
                if not self.field_size[0] > geometry[0][0]+current_dir[0] >= 0 or not self.field_size[1] > geometry[0][1]+current_dir[1] >= 0:
                    # уничтожаем
                    to_respawn.append(player_id)
                    self.points[player_id] = int(self.points[player_id]*0.8)
                    print('Выход за границы', action, geometry[0])
                    del self.snakes[player_id][snake_id]
                # Столкновение с препятствием
                elif self.fences_arr[geometry[0][0]+current_dir[0]][geometry[0][1]+current_dir[1]]:
                    to_respawn.append(player_id)
                    self.points[player_id] = int(self.points[player_id]*0.8)
                    print('Столкновение', action, geometry[0])
                    del self.snakes[player_id][snake_id]

                    
        # Теперь формируем ту самую перемунную wanted которая имеет формат 
        '''
        {
            '[0,0]' : [[player_id_1, snake_id, y, x]],
            '[5,8]' : [[player_id_1, snake_id, y, x], [player_id_2, snake_id, y, x]] - пример когда 2 игрока пытаются походить в ячейку по координатам 5 8
            ...
            
            }
        '''
        for player_id in player_ids:
            for snake_id in list(self.snakes[player_id].keys()):
                action = actions[player_id][snake_id]
                geometry = copy(self.snakes[player_id][snake_id]['geometry'])
                current_dir = self.snakes[player_id][snake_id]['direction']
                key = str(list([geometry[0][0]+current_dir[0], geometry[0][1]+current_dir[1]]))
                if not key in wanted.keys():
                    wanted[key] = [[player_id, snake_id, geometry[0][0]+current_dir[0], geometry[0][1]+current_dir[1]]]
                else:
                    wanted[key].append([player_id, snake_id, geometry[0][0]+current_dir[0], geometry[0][1]+current_dir[1]])
                              
        # Перебираем ячейки в которые ходят змейки
        for key in list(wanted.keys()):
            if len(wanted[key]) > 1:
                # Две или более змейки хотят походить в одну клетку
                print('Две в оду', wanted[key])
                for e in wanted[key]:
                    to_respawn.append(e[0])
                    self.points[player_id] = int(self.points[e[0]]*0.8)
                    del self.snakes[e[0]][e[1]]
            else:
                e = wanted[key][0]
                print(e)
                # Столкновение с другой змейкой
                if self.field[e[-2]][e[-1]] in player_ids:
                    print('Вероятно врезались', e)
                    other = self.field[e[-2]][e[-1]]
                    # Ищем нужную змейку игрока (приходится т.к на поле пишутся id игроков, а не змей, мб можно поправить)
                    for other_snake in list(self.snakes[other].keys()):
                        # Проверяем, врезаемся не в хвост (если змейка длиной 1 то голова = хвост)
                        '''
                        АХТУНГ!!!
                        Тут есть баг связанный с тем что если змейка в которую врезаемся съест еду в этом ходу то хвост не подвинется и нужно уничтожить змею игрока
                        '''
                        if len(self.snakes[other][other_snake]['geometry'])>1 and [e[-2],e[-1]] in self.snakes[other][other_snake]['geometry'][1:-1]:
                            print('Врезались в голову', self.snakes[other][other_snake]['geometry'])
                            to_respawn.append(e[0])
                            self.points[player_id] = int(self.points[e[0]]*0.8)
                            del self.snakes[e[0]][e[1]]
                            break
        
        # Ход для тех змеек которые не столкнулись
        for player_id in player_ids:
            for snake_id in list(self.snakes[player_id].keys()):
                current_dir = self.snakes[player_id][snake_id]['direction']
                geometry = copy(self.snakes[player_id][snake_id]['geometry'])
                i = int(geometry[0][0]+current_dir[0])
                j = int(geometry[0][1]+current_dir[1])
                # Если съела еду, то не укорачивам тело 
                if self.field[i][j] == '0':
                    self.points[player_id]+=1
                    self.food.remove([i,j])
                    self.field[i][j] = player_id
                    self.snakes[player_id][snake_id]['geometry'] = [[i, j]] + geometry
                else:
                    self.snakes[player_id][snake_id]['geometry'] = [[i, j]] + geometry[:-1]
                    
                    
        # Респавн змей в рандомных свободных координатах
        # Переотрисовываем поле с учётом последних ходов
        self.refresh_field()
        print('respawn', to_respawn)
        for e in to_respawn:
            self.snake_id_counter+=1
            i = int(np.random.choice(self.field_size[0]))
            j = int(np.random.choice(self.field_size[1]))
            while self.field[i][j] != '.':
                i = int(np.random.choice(self.field_size[0]))
                j = int(np.random.choice(self.field_size[1]))
            self.field[i][j] = e
            self.snakes[e][str(self.snake_id_counter)] = {'geometry': [[i,j]], 'points':0, 'direction':self.possible_directions[0]}
            
        # Респавн еды
        '''
        Стоит переработать т.к по мере роста змей свободных клеток становится на поле всё меньше
        а кол-во еды остается прежним, т.е змейки будут быстрее на неё натыкаться и разрастаться.
        Возможно стоит генерировать кол-во еды как % от свободных клеток, а не как % от размера поля.
        '''
        cur_food = len(self.food)
        if cur_food < self.n_food:
            for i in range(self.n_food - cur_food):
                i = int(np.random.choice(self.field_size[0]))
                j = int(np.random.choice(self.field_size[1]))
                while self.field[i][j] != '.':
                    i = int(np.random.choice(self.field_size[0]))
                    j = int(np.random.choice(self.field_size[1]))
                self.field[i][j] = '0'
                self.food.append([i,j])
                    

        # Очищаем actions и увеличиваем тик
        self.actions = {}
        self.tick+=1
        # Возвращаем новые наблюдения и флаг конца игры
        return self.get_players_obs(), self.is_teminate_state()
    

        
            
        
        
            