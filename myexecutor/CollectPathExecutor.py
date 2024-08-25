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
    MOVE_MODE_CIRCLE_GRAB_LEAF = "circle_grab_leaf"  # 视角水平转圈抓四叶印

    def __init__(self, x,y,type=None, action=None,move_mode=Point.MOVE_MODE_NORMAL, nahida_collect=False, crazy_f=False):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        self.nahida_collect = nahida_collect
        self.crazy_f = crazy_f

class CollectPath(BasePath): pass

class CollectPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path,debug_enable):
        super().__init__(json_file_path=json_file_path,debug_enable=debug_enable)

        # TODO 这里父类已经定义过了，子类再写一遍原因是希望IDE给点类型提示。后续希望改成泛型
        self.next_point: CollectPoint = None
        self.prev_point: CollectPoint = None

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

        # 尝试恢复视角
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 500, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 500, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 500, 0, 0)

    def grab_leaf(self):
        """
        四叶印
        :return:
        """
        self.log("按下t抓四叶印")
        self.kb_press_and_release('t')

    def circle_grab_leaf(self):
        while self.gc.is_flying(): time.sleep(0.5)
        time.sleep(0.5)
        self.log("开始转圈抓四叶印")
        x, y = 200, 0
        i = 50
        while i > 0 and not self.stop_listen:
            self.grab_leaf()
            i -= 1
            self.logger.debug("转圈中")
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, 0, 0, 0)
            time.sleep(0.04)


    def up_down_grab_leaf(self):
        time.sleep(0.5)
        self.log("开始上下晃动视角抓四叶印")
        x, y = 0, -1000  # y代表垂直方向上的视角移动, x为水平方向
        i = 40
        self.kb_press('w')  # 继续飞行
        while i > 0 and not self.stop_listen:
            self.grab_leaf()
            if i % 10 == 0:
                y = -y
            i -= 1
            self.logger.debug("上下晃动视角中")
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, y, 0, 0)
            time.sleep(0.04)


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
        elif point.move_mode == CollectPoint.MOVE_MODE_CIRCLE_GRAB_LEAF:
            self.logger.debug("转圈抓叶子！")
            self.circle_grab_leaf()



    def on_move_after(self, point: CollectPoint):
        if point.nahida_collect:
            self.logger.info('草神转圈')
            self.nahida_collect()
        elif point.crazy_f or self.enable_crazy_f:
            self.logger.info('已经到达点位也要疯狂按f')
            self.crazy_f()

if __name__ == '__main__':
    # 测试点位
    # j = getjson_path_byname('慕风蘑菇_清泉镇_蒙德_5个_20240824_175238.json')
    j = getjson_path_byname('树王圣体菇_无郁稠林_蘑菇平台_蒙德_3个_20240825_224137.json')
    p = CollectPathExecutor(j, debug_enable=True)
    # print(type(p.next_point))
    # from_idx = len(p.base_path.positions) - 3
    from_idx = None
    p.execute(from_index=from_idx)
