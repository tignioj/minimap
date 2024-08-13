import sys
import time

from typing import List
import cv2
from matchmap.minimap_interface import MinimapInterface
from myutils.jsonutils import getjson_path_byname
from myexecutor.BasePathExecutor2 import Point,BasePathExecutor

def show_points(points, width=1024, scale=None):
    if len(points) < 1:
        return

    region_img = get_points_img(points,width,scale=scale)
    # region_img = cv2.resize(region_img, None, fx=0.5, fy=0.5)
    from PIL import Image
    img = Image.fromarray(cv2.cvtColor(region_img, cv2.COLOR_BGR2RGB))
    img.show()
    # cv2.imshow('points', region_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

def get_points_img(points: List[Point], width=2048, user_position=None, scale=None):
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
    region_img = cv2.cvtColor(region_img, cv2.COLOR_GRAY2BGR)
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
        cv2.line(region_img, point_A, point_B, (255, 0,0), 1)
        # cv2.arrowedLine(region_img, point_B, point_A, (255, 0, 0), 1, tipLength=0.2)
        last_point = point

        if index == 0: # 起点设置为红色
            color = (0, 0, 255)  # 绿色，BGR格式
        # 画点（在指定坐标处绘制一个红色的点，大小为2）
        elif point.type == point.TYPE_TARGET:
            color = (0, 255, 0)  # 绿色，BGR格式
        elif point.type == Point.TYPE_PATH:
            color = (255, 0, 0)  # 蓝色，BGR格式
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
    region_img = get_points_img(points, width, pos, scale)
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
    # jsonfile = getjson_path_byname('甜甜花_蒙德_清泉镇_2024-08-08_15_42_55.json')
    # jsonfile = getjson_path_byname('调查_璃月_地中之岩_2024-04-29_06_23_28.json')
    # jsonfile = getjson_path_byname('月莲_须弥_降魔山下_6个.json')
    jsonfile = getjson_path_byname('月莲_test.json')
    # jsonfile = getjson('jiuguan_蒙德_test_scale2_20240808.json')
    # jsonfile = getjson_path_byname('jiuguan_蒙德_wfsd_20240808.json')
    # jsonfile = getjson_path_byname('jiuguan_枫丹_tiantianhua_20240808.json')
    # jsonfile = getjson_path_byname('甜甜花_枫丹_中央实验室遗址_test_2024-08-08_12_37_05.json')
    json_map = BasePathExecutor.load_json(jsonfile)
    show_points(json_map['positions'],  1024, scale=1)
    # show_points(json_map.get('positions'), json_map['name'],width=1200,scale=3)
    # while True:
        # time.sleep(0.1)
        # show_points_live(json_map.get('positions'), scale=1.5)
    #     show_points_live(path_list, object_to_detect=object_to_detect, width=1024)
