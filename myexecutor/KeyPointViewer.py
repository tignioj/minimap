import sys
import time

from typing import List
import cv2
from matchmap.minimap_interface import MinimapInterface
from myexecutor.executor_utils import load_json, Point
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
    target = filename.split("_")[0]
    from myutils.configutils import resource_path
    # 拼接资源目录的路径
    file = os.path.join(resource_path,'pathlist',target, filename)
    return file

def show_points(points, object_to_detect=None, width=1024, scale=None):
    if len(points) < 1:
        return

    region_img = get_points_img(points,object_to_detect, width,scale=scale)
    # region_img = cv2.resize(region_img, None, fx=0.5, fy=0.5)
    cv2.imshow('points', region_img)
    # cv2.imwrite('jiuguan.png', region_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def get_points_img(points: List[Point], object_to_detect, width=2048, user_position=None, scale=None):
    if points is None or len(points) < 1: return

    point_start = points[0]
    dx,dy = 0,0
    region_img = MinimapInterface.get_region_map(point_start.x, point_start.y, width)
    if user_position:
        region_img = MinimapInterface.get_region_map(user_position[0], user_position[1], width)
        if region_img is None:
            print('局部地图为空')
            return
        dx = user_position[0] - point_start.x
        dy = user_position[1] - point_start.y

    if region_img is None:
        print("无法获取局部地图")
        return
    last_point = point_start
    # print(dx,dy)
    for index, point in enumerate(points):
        x = int(point.x - point_start.x + width // 2 - dx)
        y = int(point.y - point_start.y + width // 2 - dy)
        point_A = (x,y)

        x2 = int(last_point.x - point_start.x + width // 2 - dx)
        y2 = int(last_point.y - point_start.y + width // 2 - dy)
        point_B = (x2,y2)
        # 画线
        # cv2.line(image, point_A, point_B, (255, 0, 0), 2)
        cv2.arrowedLine(region_img, point_B, point_A, (255, 0, 0), 1, tipLength=0.2)
        last_point = point

        # 画点（在指定坐标处绘制一个红色的点，大小为2）
        if point.type == object_to_detect:
            color = (0, 255, 0)  # 绿色，BGR格式
        elif point.type == Point.TYPE_PATH:
            color = (0, 255, 255)  # 黄色，BGR格式
        else:
            color = (100, 100, 100)
        thickness = 1
        cv2.circle(region_img, (x, y), thickness, color, 2)

        # 定义要添加的文字和位置
        text = f'{index}'
        # 选择字体、字体大小、颜色等
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        color = (80, 80, 30)  # BGR颜色 (蓝, 绿, 红)
        thickness = 1
        # 在图像上添加文字
        cv2.putText(region_img, text, (x,y), font, font_scale, color, thickness)

    # 计算中心点
    if scale:
        if scale < 0.1: scale = 0.1
        elif scale > 10: scale = 10
        height, width = region_img.shape[:2]
        center = (width // 2, height // 2)

        # 定义放大倍数
        scale_factor = scale

        # 创建仿射变换矩阵
        matrix = cv2.getRotationMatrix2D(center, 0, scale_factor)

        # 应用缩放（放大）
        region_img = cv2.warpAffine(region_img, matrix, (width, height))

    return region_img


def get_points_img_live(points: [Point], object_to_detect=None, width=1024,scale=None):
    if points is None or len(points) == 0:
        return None
    pos = MinimapInterface.get_position()
    region_img = get_points_img(points, object_to_detect, width, pos, scale)
    if pos is not None: cv2.circle(region_img, (width//2,width//2), 5, (0,255,255), 2)
    return region_img


def show_points_live(points: List[Point], object_to_detect=None, width=1024,scale=None):
    """
    事实显示路径（包括任务所在位置）
    :param points:
    :param object_to_detect:
    :param width:
    :return:
    """
    region_img = get_points_img_live(points, object_to_detect, width,scale)
    if region_img is None:
        print('加载失败')
        return

    # show_size = 800
    # if region_img.shape[0] > show_size:
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
    # jsonfile = getjson('调查_稻妻_名椎滩_2024-04-28_05_54_44.json')
    # jsonfile = getjson('甜甜花_蒙德_清泉镇_2024-07-31_07_30_39.json')
    # jsonfile = getjson('jiuguan_蒙德_test_scale2_20240808.json')
    jsonfile = getjson('jiuguan_蒙德_wfsd_20240808.json')
    json_map = load_json(jsonfile)
    import json
    # show_points(json_map['positions'], json_map['name'], 1024, scale=2)
    while True:
        time.sleep(0.1)
        show_points_live(json_map.get('positions'))
        # show_points(p.points, p.target_name, 1024)
    #     show_points_live(path_list, object_to_detect=object_to_detect, width=1024)
