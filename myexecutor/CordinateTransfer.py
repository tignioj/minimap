import json
import os
import sys

from myutils.configutils import resource_path
from myutils.fileutils import getjson_path_byname

def bgi2minimap(bgi_json, save_path, save=False):
    dx,dy = 790,1241
    with open(bgi_json, 'r', encoding='utf8') as f:
        data = json.load(f)
        new_data = dict()
        info = data.get('info')
        print(info)
        new_data['name'] = info.get('name')
        new_data['anchor_name'] = '传送锚点'
        new_data['country'] = '稻妻'
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


if __name__ == '__main__':
    folder = os.path.join(resource_path, 'pathlist', '鸣草')
    new_folder = os.path.join(resource_path, 'pathlist', '新鸣草')
    files = os.listdir(folder)
    for file in files:
        file_path = os.path.join(folder, file)
        save_path = os.path.join(new_folder, f'新{file.split(".json")[0]}_new.json')
        bgi2minimap(bgi_json=file_path, save_path=save_path, save=True)