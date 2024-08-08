import json
import os
import sys
import cv2
def shift_file_positions(json_path,dx, dy,scale=1, save=False):
    with open(json_path, mode='r',encoding='utf8') as json_file:
        data = json.load(json_file)
        # 修改positions中的x和y值
        for position in data['positions']:
            position['x'] += dx
            position['y'] += dy

        modified_json_data = json.dumps(data, ensure_ascii=False, indent=4)

        # 将修改后的数据转换回JSON格式
    if save:
        filename = json_path.split(".json")[0]
        with open(f'{filename}_scale{scale}_.json', mode='w',encoding='utf8') as json_file:
            json_file.write(modified_json_data)

    return modified_json_data

def __getjson(filename):
    # 获取当前脚本所在的目录
    target = filename.split("_")[0]
    relative_path = f"pathlist/{target}"
    # 拼接资源目录的路径
    file = os.path.join(relative_path, filename)
    return file

x2_known = 1695.16736
y2_known = 2262.8335
x1_known = 3339.6590312499993
y1_known = -6682.49447265625

# x2_known = -19
# y2_known = -22
# x1_known = 762.2859843749993
# y1_known = -3251.8152734375

# 计算坐标系2的原点在坐标系1中的位置
scale = 1.5
x0 = x1_known - scale * x2_known
y0 = y1_known + scale * y2_known  # y轴反向
print(x0,y0)
# sys.exit(0)
def convert_coordinates(x2, y2):
    """
    将坐标系2的坐标转换为坐标系1的坐标。
    参数:
    x2, y2 - 坐标系2中的坐标
    返回:
    x1, y1 - 坐标系1中的坐标
    """
    # 转换坐标系2到坐标系1的尺度
    x1 = x0 + scale * x2
    y1 = y0 - scale * y2  # y轴方向相反，所以需要取负值

    return x1, y1
def jiuguan2minimap(json_path,dx,dy,scale=1.0, save=False):
    minimap_paths = []
    with open(json_path, mode='r',encoding='utf8') as json_file:
        data = json.load(json_file)
        curve_list = data['curve_list']
        for curve in curve_list:
            # 保存一个线段
            minimap_path = {
                'name': curve['lineName'], 'country': "蒙德", 'positions': [] }
            # 修改positions中的x和y值
            for index,poi in enumerate(curve['curve_poi']):
                x,y = convert_coordinates(poi['x'], poi['y'])
                if index ==0 :
                    print(x,y)
                minimap_path['positions'].append({
                    "x": x,
                    "y": y,
                    "type": "target"
                })
                minimap_paths.append(minimap_path)
        if save:
            filename = json_path.split(".json")[0]
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d")
            with open(f'{filename}_{timestamp}.json', mode='w',encoding='utf8') as json_file:
                # 将修改后的数据转换回JSON格式
                modified_json_data = json.dumps(minimap_path, ensure_ascii=False, indent=4)
                json_file.write(modified_json_data)
    return minimap_paths

if __name__ == '__main__':
    # jsonname = '甜甜花_蒙德_清泉镇_2024-07-31_07_30_39.json'
    # jsonname = 'jiuguan_蒙德_test.json'
    jsonname = 'jiuguan_蒙德_wfsd.json'
    # jsonname = 'jiuguan_test3.json'
    jsonfile = __getjson(jsonname)
    # shiftjson = shift_file_positions(jsonfile, -1, 1.26, save=False)
    p = jiuguan2minimap(jsonfile, 0, 0,1.5,True)
