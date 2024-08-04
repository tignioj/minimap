import math
import sys
import threading
import time

import cv2
import numpy as np

from matchmap.minimap_interface import MinimapInterface
import os


# MinimapInterface.create_cached_local_map()

def calculate_angle(x0, y0, x1, y1):
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
        return angle if dy >= 0 else angle + 2 * math.pi
    else:
        return angle + math.pi


def getjson(filename):
    # 获取当前脚本所在的目录
    current_file_path = os.path.dirname(__file__)
    target = filename.split("_")[0]
    relative_path = f"../autotrack/pathlist/{target}"
    # 拼接资源目录的路径
    file = os.path.join(relative_path, filename)
    return file

def show_points(points, object_to_detect=None, radius=1024):
    if len(points) < 1:
        return

    region_img = get_points_img(points,object_to_detect, radius)
    cv2.imshow('points', region_img)
    key = cv2.waitKey(1)
    if key & 0xFF == ord('q'):
        cv2.destroyAllWindows()
    return region_img

def get_points_img(points, object_to_detect, radius=2048, user_position=None):
    if points is None or len(points) < 1:
        return
    point_start = points[0]
    dx,dy = 0,0
    region_img = MinimapInterface.get_region_map(point_start['x'], point_start['y'], radius)
    if user_position:
        region_img = MinimapInterface.get_region_map(user_position[0], user_position[1], radius)
        if region_img is None:
            print('局部地图')
            return
        dx = user_position[0] - point_start['x']
        dy = user_position[1] - point_start['y']

    if region_img is None:
        print("无法获取局部地图")
        return
    last_point = point_start
    # print(dx,dy)
    for point in points:
        x = int(point['x'] - point_start['x'] + radius // 2 - dx)
        y = int(point['y'] - point_start['y'] + radius // 2 - dy)
        point_A = (x,y)

        x2 = int(last_point['x'] - point_start['x'] + radius // 2 - dx)
        y2 = int(last_point['y'] - point_start['y'] + radius // 2 - dy)
        point_B = (x2,y2)
        # 画线
        # cv2.line(image, point_A, point_B, (255, 0, 0), 2)
        cv2.arrowedLine(region_img, point_B, point_A, (255, 0, 0), 2, tipLength=0.2)
        last_point = point

        # 画点（在指定坐标处绘制一个红色的点，大小为2）
        if point['type'] == 'start' or point['type'] == 'end':
            color = (0, 0, 255)  # 红色，BGR格式
        elif point['type'] == object_to_detect:
            color = (0, 255, 0)  # 绿色，BGR格式
        elif point['type'] == 'path':
            color = (0, 255, 255)  # 黄色，BGR格式
        thickness = 1
        cv2.circle(region_img, (x, y), thickness, color, 2)

    return region_img

def get_points_img_live(points, object_to_detect=None, radius=1024):
    if points is None or len(points) == 0:
        return None
    pos = MinimapInterface.get_position()
    region_img = get_points_img(points, object_to_detect, radius, pos)
    if pos is None:
        return
    cv2.circle(region_img, (radius//2,radius//2), 5, (0,255,255), 2)
    return region_img


def show_points_live(points, object_to_detect=None, radius=1000):
    """
    事实显示路径（包括任务所在位置）
    :param points:
    :param object_to_detect:
    :param radius:
    :return:
    """
    region_img = get_points_img_live(points, object_to_detect, radius)
    if region_img is None:
        print('加载失败')
        return

    # show_size = 800
    # if region_img.shape[0] > show_size:
    #     region_img = cv2.resize(region_img, None,fx=show_size/radius, fy=show_size/radius)
    cv2.imshow('path viewer', region_img)
    cv2.moveWindow('path viewer', 10, 10)
    key = cv2.waitKey(1)  # 不要用多线程调用, 否则会卡住
    if key & 0xFF == ord('q'):
        cv2.destroyAllWindows()
        sys.exit(0)


if __name__ == '__main__':
    # jsonfile = getjson('调查_稻妻_九条阵屋_2024-04-27_16_48_26.json')
    # jsonfile = getjson('调查_稻妻_无相火_2024-04-27_15_37_44.json')
    # jsonfile = getjson('调查_稻妻_名椎滩_2024-04-28_05_54_44.json')
    # jsonfile = getjson('调查_稻妻_沉眠之庭副本西侧_2024-04-28_15_56_01.json')
    # jsonfile = getjson('调查_须弥_鸡哥左下角_2024-04-29_13_45_26.json')
    # jsonfile = getjson('调查_璃月_测试4_绝云间_2024-07-30_09_12_47.json')
    jsonfile = getjson('调查_璃月_珉林东北_2024-04-27_12_54_51.json')

    import json

    with open(jsonfile, encoding="utf-8") as r:
        json_obj = json.load(r)
        object_to_detect = json_obj["name"]
        print(f"当前采集任务:{object_to_detect}")
        path_list = json_obj['positions']
        # show_points_live(path_list, object_to_detect=object_to_detect)
        show_points(path_list, object_to_detect=object_to_detect)
        # while True:
        #     show_points_live(path_list, object_to_detect=object_to_detect, radius=1024)
