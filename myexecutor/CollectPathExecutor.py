import math
import random
import sys
import threading
import time
import json

import cv2
import win32api, win32con
import numpy as np

from controller.FightController import CharacterDieException
from myexecutor.BasePathExecutor2 import BasePathExecutor, Point, BasePath, ExecuteTerminateException
from myutils.fileutils import getjson_path_byname
from typing import List

# TODO
# 结尾经常容易漏捡
# 情况1：树王菇蘑菇平台移动速度过快，到达的时候已经break，可能无法继续执行生命周期的on_nearby方法拾取植物
# 情况2：判断目的地是否到达是以判定多少像素接近时计算的。大部分情况下接近目标点的时候，break掉，而物品都在前面，此时on_nearby也失效

class CollectPoint(Point):

    MOVE_MODE_UP_DOWN_GRAB_LEAF = 'up_down_grab_leaf'  # 视角上下晃动抓四叶印
    ACTION_NAHIDA_COLLECT = 'nahida_collect'

    def __init__(self, x,y,type=None, action=None,move_mode=Point.MOVE_MODE_NORMAL, nahida_collect=False, crazy_f=False):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        # self.nahida_collect = nahida_collect
        # self.crazy_f = crazy_f

class CollectPath(BasePath): pass

class CollectPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path,debug_enable=None):
        super().__init__(json_file_path=json_file_path,debug_enable=debug_enable)

        # TODO 这里父类已经定义过了，子类再写一遍原因是希望IDE给点类型提示。后续希望改成泛型
        self.next_point: CollectPoint = None
        self.prev_point: CollectPoint = None

        # 因为纳西妲长e最多扫6个采集物，所以有些地方可能要连续扫2次，此类情况要等待cd。这里记录上一次扫码结束时间
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
                                 # nahida_collect=point.get('nahida_collect'),
                                 # crazy_f=point.get('crazy_f')
                                 )
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
        from controller.FightController import SwitchCharacterTimeOutException, CharacterNotFoundException
        try:
            self.fight_controller.switch_character('纳西妲')
        except CharacterDieException as e:
            self.logger.error(e.args)
            self.logger.debug("纳西妲死亡，无法继续采集，回七天神像")
            from controller.MapController2 import MapController
            MapController().go_to_seven_anemo_for_revive()
            raise ExecuteTerminateException()
        except (SwitchCharacterTimeOutException, CharacterNotFoundException) as e:
            self.logger.error(e.args)
            return

        # 等待e技能冷却
        cd = time.time() - self.nahida_collect_last_time
        if cd < 6:  # 纳西妲长e冷却时长
            time.sleep(6-cd+0.5)

        # 下落攻击的时候会有一小段时间处于飞行状态，此时禁止扫码，等待飞行状态结束后才允许
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
        self.view_reset()

    def view_reset(self):
        """
        恢复视角:游戏特性，按下鼠标中间视角会恢复到正中间
        :return:
        """
        self.ms_middle_press()
        self.ms_middle_release()

    def grab_leaf(self):
        """
        抓四叶印
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

        self.view_reset()


    def on_nearby(self, coordinate):
        # super().on_nearby(coordinate)
        self.logger.debug(f'接近点位{self.next_point}了')
        if self.enable_crazy_f:
            self.logger.debug(f'疯狂按下f')
            self.crazy_f()

    def on_move_before(self, point: CollectPoint):
        if point.move_mode == CollectPoint.MOVE_MODE_UP_DOWN_GRAB_LEAF:
            self.logger.debug("上下晃动视角抓四叶印！")
            self.up_down_grab_leaf()

    def shield(self):
        try:
            self.fight_controller.shield()
        except CharacterDieException as e:
            # self.logger.error(e.args)
            self.logger.debug("虽然盾辅角色死亡了，但是不需要战斗，不影响采集, 继续行动")


    def on_move_after(self, point: CollectPoint):
        super().on_move_after(point)
        if point.action == CollectPoint.ACTION_NAHIDA_COLLECT:
            self.logger.info('草神转圈')
            self.nahida_collect()
        if self.next_point.move_mode == CollectPoint.MOVE_MODE_UP_DOWN_GRAB_LEAF and self.next_point.type == CollectPoint.TYPE_TARGET:
            time.sleep(0.3)  # 通过四叶印到达目的地会有一小段时间悬空，等待降下，否则无法拾取


if __name__ == '__main__':
    # 测试点位
    # CollectPathExecutor(getjson_path_byname('慕风蘑菇_清泉镇_蒙德_5个_20240824_175238.json')).execute()
    # CollectPathExecutor(getjson_path_byname('慕风蘑菇_清泉镇2_蒙德_1个_20240824_162230.json')).execute()
    CollectPathExecutor(getjson_path_byname('月莲_桓那兰那_须弥_4个_20240814_114304.json')).execute()

    # print(type(p.next_point))
    # from_idx = len(p.base_path.positions) - 3
    # from_idx = None
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_右下角蘑菇平台_须弥_6个_20240826_054526.json')).execute()
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_右下角地面_须弥_6个_20240826_052134.json')).execute()

    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_左上角蘑菇平台_须弥_2个_20240826_030148.json')).execute()
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_左上角地面_须弥_5个_20240826_055815.json')).execute()
    # CollectPathExecutor(getjson_path_byname('树王圣体菇_无郁稠林_左上角丘丘人寨子附近_须弥_1个_20240826_055107.json')).execute()
