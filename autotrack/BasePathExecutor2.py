import random
import sys
import threading
import time
import json

import cv2

import numpy as np
from controller.BaseController import BaseController
from collections import deque
from controller.MapController2 import MapController
from controller.OCRController import OCRController
from capture.genshin_capture import GenShinCapture
from autotrack.utils import point1_near_by_point2
from myutils.timerutils import RateLimiter
from myutils.configutils import cfg, PROJECT_PATH

class MovingStuckException(Exception):
    pass

class MovingTimeOutException(Exception):
    pass

class BasePathExecutor(BaseController):
    # 到达下一个点位采取何种移动方式？
    # TODO 暂时飞行模式和跳跃模式做同样的狂按空格处理
    MOVE_TYPE_NORMAL = 'path'  # (默认)正常步行模式
    MOVE_TYPE_FLY = 'fly'  # 飞行模式
    MOVE_TYPE_JUMP = 'jump'  # 跳跃模式

    def __init__(self, gc=None, debug_enable=False, ocr=None, show_path_viewer=False):
        super().__init__(debug_enable=debug_enable)
        self.show_path_viewer = show_path_viewer
        if ocr is None: ocr = OCRController(debug_enable=debug_enable)
        self.ocr = ocr
        self.gc = gc

        # 状态
        self.current_position = None
        self.current_rotation = None  # 当前视角
        self.next_point = None
        self.is_path_end = False  # 是否到达终点
        self.near_by_threshold = 8  # A,B距离多少个像素点表示他们是临近
        self.near_by_threshold_small_step = 2  # 开启小碎步时，A,B判定距离是否接近的阈值

        self.move_next_point_allow_max_time = cfg.get('move_next_point_allow_max_time', 20)
        if self.move_next_point_allow_max_time < 5: self.move_next_point_allow_max_time = 5
        elif self.move_next_point_allow_max_time > 60: self.move_next_point_allow_max_time = 60

        self.object_to_detect = None  # 目标检测对象, 例如 钓鱼
        self.position_history = deque(maxlen=8)  # 一秒钟存1次，计算总距离
        self.stuck_movement_threshold = cfg.get('stuck_movement_threshold', 20)
        if self.stuck_movement_threshold < 2: self.stuck_movement_threshold = 2
        elif self.stuck_movement_threshold > 50: self.stuck_movement_threshold = 50

        self.path_viewer_width = cfg.get('path_viewer_width', 500)
        if self.path_viewer_width < 50: self.path_viewer_width = 50
        elif self.path_viewer_width > 4096: self.path_viewer_width = 4096

        self.allow_small_steps = cfg.get('allow_small_steps', 1) == 1
        self.enable_crazy_f = cfg.get('enable_crazy_f', 1) == 1
        self.enable_loop_press_e = cfg.get('enable_loop_press_e', 1) == 1
        self.enable_loop_press_z = cfg.get('enable_loop_press_z', 1) == 1
        self.enable_loop_jump = cfg.get('enable_loop_jump', 1) == 1
        self.enable_dash = cfg.get('enable_dash', 1) == 1

        self.rate_limiter_history = RateLimiter(1)  # 一秒钟之内只能执行一次

        self.last_update_time = time.time()
        self.UPDATE_POSITION_INTERVAL = 0.05  # 0.05s更新一次位置

        # 多线程
        self._thread_object_detect_finished = False  # 目标检测任务
        self._thread_update_state_finished = False  # 更新状态

        # 传送用
        self.map_controller = MapController(tracker=self.tracker, debug_enable=debug_enable)

        # 调试
        self.debug_enable = debug_enable
        self.rate_limiter = RateLimiter(5)  # 5秒内只能执行一次

    def _thread_object_detection(self):
        pass

    def debug(self, *args):
        if self.stop_listen: return
        self.logger.debug(args)

    def points_viewer(self, positions, name):
        from autotrack.KeyPointViewer import get_points_img_live
        #  当前路径结束后，应当退出循环，结束线程，以便于开启下一个线程展示新的路径
        self.log(f"准备展示路径, path_end={self.is_path_end}, stop_listen={self.stop_listen}")
        while not self.stop_listen and not self.is_path_end:
            if self.stop_listen or self.is_path_end: return
            time.sleep(0.3)
            if positions is not None and len(positions) > 0:
                img = get_points_img_live(positions, name, radius=self.path_viewer_width)
                if img is None: continue
                cv2.imshow('path viewer', img)
                cv2.moveWindow('path viewer', 10, 10)
                cv2.waitKey(1)
        cv2.destroyAllWindows()
        self.log("路径展示结束")

    def calculate_total_displacement(self):
        """
        计算多少秒内的总位移
        :return:
        """
        if len(self.position_history) < 7:
            return 100000000 # Not enough data to calculate displacement

        total_displacement = 0
        prev_pos = self.position_history[0]

        for curr_pos in self.position_history:
            displacement = ((curr_pos[0] - prev_pos[0]) ** 2 + (curr_pos[1] - prev_pos[1]) ** 2) ** 0.5
            total_displacement += displacement
            prev_pos = curr_pos

        return total_displacement

    def crazy_f(self):
        self.kb_press_and_release('f')

    def on_nearby(self, coordinates):
        self.logger.debug(f'接近点位{coordinates}了')
        if self.enable_crazy_f:
            self.debug('疯狂按下f')
            self.crazy_f()

    # 移动
    # 异常：原地踏步
    # 类型：途径点、调查点
    # 行为：跳跃, 飞行，小碎步
    # 拓展：自定义按键
    def move(self, coordinates, small_step_enable=False):
        if self.stop_listen: return
        point_start_time = time.time()

        # 是否接近下一个点位的距离阈值
        near_by_threshold = self.near_by_threshold
        if small_step_enable: near_by_threshold = self.near_by_threshold_small_step

        # 当接近目的地时，调整更小的阈值, 使得小碎步可以更精准走到目的地
        from myutils.timerutils import RateLimiter
        rate_limiter_debugprint = RateLimiter(1)

        rate_limiter_press_e = RateLimiter(1)
        rate_limiter_press_z = RateLimiter(1)
        rate_limiter_press_jump = RateLimiter(1)
        rate_limiter_press_dash = RateLimiter(1)

        running_small_step = False  # 当距离过远的时候，不需要小碎步行动
        while not point1_near_by_point2(self.current_position, coordinates, near_by_threshold):
            if self.stop_listen: return
            t = time.time()

            if self.enable_loop_press_z: rate_limiter_press_z.execute(self.kb_press_and_release, 'z')
            if self.enable_loop_press_e: rate_limiter_press_e.execute(self.kb_press_and_release, 'e')

            try:
                if time.time() - point_start_time >= self.move_next_point_allow_max_time:
                    raise MovingTimeOutException("跑点超时！")
                pos = self.current_position
                if not pos:
                    self.log("获取地址失败，正在等待刷新地址, 松开wsad")
                    self.kb_release('w')
                    self.kb_release('s')
                    self.kb_release('a')
                    self.kb_release('d')
                    time.sleep(1)
                    continue


                if point1_near_by_point2(pos, coordinates, self.near_by_threshold):
                    self.on_nearby(coordinates)
                    running_small_step = True

                self.rate_limiter_history.execute(self.position_history.append, self.current_position)
                # self.position_history.append(self.current_position)  # 记录历史路径
                total_displacement = self.calculate_total_displacement()  # 8秒内的位移
                if total_displacement < self.stuck_movement_threshold: raise MovingStuckException(f"8秒内位移平均值为{total_displacement}, 判定为卡住了！")

                rate_limiter_debugprint.execute(self.debug, f"执行{coordinates}点位,已用{time.time() - point_start_time}秒")
                rot = self.get_next_point_rotation(coordinates)
                if rot: self.to_degree(rot)

                if not point1_near_by_point2(self.current_position, coordinates, 20):
                    # TODO BUG: 执行间隔太短将不生效
                    if self.enable_dash: rate_limiter_press_dash.execute(self.mouse_right_click)
                    if self.enable_loop_jump: rate_limiter_press_jump.execute(self.kb_press_and_release, self.Key.space)

                self.kb_press("w")
                if small_step_enable and running_small_step and self.allow_small_steps:
                    time.sleep(0.05)
                    self.debug("小碎步松开w")
                    self.kb_release('w')
                    # self.kb_press_and_release('d')
                # time.sleep(0.02)

            except MovingStuckException as e:
                self.debug(e)
                self.kb_press_and_release('d')  # 避免卡住
                self.kb_press_and_release(self.Key.space)  # 避免卡住
                self.kb_press_and_release('a')  # 避免卡住
                self.kb_press_and_release(self.Key.space)  # 避免卡住
                self.kb_press("w")
            except MovingTimeOutException:
                self.logger.debug('点位执行超时, 跳过该点位')
                self.kb_press_and_release("x")  # 避免攀爬
                self.kb_press_and_release(self.Key.space)  # 避免卡住
                self.kb_press_and_release('s')  # 避免卡住
                self.kb_press_and_release('a')  # 避免卡住
                self.kb_press_and_release('d')  # 避免卡住
                self.kb_press_and_release('w')  # 避免卡住
                return

            self.logger.debug('cost time: ' + str(time.time()-t))
        self.kb_release('w')


    def on_move_after(self, point):
        self.log(f'到达点位{point}了')
        if self.enable_crazy_f:
            self.debug('疯狂按下f')
            self.crazy_f()

    def update_state(self):
        start = time.time()
        pos = self.tracker.get_position()
        if pos: self.current_position = pos
        rot = self.tracker.get_rotation()
        if rot: self.current_rotation = rot

        self.last_update_time = time.time()
        msg = f"更新状态: cost:{time.time() - start},next:{self.next_point}, current pos:{self.current_position}, rotation:{self.current_rotation},is_path_end:{self.is_path_end}, is_object_detected_end:{self._thread_object_detect_finished}"
        self.logger.debug(msg)
        # self.rate_limiter.execute(self.debug, msg)

    def get_next_point_rotation(self, next_point):
        from autotrack.utils import calculate_angle
        if self.current_position and next_point:
            nextp = (next_point[0], next_point[1])
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
            time.sleep(self.UPDATE_POSITION_INTERVAL)

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
                if self.stop_listen: return
                self.debug(f"当前位置{self.current_position}, 正在前往点位{point}")
                self.next_point = point
                if point['type'] == 'start':  # 传送
                    # self.map_controller.transform((point['x'], point['y']), point['country'], create_local_map_cache=True)

                    thread_object_detect = threading.Thread(target=self._thread_object_detection)
                    thread_object_detect.start()
                    # 开始更新位置
                    thread_update_state = threading.Thread(target=self._thread_update_state)
                    thread_update_state.start()

                    # 异常线程
                    thread_exception = threading.Thread(target=self._thread_exception_detect)
                    thread_exception.start()

                wait_times = 10
                while not self.current_position:
                    if self.stop_listen: return
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

                # TODO 计算下一个点位和当前点位距离，如果过于接近也开启小碎步模式
                small_step_enable = point['type'] == self.object_to_detect or point['type'] == 'end'
                self.move((point['x'], point['y']), small_step_enable)

                self.debug("已到达", point)
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
        self.log("线程已全部结束")

        # 重置状态
        self.reset_state()
        return True


def _execute_all():
    # p.path_execute(getjson('甜甜花_枫丹_中央实验室遗址_2024-07-31_07_01_37.json'))
    points_path = cfg.get('points_path', os.path.join(PROJECT_PATH,'resources', 'pathlist'))
    show_path_viewer = cfg.get('show_path_viewer', True)
    debug_enable = cfg.get('debug_enable', True)
    p = BasePathExecutor(debug_enable=debug_enable, show_path_viewer=show_path_viewer)
    if not os.path.exists(points_path):
        p.logger.error('路径不存在！')
        return
    filenames = os.listdir(points_path)
    try:
        for filename in filenames:
            p.path_execute(os.path.join(points_path, filename))
    except Exception as e:
        p.logger.error(f'发生错误: {e}')
    finally:
        print("全部执行完成，按下m")
        p.kb_press_and_release("m")
        # print("30秒后进入睡眠")
        # time.sleep(30)

def getjson(filename):
    # 获取当前脚本所在的目录
    target = filename.split("_")[0]
    relative_path = f"pathlist/{target}"
    # 拼接资源目录的路径
    file = os.path.join(relative_path, filename)
    return file

if __name__ == '__main__':
    # 测试点位
    import json, os
    # p = BasePathExecutor(debug_enable=True, show_path_viewer=True)
    # p.path_execute(getjson('甜甜花_蒙德_清泉镇_2024-07-31_07_30_39.json'))
    # p.path_execute(getjson('甜甜花_蒙德_清泉镇_2024-07-31_07_30_39.json'))
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
    _execute_all()
