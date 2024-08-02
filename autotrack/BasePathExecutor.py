import random
import sys
import threading
import time
import json

import cv2

import numpy as np
from controller.BaseController import BaseController
from controller.MapController import MapController
from controller.OCRController import OCRController
from capture.genshin_capture import GenShinCapture
from autotrack.utils import point1_near_by_point2


class BasePathExecutor(BaseController):
    # 到达下一个点位采取何种移动方式？
    # TODO 暂时飞行模式和跳跃模式做同样的狂按空格处理
    MOVE_TYPE_NORMAL = 'path'  # (默认)正常步行模式
    MOVE_TYPE_FLY = 'fly'  # 飞行模式
    MOVE_TYPE_JUMP = 'jump'  # 跳跃模式

    def __init__(self, gc=None, debug_enable=False, ocr=None, show_path_viewer=False):
        super().__init__(debug_enable=debug_enable)
        self.show_path_viewer = show_path_viewer
        if gc is None: gc = GenShinCapture
        if ocr is None: ocr = OCRController(debug_enable=debug_enable)
        self.ocr = ocr
        self.gc = gc

        # 调试
        self.debug_enable = debug_enable

        # 状态
        self.current_position = None
        self.current_rotation = None  # 当前视角
        self.next_point = None
        self.is_path_end = False  # 是否到达终点
        self.near_by_threshold = 10  # A,B距离多少个像素点表示他们是临近
        self.near_by_threshold_small_step = 2  # 目标点
        self.object_to_detect = None  # 目标检测对象, 例如 钓鱼

        self.last_update_time = time.time()
        self.LAST_UPDATE_TIME_INTERVAL = 0.05  # 0.05s更新一次位置

        # 多线程
        self._thread_object_detect_finished = False  # 目标检测任务
        self._thread_update_state_finished = False  # 更新状态

        # 传送用
        self.map_controller = MapController(tracker=self.tracker, debug_enable=debug_enable)

    def _thread_object_detection(self):
        pass

    def points_viewer(self, positions, name):
        from autotrack.KeyPointViewer import get_points_img_live
        #  当前路径结束后，应当退出循环，结束线程，以便于开启下一个线程展示新的路径
        self.log(f"准备展示路径, path_end={self.is_path_end}, stop_listen={self.stop_listen}")
        while not self.stop_listen and not self.is_path_end:
            time.sleep(0.5)
            if positions is not None and len(positions) > 0:
                img = get_points_img_live(positions, name, radius=800)
                if img is None: continue
                cv2.imshow('path viewer', img)
                cv2.moveWindow('path viewer', 10, 10)
                cv2.waitKey(1)
        cv2.destroyAllWindows()
        self.log("路径展示结束")

    def move(self, point):
        if self.stop_listen: return

        self.next_point = point
        # 视角调整到北部
        # pass
        # 根据当前位置与下一个点位的差值决定按下w,s,a,d四个方向键
        # 例如，当前位置是(0,0), 下一个点位是(100,-500)
        # 对于x轴方向，计算100-0 = 100 > 0，表示应该向右边走, 则按下d
        # 对于y轴方向, 计算-500-0 = -500 < 0，表示应该向上边走，则按下w
        small_step_enable = False
        jump_mode_enable = False
        fly_mode_enable = False
        #  TODO：抽象出行为接口，为不同的行为编写不同的行动方式。
        if point.get('type') == self.object_to_detect or point.get('type') == 'end':
            # 小碎步模式
            self.log("开启小碎步模式")
            small_step_enable = True
        elif point.get('type') == self.MOVE_TYPE_JUMP:
            jump_mode_enable = True
        elif point.get('type') == self.MOVE_TYPE_FLY:
            fly_mode_enable = True

        point_start_time = time.time()
        MAX_ALLOW_STEP_TIME = 30
        last_step_position = self.current_position
        LAST_STEP_UPDATE_INTERVAL = 8 # 8秒缓存一次上次的位置

        # 防止原地踏步的标志
        same_step_counter = 0  # 和上一次卡住的位移做差，距离过小则+1
        same_step_small_step_threshold = 2
        same_step_normal_step_threshold = 10
        same_step_timer_start = time.time()

        # 是否接近目的地的标记
        near_by_threshold = self.near_by_threshold
        # 当接近目的地时，调整更小的阈值, 使得小碎步可以更精准走到目的地
        near_by_threshold_small_step = self.near_by_threshold_small_step

        while not self.stop_listen:

            while not self.pos and not self.stop_listen:
                self.log("获取地址失败，正在等待刷新地址, 松开wsad")
                self.kb_release('w')
                self.kb_release('s')
                self.kb_release('a')
                self.kb_release('d')
                time.sleep(2)

            # 调查类型和结束点位采取小碎步模式
            if point['type'] == self.object_to_detect or point['type'] == 'end':
                if point1_near_by_point2((point['x'], point['y']), self.current_position, near_by_threshold):
                    self.log(f"距离小于{near_by_threshold}已经接近{point}, 开启小碎步模式")
                    if not small_step_enable:
                        same_step_counter = 0
                    small_step_enable = True
                else:
                    small_step_enable = False

            elif fly_mode_enable:
                self.kb_press_and_release(self.Key.space)
            elif jump_mode_enable:
                self.kb_press_and_release(self.Key.space)

            used_time = time.time() - point_start_time
            left_time = MAX_ALLOW_STEP_TIME - used_time
            if time.time() - same_step_timer_start > LAST_STEP_UPDATE_INTERVAL:
                last_step_position = self.current_position  # 8秒更新一次位置
                self.log(f"更新位置：{last_step_position}")
                same_step_timer_start = time.time()

            # 防止走过界
            if small_step_enable:
                # 小碎步判定是否走过界的方式
                time.sleep(0.1)
                self.log("小碎步松开wsad")
                self.kb_release('w')
                if point1_near_by_point2(last_step_position, self.current_position, same_step_small_step_threshold):
                    self.log(f"小碎步{LAST_STEP_UPDATE_INTERVAL}s前{last_step_position}, 现在{self.current_position}, 计数器{same_step_counter}")
                    same_step_counter += 1
                else:
                    same_step_counter = 0
            else:
                # 非小碎步判定是否原地踏步的方式
                if point1_near_by_point2(last_step_position, self.current_position, same_step_normal_step_threshold):
                    self.log(f"{LAST_STEP_UPDATE_INTERVAL}s前{last_step_position}, 现在{self.current_position}, 计数器{same_step_counter}")
                    same_step_counter += 1
                else:
                    same_step_counter = 0

            self.log(f"执行{point}点位已用{used_time}秒,剩余{left_time}秒")
            if left_time < 0:
                self.log(f"未在规定时间内到达{self.next_point},当前在{self.current_position}, 跳过{self.next_point}")
                self.kb_press_and_release("x")  # 避免攀爬
                self.kb_press_and_release(self.Key.space)  # 避免卡住
                self.kb_press_and_release('s')  # 避免卡住
                self.kb_press_and_release('a')  # 避免卡住
                self.kb_press_and_release('d')  # 避免卡住
                self.kb_press_and_release('w')  # 避免卡住
                break
            # 防止卡住
            # 如果5秒内的步位移过小，则尝试不断跳跃
            # 每走一步就和上一次卡住的位置做计算，如果距离过小则计数器+1, 否则设置为0
            # 当计数器大于10，也就是连续10次距离位移过小, 而且超过10秒，则认为卡住了

            if used_time > LAST_STEP_UPDATE_INTERVAL and same_step_counter > 10:
                self.log("你似乎原地打转了，开始跳跃!")
                self.kb_press_and_release('d')  # 避免卡住
                self.kb_press_and_release(self.Key.space)  # 避免卡住
                self.kb_press_and_release('a')  # 避免卡住
                self.kb_press_and_release(self.Key.space)  # 避免卡住
                same_step_counter = 0

            rot = self.get_next_point_rotation(point)
            if rot:
                # self.log(f"计算下一个点位角度为{rot}")
                self.to_degree(rot)
            else:
                pass
                # self.log("无法计算下一个点位的角度")

            self.kb_press("w")
            self.log(f"same step counter{same_step_counter}")

            # dist = math.sqrt(delta_x ** 2 + delta_y ** 2)
            # 如果当前距离还很远，则正常行走
            if point['type'] != self.object_to_detect and point1_near_by_point2((point['x'], point['y']),
                                                                                self.current_position,
                                                                                near_by_threshold):
                self.log(f"距离小于{near_by_threshold_small_step},  认为接近{point}, 松开w")
                self.kb_release("w")
                break
            # 如果当前距离已经快接近，则小步骤靠近以防止走过头而转圈
            if point1_near_by_point2((point['x'], point['y']), self.current_position, near_by_threshold_small_step):
                self.log(f"距离小于{near_by_threshold_small_step},  认为到达{point}, 松开w")
                self.kb_release("w")
                break

    def on_move_after(self, point):
        """
        生命周期方法
        :param point:
        :return:
        """
        pass

    def update_state(self):
        start = time.time()
        if not time.time() - self.last_update_time > self.LAST_UPDATE_TIME_INTERVAL:
            return
        pos = self.tracker.get_position()
        self.pos = pos
        if self.pos:
            # 仅保存正确的位置
            self.current_position = (pos[0], pos[1])  # 当前点位
        rotation = self.tracker.get_rotation()
        if rotation:
            self.current_rotation = rotation

        self.last_update_time = time.time()
        # self.log(f"更新状态: cost:{time.time() - start},next:{self.next_point}, current pos:{self.current_position}, rotation:{self.current_rotation},is_path_end:{self.is_path_end}, is_object_detected_end:{self._thread_object_detect_finished}")

    def get_next_point_rotation(self, next_point):
        from autotrack.utils import calculate_angle
        if self.current_position and next_point:
            nextp = (next_point['x'], next_point['y'])
            x0, y0 = self.current_position[0], self.current_position[1]
            deg = calculate_angle(x0, y0, nextp[0], nextp[1])
            # self.log(f"计算角度 ,当前:{self.current_position}, next{nextp}, 结果{deg}")
            return deg

    def reset_state(self):
        self.current_position = None
        self.current_rotation = None  # 当前视角
        self.next_point = None
        self.is_path_end = False  # 是否到达终点
        self.near_by_threshold = 8  # A,B距离多少个像素点表示他们是临近
        self.object_to_detect = None  # 目标检测对象, 例如 钓鱼

        # 多线程
        self._thread_object_detect_finished = False  # 目标检测任务
        self._thread_update_state_finished = False  # 更新状态

    def _thread_update_state(self):
        while not self.is_path_end and not self.stop_listen and not self._thread_update_state_finished:
            # self.log(f"多线程更新状态中, {self.stop_listen}")
            self.update_state()

    def _thread_exception_detect(self):
        pass

    def path_execute(self, path):
        self.log("开始执行{}".format(path))
        self.reset_state()

        with open(path, encoding="utf-8") as r:
            json_obj = json.load(r)
            self.object_to_detect = json_obj["name"]
            self.log(f"当前采集任务:{self.object_to_detect}")
            path_list = json_obj['positions']
            if len(path_list) < 1:
                self.log(f"空白路线, 跳过")
                return
            if path_list[0].get('type') != 'start':
                self.log(f"第一个点位必须是start,跳过该路线")
                return

            thread_path_viewer = threading.Thread(target=self.points_viewer, args=(path_list, self.object_to_detect))
            if self.show_path_viewer:
                thread_path_viewer.start()

            for point in path_list:
                self.log(f"当前位置{self.current_position}, 正在前往点位{point}")
                self.next_point = point
                if point['type'] == 'start':  # 传送
                    self.map_controller.transform((point['x'], point['y']), point['country'], create_local_map_cache=True)

                    thread_object_detect = threading.Thread(target=self._thread_object_detection)
                    thread_object_detect.start()
                    # 开始更新位置
                    thread_update_state = threading.Thread(target=self._thread_update_state)
                    thread_update_state.start()

                    # 异常线程
                    thread_exception = threading.Thread(target=self._thread_exception_detect)
                    thread_exception.start()

                wait_times = 10
                while not self.current_position and not self.stop_listen:
                    wait_times -= 1
                    self.log(f"当前位置为不明，正在第{10 - wait_times}次循环等待中")
                    if wait_times < 0:
                        self.log(f"等待时间过长，跳过该点位{point}")
                        break
                    time.sleep(1)
                if not self.current_position: continue  # 上面的while循环未能成功加载位置，跳到下一个点位

                if not point1_near_by_point2(self.current_position,
                                             (point['x'], point['y']), 500):
                    # 如果当前点位距离下一个点位过远，可能是由于角色死亡被传送
                    self.log("当前点位距离下一个点位过远，可能是由于角色死亡被传送, 提前终止{}".format(path))
                    # 重置状态
                    self.reset_state()
                    return False

                # if point['type'] == 'path':
                self.move(point)
                # else:
                #     self.to_degree(0)
                #     self.set_lock_view(True)
                #     self.move_lock_view(point)

                self.log("已到达", point)
                self.on_move_after(point)

                if point['type'] == "end":
                    self.log("已经走到终点")
                    self.is_path_end = True

        self.log("文件{}执行完毕".format(path))

        self.is_path_end = True

        # 等待线程结束
        thread_object_detect.join()
        thread_update_state.join()
        thread_exception.join()
        if self.show_path_viewer:
            thread_path_viewer.join()
        self.log("锁定线程和物品检测线程已结束")

        # 重置状态
        self.reset_state()
        return True


def getjson(filename):
    # 获取当前脚本所在的目录
    current_file_path = os.path.dirname(__file__)
    target = filename.split("_")[0]
    relative_path = f"pathlist/{target}"
    # 拼接资源目录的路径
    file = os.path.join(relative_path, filename)
    return file


if __name__ == '__main__':
    # 测试点位
    import json, os

    p = BasePathExecutor(debug_enable=True, show_path_viewer=True)
    p.path_execute(getjson('调查_璃月_测试2_2024-07-30_06_09_55.json'))
    # p.path_execute(getjson("钓鱼_蒙德_低语森林_2024-04-26_15_11_25.json"))
    # p.path_execute(getjson("2024-04-22_15_09_28_蒙德_fish_mengde_qinquanzhen.json"))
    # p.path_execute(getjson("2024-04-22_23_30_42_蒙德_fish_mengde_chenxijiuzhuang.json"))  # 钓鱼点有冰史莱姆
    # p.path_execute(getjson("2024-04-23_10_14_34_璃月_fish_liyue_guiliyuan.json"))  # 可能会不小心上桥
    # p.path_execute(getjson("2024-04-23_14_18_25_璃月_fish_liyue-luhuachi.json")) #bad
    # while not p.path_execute(getjson("2024-04-23_15_06_07_璃月_fish_liyue_liyuegang.json")): pass
    # while not p.path_execute(getjson("2024-04-25_07_28_31_璃月_fish_liyue_liyuegang.json")): print( "没有执行成功，再次执行！！")  # alhpa 翻车
    # while not p.path_execute(getjson("2024-04-23_23_45_06_稻妻_fish_daoqi_mingzhuitan.json")): print( "没有执行成功，再次执行！！")
    # p.path_execute(getjson("2024-04-24_00_20_44_稻妻_fish_daoqi_yueshicun.json"))
    # p.path_execute(getjson("2024-04-25_02_13_52_稻妻_fish_daoqi_yueshicun2.json"))
    # p.path_execute(getjson("染之庭_稻妻_无想刃狭间_2024-04-27_06_16_04.json"))

    # // TODO 在终点把视角调整到正确的位置
