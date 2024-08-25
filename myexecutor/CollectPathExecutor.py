import math
import random
import sys
import threading
import time
import json

import cv2
import win32api, win32con
import numpy as np
from myexecutor.BasePathExecutor2 import BasePathExecutor, Point, BasePath
from myutils.jsonutils import getjson_path_byname
from typing import List

class CollectPoint(Point):

    MOVE_MODE_UP_DOWN_GRAB_LEAF = 'up_down_grab_leaf'  # 视角上下晃动抓四叶印

    def __init__(self, x,y,type=None, action=None,move_mode=Point.MOVE_MODE_NORMAL, nahida_collect=False, crazy_f=False):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        self.nahida_collect = nahida_collect
        self.crazy_f = crazy_f

class CollectPath(BasePath): pass

class CollectPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path,debug_enable=None):
        super().__init__(json_file_path=json_file_path,debug_enable=debug_enable)

        # TODO 这里父类已经定义过了，子类再写一遍原因是希望IDE给点类型提示。后续希望改成泛型
        self.next_point: CollectPoint = None
        self.prev_point: CollectPoint = None

        # 因为纳西妲长e最多扫6个采集物，因此有些地方可能要连续扫2次，因此要等待cd, 这里记录上一次扫码结束时间
        self.nahida_collect_last_time = 0

    @staticmethod
    def load_basepath_from_json_file(json_file_path) -> CollectPath:
        with open(json_file_path, encoding="utf-8") as r:
            json_dict = json.load(r)
            points: List[CollectPoint] = []
            for point in json_dict.get('positions', []):
                p = CollectPoint(x=point.get('x'),
                                 y=point.get('y'),
                                 type=point.get('type', Point.TYPE_PATH),
                                 move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                                 action=point.get('action'),
                                 nahida_collect=point.get('nahida_collect'),
                                 crazy_f=point.get('crazy_f'))
                points.append(p)
            return CollectPath(name=json_dict.get('name', 'undefined'),
                            country=json_dict.get('country','蒙德'),
                            positions=points,
                            anchor_name=json_dict.get('anchor_name', '传送锚点'))
    def view_down(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 20000, 0, 0)
        time.sleep(0.01)
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 20000, 0, 0)

    def nahida_collect(self):
        # 等待cd
        cd = time.time() - self.nahida_collect_last_time
        if cd < 6:  # 纳西妲长e冷却时长
            time.sleep(6-cd+0.5)

        # 防止下落攻击时没点到
        while self.gc.is_flying(): time.sleep(0.5)
        time.sleep(0.5)
        self.log("开始转圈")
        x, y = 200, 0
        i = 140
        self.view_down()  # 视角拉到最下面
        self.kb_press("e")
        while i > 0 and not self.stop_listen:
            i -= 1
            print("转圈中")
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, -30, 0, 0)
            time.sleep(0.04)
        self.kb_release("e")
        self.nahida_collect_last_time = time.time()

        # 尝试恢复视角
        self.restore_view()

    def restore_view(self):
        """
        恢复视角:游戏特性，按下鼠标中间视角会恢复到正中间
        :return:
        """
        self.ms_middle_press()
        self.ms_middle_release()

    def grab_leaf(self):
        """
        四叶印
        :return:
        """
        self.log("按下t抓四叶印")
        self.kb_press_and_release('t')


    def up_down_grab_leaf(self):
        time.sleep(0.5)
        self.log("开始上下晃动视角抓四叶印")
        x, y = 0, -1000  # y代表垂直方向上的视角移动, x为水平方向
        i = 40
        # self.kb_press('w')  # 飞行
        while i > 0 and not self.stop_listen:
            self.grab_leaf()
            if i % 10 == 0:
                y = -y
            i -= 1
            self.logger.debug("上下晃动视角中")
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, y, 0, 0)
            time.sleep(0.04)

        self.restore_view()


    def on_nearby(self, coordinate):
        # super().on_nearby(coordinate)
        self.logger.debug(f'接近点位{self.next_point}了')
        if self.enable_crazy_f or self.next_point.crazy_f:
            self.logger.debug(f'疯狂按下f')
            self.crazy_f()

    def on_move_before(self, point: CollectPoint):
        if point.move_mode == CollectPoint.MOVE_MODE_UP_DOWN_GRAB_LEAF:
            self.logger.debug("上下视角抓叶子！")
            self.up_down_grab_leaf()


    def on_move_after(self, point: CollectPoint):
        if point.nahida_collect:
            self.logger.info('草神转圈')
            self.nahida_collect()
        elif point.crazy_f or self.enable_crazy_f:
            self.logger.info('已经到达点位也要疯狂按f')
            self.crazy_f()
if __name__ == '__main__':
    # 测试点位
    # CollectPathExecutor(getjson_path_byname('慕风蘑菇_清泉镇_蒙德_5个_20240824_175238.json')).execute()
    CollectPathExecutor(getjson_path_byname('慕风蘑菇_清泉镇2_蒙德_1个_20240824_162230.json')).execute()

    # print(type(p.next_point))
    # from_idx = len(p.base_path.positions) - 3
    from_idx = None
    # TODO : 拉四叶印后，应当等待人物落地才开始出发，否则可能拿不到材料
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_右下角_须弥_6个_20240825_220239.json')).execute(from_index=from_idx)
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_左上角蘑菇平台_须弥_2个_20240826_030148.json')).execute()
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_左上角地面_须弥_5个_20240826_022440.json')).execute(from_index=from_idx)
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_左上角丘丘人寨子附近_须弥_1个_20240826_031635.json')).execute()
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_右下角蘑菇平台_须弥_6个_20240826_011946.json')).execute()
