from mylogger.MyLogger3 import MyLogger
import os
from myutils.configutils import cfg
from typing import List
# from myexecutor.BasePathExecutor2 import Point
import numpy as np

logger = MyLogger('track_utils')
import json


def log(*args):
    logger.debug(args)


def euclidean_distance(coordinates1, coordinates2):
    return np.linalg.norm(np.array(coordinates1) - np.array(coordinates2))


def find_closest_point_index(coordinates, points, distance_threshold=None):
    """
    寻找距离指定坐标最近的点的下标, 要求最近的点在指定阈值内,如果不指定阈值则直接返回最近的
    :param coordinates:
    :param points:
    :param distance_threshold:
    :return:
    """
    closest_point_index = None
    min_distance = float('inf')
    for index, point in enumerate(points):
        distance = euclidean_distance(coordinates, (point.x, point.y))
        if distance < min_distance:
            min_distance = distance
            closest_point_index = index

    if distance_threshold is not None:  # 如果指定了阈值,则判断最终结果是否小于阈值
        # 小于则返回最近的点下标,否则返回空
        if min_distance < distance_threshold:
            return closest_point_index
        else:
            return None
    else:
        return closest_point_index  # 没有指定阈值,直接返回最近的点下标



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
    return euclidean_distance(point1, point2) < threshold


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
