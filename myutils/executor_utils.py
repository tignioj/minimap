from mylogger.MyLogger3 import MyLogger
import os
from myutils.configutils import cfg
from typing import List
import numpy as np
logger = MyLogger('track_utils')
import json


def log(*args):
    logger.debug(args)

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


