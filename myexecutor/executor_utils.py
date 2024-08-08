from mylogger.MyLogger3 import MyLogger
from myutils.configutils import cfg
import numpy as np
logger = MyLogger('track_utils')
import json


def log(*args):
    logger.debug(args)

class Point:
    TYPE_PATH = 'path'
    TYPE_TARGET = 'target'

    def __init__(self, x, y, type=TYPE_PATH, action=None):
        self.x = x
        self.y = y
        if type: self.type = type
        if action: self.action = action




from typing import List
def load_json(json_file_path):
    json_map = {
        "country": None,
        "positions": None,
        "name": None
    }
    from myutils.configutils import resource_path
    with open(json_file_path, encoding="utf-8") as r:
        json_obj = json.load(r)
        json_map['country'] = json_obj.get('country', '蒙德')
        json_map['name'] = json_obj.get('name')
        positions = json_obj.get('positions')

    if json_map is None or len(positions) < 1: raise Exception(f"空白路线, 跳过")
    json_map['positions']:List[Point] = []
    for point in positions:
        p = Point(x=point.get('x'), y=point.get('y'), type=point.get('type'))
        json_map['positions'].append(p)
    return json_map
def point1_near_by_point2(point1, point2, threshold):
    """
    两点的欧氏距离是否小于阈值,是则返回True
    :param point1:
    :param point2:
    :param threshold:
    :return:
    """
    if point1 is None or point2 is None:
        return False

    # 计算两点之间的欧氏距离
    distance = np.linalg.norm(np.array(point1) - np.array(point2))
    # self.log("欧式距离", distance)
    # 检查距离是否小于阈值
    if distance < threshold:
        return True
    else:
        return False


def calculate_angle(x0, y0, x1, y1):
    """
    计算 (x0,y0) -> (x1,y1)的角度
    :param x0:
    :param y0:
    :param x1:
    :param y1:
    :return:
    """
    import math
    # 计算斜率
    dx = x1 - x0
    dy = y1 - y0

    # 特殊情况处理
    if dx == 0:
        if dy > 0:
            return math.pi / 2  # 90度
        elif dy < 0:
            return 3 * math.pi / 2  # 270度
        else:
            return None  # 无法确定角度

    angle = math.atan(dy / dx)

    # 判断角度是否在正确的象限
    if dx > 0:
        ang = angle if dy >= 0 else angle + 2 * math.pi
    else:
        ang = angle + math.pi

    # 上面的结果是x轴正方向极坐标角度值, 0~360度
    # 下面将0~360的结果变成 179 ~ 1 | -1 ~ -179
    if ang is not None:
        deg = int(math.degrees(ang))
        if deg < 90:
            deg = -(deg + 90)
        else:
            deg = 180 - (deg - 90)
        return deg
    else:
        return None


