import json
import os

from myutils.configutils import resource_path

def bgi2minimap(bgi_json, save_path, save=False):
    dx,dy = 790,1241
    with open(bgi_json, 'r', encoding='utf8') as f:
        data = json.load(f)
        new_data = dict()
        info = data.get('info')
        print(info)
        new_data['name'] = info.get('name')
        new_data['anchor_name'] = '传送锚点'
        new_data['country'] = '璃月'
        point_type = info.get('type')
        if point_type == 'collect':
            new_data['executor'] = 'CollectPathExecutor'
        positions = data.get('positions', [])
        for position in positions:
            if position.get('move_mode') == 'walk':
                position['move_mode'] = 'normal'
            if position.get('type') == 'teleport':
                position['type'] = 'path'
            x = -position.get('x') + dx/2
            y = -position.get('y') - dy/2
            position['x'] = x*2
            position['y'] = y*2

        new_data['positions'] = positions
    print(new_data)
    # 如果 save 为 True，则保存修改后的 JSON 文件
    if save:
        with open(save_path, 'w', encoding='utf8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        print(f"修改后的 JSON 已保存到 {save_path}")

def minimap2bgi(minimap_json, save_path, save=False):
    dx, dy = 790, 1241
    with open(minimap_json, 'r', encoding='utf8') as f:
        data = json.load(f)
        new_data = dict()
        new_data['info'] = {
            'name': data.get('name'),
            'type': 'collect' if data.get('executor') == 'CollectPathExecutor' else 'other'
        }
        positions = data.get('positions', [])
        for index, position in enumerate(positions, start=1):  # 从1开始递增
            position['id'] = index  # 添加 id 字段
            if position.get('move_mode') == 'normal':
                position['move_mode'] = 'walk'
            if position.get('type') == 'path':
                position['type'] = 'teleport'
            x = -position.get('x') / 2 + dx / 2
            y = -position.get('y') / 2 - dy / 2
            position['x'] = x
            position['y'] = y

        new_data['positions'] = positions
    print(new_data)
    # 如果 save 为 True，则保存修改后的 JSON 文件
    if save:
        with open(save_path, 'w', encoding='utf8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        print(f"修改后的 JSON 已保存到 {save_path}")

if __name__ == '__main__':
    folder = os.path.join(resource_path, 'pathlist', '灼灼彩菊')
    new_folder = os.path.join(resource_path, 'pathlist', 'bgi灼灼彩菊')
    if not os.path.exists(new_folder):
        os.makedirs(new_folder)
    files = os.listdir(folder)
    for file in files:
        file_path = os.path.join(folder, file)
        save_path = os.path.join(new_folder, f'bgi{file.split(".json")[0]}.json')
        try:
            # bgi2minimap(bgi_json=file_path, save_path=save_path, save=True)
            minimap2bgi(minimap_json=file_path, save_path=save_path, save=True)
        except Exception as e:
            print(e)