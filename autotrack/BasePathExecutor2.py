import random
import sys
import threading
import time
import cv2
import json
import logging
import numpy as np
from controller.BaseController import BaseController
from collections import deque
from controller.MapController2 import MapController
from controller.OCRController import OCRController
from capture.genshin_capture import GenShinCapture
from autotrack.utils import point1_near_by_point2
from myutils.configutils import cfg, PROJECT_PATH
from myutils.timerutils import RateLimiter
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('path_executor')

class MovingStuckException(Exception):
    pass

class MovingTimeOutException(Exception):
    pass


class Point:
    TYPE_START = 'start'
    TYPE_PATH = 'path'
    TYPE_TARGET = 'target'
    TYPE_END = 'end'

    def __init__(self, x, y, type=TYPE_PATH, action=None):
        self.x = x
        self.y = y
        self.type = type
        self.target_name = None
        self.action = action

from typing import List
class PathWrapper:
    def raise_error(self, msg):
        logger.error(msg)
        raise Exception(msg)
    def __init__(self, jsonfile):
        with open(jsonfile, encoding="utf-8") as r:
            json_obj = json.load(r)
            target_name = json_obj.get('name')
            positions = json_obj.get('positions')

        if positions is None or len(positions) < 1:
            self.raise_error(f"空白路线, 跳过")

        self.absolute_path = jsonfile
        # 冗余信息
        if positions[0].get('type') != "start":
            self.raise_error(f"第一个点位必须是start")

        self.points: List[Point] = []
        self.country = positions[0].get('country')
        self.target_name = target_name
        for point in positions:
            p = Point(x=point.get('x'), y=point.get('y'), type=point.get('type'))
            self.points.append(p)

class BasePathExecutor(BaseController):

    # 到达下一个点位采取何种移动方式？
    # TODO 暂时飞行模式和跳跃模式做同样的狂按空格处理
    MOVE_TYPE_NORMAL = 'path'  # (默认)正常步行模式
    MOVE_TYPE_FLY = 'fly'  # 飞行模式
    MOVE_TYPE_JUMP = 'jump'  # 跳跃模式

    def __init__(self, path: PathWrapper, debug_enable=False):
        super().__init__(debug_enable=debug_enable)
        self.ocr = OCRController(debug_enable=debug_enable)
        # 传送用
        self.map_controller = MapController(tracker=self.tracker, debug_enable=debug_enable)
        self.debug_enable = debug_enable
        self.path_obj = path

        ################## 参数 #########################
        self.move_next_point_allow_max_time = cfg.get('move_next_point_allow_max_time', 20)
        if self.move_next_point_allow_max_time < 5:
            self.move_next_point_allow_max_time = 5
        elif self.move_next_point_allow_max_time > 60:
            self.move_next_point_allow_max_time = 60

        self.object_to_detect = None  # 目标检测对象, 例如 钓鱼
        self.position_history = deque(maxlen=8)  # 一秒钟存1次，计算总距离
        self.stuck_movement_threshold = cfg.get('stuck_movement_threshold', 20)
        if self.stuck_movement_threshold < 2:
            self.stuck_movement_threshold = 2
        elif self.stuck_movement_threshold > 50:
            self.stuck_movement_threshold = 50

        # 精度：当前位置距离目标点距离多少个像素点表示他们是临近, 小碎步时候要用到
        self.target_nearby_threshold = cfg.get('target_nearby_threshold', 2)
        if self.target_nearby_threshold < 0.1: self.target_nearby_threshold = 0.1
        if self.target_nearby_threshold > 10: self.target_nearby_threshold = 10

        self.path_point_nearby_threshold = cfg.get('path_point_nearby_threshold', 2)
        if self.path_point_nearby_threshold < 2: self.path_point_nearby_threshold = 2
        if self.path_point_nearby_threshold > 50: self.path_point_nearby_threshold = 50

        self.path_viewer_width = cfg.get('path_viewer_width', 500)
        if self.path_viewer_width < 50:
            self.path_viewer_width = 50
        elif self.path_viewer_width > 4096:
            self.path_viewer_width = 4096

        self.allow_small_steps = cfg.get('allow_small_steps', 1) == 1
        self.enable_crazy_f = cfg.get('enable_crazy_f', 1) == 1
        self.enable_loop_press_e = cfg.get('enable_loop_press_e', 1) == 1
        self.enable_loop_press_z = cfg.get('enable_loop_press_z', 1) == 1
        self.enable_loop_jump = cfg.get('enable_loop_jump', 1) == 1
        self.enable_dash = cfg.get('enable_dash', 1) == 1

        self.last_update_time = time.time()
        self.UPDATE_POSITION_INTERVAL = 0.05  # 0.05s更新一次位置

        ############ 状态 ##############
        self.current_position = None
        self.current_rotation = None  # 当前视角
        self.next_point = None
        self.prev_point = None
        self.is_path_end = False  # 是否到达终点
        # 多线程
        self._thread_object_detect_finished = False  # 目标检测任务
        self._thread_update_state_finished = False  # 更新状态

        ######## 其他 #######
        self.rate_limiter1_history = RateLimiter(1)  # 一秒钟之内只能执行一次
        self.rate_limiter5_debug_print = RateLimiter(5)  # 5秒内只能执行一次


    def _thread_object_detection(self):
        pass

    def debug(self, *args):
        if self.stop_listen: return
        self.logger.debug(args)

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
        if small_step_enable: near_by_threshold = self.target_nearby_threshold
        else: near_by_threshold = self.path_point_nearby_threshold

        # 当接近目的地时，调整更小的阈值, 使得小碎步可以更精准走到目的地
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

                if point1_near_by_point2(pos, coordinates, self.path_point_nearby_threshold):
                    self.on_nearby(coordinates)
                    running_small_step = True

                self.rate_limiter1_history.execute(self.position_history.append, self.current_position)
                # self.position_history.append(self.current_position)  # 记录历史路径
                total_displacement = self.calculate_total_displacement()  # 8秒内的位移
                if total_displacement < self.stuck_movement_threshold: raise MovingStuckException(f"8秒内位移平均值为{total_displacement}, 判定为卡住了！")

                rate_limiter_debugprint.execute(self.debug, f"执行{coordinates}点位,已用{time.time() - point_start_time}秒")
                rot = self.get_next_point_rotation(coordinates)
                if rot: self.to_degree(rot)

                if not point1_near_by_point2(self.current_position, coordinates, 20):
                    # BUG: 必须先冲刺后，跳跃才生效
                    if self.enable_dash: rate_limiter_press_dash.execute(self.mouse_right_click)
                    if self.enable_loop_jump:
                        if self.enable_dash: time.sleep(0.005)  # 防止执行时间过短
                        rate_limiter_press_jump.execute(self.kb_press_and_release, self.Key.space)

                self.kb_press("w")
                if small_step_enable and running_small_step and self.allow_small_steps:
                    time.sleep(0.08)
                    self.debug("小碎步松开w")
                    self.kb_release('w')
                    # self.kb_press_and_release('d')
                time.sleep(self.UPDATE_POSITION_INTERVAL)

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

            # self.logger.debug('cost time: ' + str(time.time()-t))
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
        self.rate_limiter5_debug_print.execute(self.debug, msg)

    def get_next_point_rotation(self, next_point):
        from autotrack.utils import calculate_angle
        if self.current_position and next_point:
            nextp = (next_point[0], next_point[1])
            x0, y0 = self.current_position[0], self.current_position[1]
            deg = calculate_angle(x0, y0, nextp[0], nextp[1])
            # self.log(f"计算角度 ,当前:{self.current_position}, next{nextp}, 结果{deg}")
            return deg

    def _thread_path_viewer(self):
        if not cfg.get('show_path_viewer', 1): return  # 无需展示路径
        path = self.path_obj
        from autotrack.KeyPointViewer import get_points_img_live
        #  当前路径结束后，应当退出循环，结束线程，以便于开启下一个线程展示新的路径
        logger.info(f"准备展示路径:{path.target_name}")
        win_name = f'path_viewer {threading.currentThread().name}'
        while not self.stop_listen and not self.is_path_end:
            time.sleep(0.3)
            if len(path.points) > 0:
                # win_name = 'path viewer'
                img = get_points_img_live(path.points, path.target_name, radius=cfg.get('path_viewer_width', 500))
                if img is None: continue
                cv2.imshow(win_name, img)
                cv2.moveWindow(win_name, 10, 10)
                cv2.waitKey(1)
            else:
                logger.debug('路径列表为空，无法展示')
        try:
            cv2.destroyWindow(win_name)
        except:

            logger.debug('还没开始展示就结束了')
        logger.debug("路径展示结束")

    def _thread_update_state(self):
        while not self.is_path_end and not self.stop_listen and not self._thread_update_state_finished:
            # self.log(f"多线程更新状态中, {self.stop_listen}")
            self.update_state()
            time.sleep(self.UPDATE_POSITION_INTERVAL)

    def _thread_exception_detect(self):
        pass

    def wait_for_position_update(self, wait_times):
        """
        等待位置刷新, 单位：秒
        :param wait_times:
        :return:
        """
        start_time = time.time()
        pos = self.current_position
        while not pos:
            pos = self.current_position
            if self.stop_listen: return None
            self.logger.debug(f'正在等待位置中，已经等待{time.time()-start_time:}')
            if time.time() - start_time > wait_times:
                return None
            time.sleep(0.001)
        return pos

    def execute(self):
        self.logger.debug(f'开始执行{self.path_obj.absolute_path}')
        self.object_to_detect = self.path_obj.target_name
        if len(self.path_obj.points) < 1:
            self.logger.warning(f"空白路线, 跳过")
            return

        # 传送的时候可以顺便缓存局部地图，因此把传送放在第一行
        self.map_controller.transform((self.path_obj.points[0].x, self.path_obj.points[0].y), self.path_obj.country, create_local_map_cache=True)
        # 开始更新位置
        thread_update_state = threading.Thread(target=self._thread_update_state)
        thread_update_state.start()
        # 路径展示
        thread_path_viewer = threading.Thread(target=self._thread_path_viewer)
        thread_path_viewer.start()
        # 目标检测
        thread_object_detect = threading.Thread(target=self._thread_object_detection)
        thread_object_detect.start()
        # 异常线程
        thread_exception = threading.Thread(target=self._thread_exception_detect)
        thread_exception.start()


        for point in self.path_obj.points[1:]:
            if self.stop_listen: return

            # 阻塞等待位置刷新
            if not self.wait_for_position_update(10):
                self.debug(f"由于超过10秒没有获取到位置,跳过点位{point}")
                continue  # 上面的while循环未能成功加载位置，跳到下一个点位

            self.debug(f"当前位置{self.current_position}, 正在前往点位{point}")
            self.next_point = point
            if not point1_near_by_point2(self.current_position, (point.x, point.y), 500):
                # 如果当前点位距离下一个点位过远，可能是由于角色死亡被传送
                self.log("当前点位距离下一个点位过远，可能是由于角色死亡被传送, 提前终止{}")
                return False

            small_step_enable = point.type == self.object_to_detect or point.type == 'end'
            self.move((point.x, point.y), small_step_enable)
            self.debug("已到达", point)

            self.on_move_after(point)

            if point.type == Point.TYPE_END:
                self.log("已经走到终点")
                break

        self.log("文件{}执行完毕")
        self.is_path_end = True
        # 等待线程结束
        thread_object_detect.join()
        thread_path_viewer.join()
        thread_update_state.join()
        thread_exception.join()
        self.log("线程已全部结束")

        # 重置状态

        return True


def execute_one(jsonfile):
    logger.info(f"开始执行{jsonfile}")
    pw = PathWrapper(jsonfile)
    debug_enable = cfg.get('debug_enable', True)
    BasePathExecutor(pw, debug_enable=debug_enable).execute()
    logger.info(f"文件{jsonfile}执行完毕")
    return True

def execute_all():
    points_path = cfg.get('points_path', os.path.join(PROJECT_PATH,'resources', 'pathlist'))
    if not os.path.exists(points_path):
        logger.error('路径不存在！')
        return
    filenames = os.listdir(points_path)
    try:
        for filename in filenames:
            execute_one(os.path.join(points_path, filename))
    except Exception as e:
        logger.error(f'发生错误: {e}')
    finally:
        logger.info("全部执行完成，按下m")
        import controller.BaseController
        BaseController().kb_press_and_release('m')
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
    # execute_one(getjson('甜甜花_枫丹_中央实验室遗址_2024-07-31_07_01_37.json'))
    # ew.execute_one(getjson('甜甜花_枫丹_中央实验室遗址_test_2024-08-07_10_28_37.json'))
    execute_all()

