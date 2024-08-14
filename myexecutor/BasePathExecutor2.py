import random
import threading
import time
import asyncio
import cv2
import sys
from controller.BaseController import BaseController
from collections import deque
from controller.MapController2 import MapController
from controller.OCRController import OCRController
from myutils.executor_utils import point1_near_by_point2, find_closest_point_index
from typing import List
import json
from myutils.configutils import cfg, PROJECT_PATH
from myutils.timerutils import RateLimiter
from mylogger.MyLogger3 import MyLogger
import logging

logger = MyLogger('path_executor', level=logging.DEBUG, save_log=True)


# 已知问题：
# TODO 1. 游泳点位概率出现原地转圈
# TODO 2. 关掉小碎步会增加原地转圈概率
# 距离点位越进, 角度变化幅度越大
# TODO 3: 目标点附近如果有npc，可能会导致进入对话

class MovingStuckException(Exception):
    pass


class MovingTimeOutException(Exception):
    pass


# 色死亡会被传送,传送后当前位置和历史位置作比较,超过一定阈值则认为死亡. 有时候会被传送到很远的的锚点,有时候会原地复活
# 原地复活的情况无法通过这种方式判断死亡,因此这不是严格意义上的判定死亡方式,而是人物的行动轨迹是否突变.
class MovingPositionMutationException(Exception):  # 位置突变异常
    pass


class Point:
    TYPE_PATH = 'path'
    TYPE_TARGET = 'target'

    MOVE_MODE_NORMAL = 'normal'
    MOVE_MODE_FLY = 'fly'  # fly的判断方式:下落攻击图标下方的白底黑字的space是否存在
    MOVE_MODE_JUMP = 'jump'  # 疯狂按空格
    # swim模式，可能会导致冲过头,尤其是浅水区人不在游泳而点位设置成了游泳的时候
    MOVE_MODE_SWIM = 'swim'  # swim 模式下，会禁止小碎步，因为小碎步的实现是疯狂按下w和停止w，这会加速消耗体力

    ACTION_STOP_FLYING_ON_MOVE_DONE = 'stop_flying'  # 接近目标的时候是否下落攻击以停止飞行

    def __init__(self, x, y, type=TYPE_PATH, move_mode=MOVE_MODE_NORMAL, action=None):
        self.x = x
        self.y = y
        self.type = type
        self.move_mode = move_mode
        self.action = action

    def __str__(self):
        return str(self.__dict__)


class PointEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Point):
            point = {'x': obj.x, 'y': obj.y}
            # 避免解析None
            if obj.type: point['type'] = obj.type
            if obj.move_mode: point['move_mode'] = obj.move_mode
            if obj.action: point['action'] = obj.action
            return point
        return super().default(obj)


class BasePathExecutor(BaseController):

    # 到达下一个点位采取何种移动方式？

    @staticmethod
    def load_json_obj_from_dict(json_dict):
        positions = json_dict['positions']
        points: List[Point] = []
        for point in positions:
            p = Point(x=point.get('x'),
                      y=point.get('y'),
                      type=point.get('type', Point.TYPE_PATH),
                      move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                      action=point.get('action'))
            points.append(p)
        json_dict['positions'] = points
        return json_dict

    @staticmethod
    def load_json(json_file_path):
        from myutils.configutils import resource_path
        with open(json_file_path, encoding="utf-8") as r:
            json_obj = json.load(r)
            json_map = {
                'name': json_obj.get('name', '未定义'),
                'country': json_obj.get('country', '蒙德'),
                "positions": None
            }
            positions = json_obj.get('positions')
            if json_map is None or len(positions) < 1: raise Exception(f"空白路线, 跳过")
            json_map['positions']: List[Point] = []
            for point in positions:
                p = Point(x=point.get('x'), y=point.get('y'),
                          type=point.get('type', Point.TYPE_PATH),
                          move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                          action=point.get('action'))
                json_map['positions'].append(p)
            return json_map

    def __init__(self, json_file_path=None, json_dict=None, debug_enable=None):
        super().__init__(debug_enable=debug_enable)
        if debug_enable is None:
            debug_enable = cfg.get('debug_enable', False)
        json_map = None
        if json_dict:
            json_map = self.load_json_obj_from_dict(json_dict)
        elif json_file_path:
            json_map = self.load_json(json_file_path)

        if json_map is None:
            raise Exception(f"无法加载json对象")
        self.country = json_map['country']  # 传送到什么区域
        self.target_name = json_map['name']  # 目标名称
        self.points: List[Point] = json_map['positions']
        self.json_file_path = json_file_path

        self.ocr = OCRController(debug_enable=debug_enable)
        # 传送用
        self.map_controller = MapController(tracker=self.tracker, debug_enable=debug_enable)
        self.debug_enable = debug_enable

        ################## 参数 #########################
        self.move_next_point_allow_max_time = cfg.get('move_next_point_allow_max_time', 20)
        if self.move_next_point_allow_max_time < 5:
            self.move_next_point_allow_max_time = 5
        elif self.move_next_point_allow_max_time > 60:
            self.move_next_point_allow_max_time = 60

        self.object_to_detect = None  # 目标检测对象, 例如 钓鱼
        self.position_history = deque(maxlen=8)  # 一秒钟存1次，计算总距离

        # 8秒内移动的总距离(像素)在多少范围内认为卡住，允许范围(2~50)
        self.stuck_movement_threshold = cfg.get('stuck_movement_threshold', 20)
        if self.stuck_movement_threshold < 2:
            self.stuck_movement_threshold = 2
        elif self.stuck_movement_threshold > 50:
            self.stuck_movement_threshold = 50

        # 精度：当前位置距离目标点距离多少个像素点表示他们是临近, 小碎步时候要用到
        self.target_nearby_threshold = cfg.get('target_nearby_threshold', 2)
        if self.target_nearby_threshold < 0.1: self.target_nearby_threshold = 0.1
        if self.target_nearby_threshold > 10: self.target_nearby_threshold = 10

        # 判断是否到达途径点的阈值
        self.path_point_nearby_threshold = cfg.get('path_point_nearby_threshold', 2)
        if self.path_point_nearby_threshold < 2: self.path_point_nearby_threshold = 2
        if self.path_point_nearby_threshold > 50: self.path_point_nearby_threshold = 50

        # 在跑路的过程中,角色'当前位置'和走过的'历史点位中最近存放的一个点位'差距超过多少的时候判定为死亡
        # 原理: 人物死亡会被传送, 要么原地复活,要么被传送到附近的锚点, 原地复活不会触发此异常(因为位置变化不大)
        # (不能和next_point比较,因为有些路径本身打点可能打的比较远)
        # 不能设置太小, 以防止人物正常的移动产生较大位移时, 误判为位置突变
        self.position_mutation_threshold = cfg.get('position_mutation_threshold', 100)
        if self.position_mutation_threshold < 50:
            self.position_mutation_threshold = 50
        elif self.position_mutation_threshold > 200:
            self.position_mutation_threshold = 200

        # 即使找到了最近的点,也要求最近的距离不能大于指定阈值
        self.search_closet_point_max_distance = cfg.get('search_closet_point_max_distance', 200)
        if self.search_closet_point_max_distance > 500: self.search_closet_point_max_distance = 500
        elif self.search_closet_point_max_distance < 80: self.search_closet_point_max_distance = 80

        # 允许多少次位置突变(当前位置突然和历史轨迹的距离超过一定阈值)
        self.position_mutation_max_time = cfg.get('position_mutation_max_time', 3)
        if self.position_mutation_max_time < 0: self.position_mutation_max_time = 0  # 突变一次就结束
        elif self.position_mutation_max_time > 10: self.position_mutation_max_time = 10

        # 路径展示器的宽高
        self.path_viewer_width = cfg.get('path_viewer_width', 500)
        if self.path_viewer_width < 50:
            self.path_viewer_width = 50
        elif self.path_viewer_width > 4096:
            self.path_viewer_width = 4096

        self.allow_small_steps = cfg.get('allow_small_steps', 1) == 1  # 是否允许小碎步接近目标：注意此选项对Point.type=='path'的途径点无效
        self.enable_crazy_f = cfg.get('enable_crazy_f', 1) == 1  # 是否在接近目标点时候疯狂按下f：对途径点无效
        self.enable_loop_press_e = cfg.get('enable_loop_press_e', 1) == 1  # 循环按下e开技能
        self.enable_loop_press_z = cfg.get('enable_loop_press_z', 1) == 1  # 循环按下z使用道具
        self.enable_loop_jump = cfg.get('enable_loop_jump', 1) == 1  # 循环按下空格跳跃
        self.enable_dash = cfg.get('enable_dash', 1) == 1  # 循环按下鼠标右键冲刺

        # 0.05s更新一次位置, 值越小，请求位置信息越频繁
        # self.update_user_status_interval = cfg.get('update_user_status_interval', 0.2)
        self.update_user_status_interval = cfg.get('update_user_status_interval', 0.1)
        if self.update_user_status_interval > 0.2:
            self.update_user_status_interval = 0.2
        elif self.update_user_status_interval < 0.01:
            self.update_user_status_interval = 0.01

        self.last_time_update_user_status = time.time()  # 上一次更新用户状态(当前位置、转向）的时间

        ############ 状态 ##############
        self.current_position = None
        self.current_rotation = None  # 当前视角
        self.next_point: Point = None
        self.prev_point: Point = None
        self.is_path_end = False  # 是否到达终点
        # 卡住前的位移，用于卡住后，系统执行一段随机行走操作判断行走后和行走前的距离是否超过一定阈值时候认为取消卡住状态
        self.stuck_before_position = None

        # 多线程
        self._thread_object_detect_finished = False  # 目标检测任务
        self._thread_update_state_finished = False  # 更新状态

        ######## 其他 #######
        self.rate_limiter1_history = RateLimiter(1)  # 一秒钟之内只能执行一次
        self.rate_limiter5_debug_print = RateLimiter(5)  # 5秒内只能执行一次

        self.rate_limiter_press_e = RateLimiter(1)
        self.rate_limiter_press_z = RateLimiter(1)
        self.rate_limiter_press_dash = RateLimiter(1)
        self.rate_limiter_press_jump = RateLimiter(1)  # 避免跳跃和冲刺同时按下导致无效


        self.rate_limiter_fly = RateLimiter(0.1)
        self.rate_limiter_small_step_release_w = RateLimiter(0.08)

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
            return 100000000  # Not enough data to calculate displacement

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
        """
        当接近点位时，此方法会不断执行直到到达点位
        :param next_point:
        :return:
        """
        self.logger.debug(f'接近点位{self.next_point}了')
        if self.enable_crazy_f:
            self.debug('疯狂按下f')
            self.crazy_f()

    def do_action_if_moving_stuck(self):
        if self.gc.is_climbing(): self.kb_press('x')
        time.sleep(0.1)
        self.kb_press_and_release(random.choice('wsad'))  # 任意方向
        time.sleep(0.1)
        self.kb_press_and_release(self.Key.space)
        # 判断是否产生了位移
        if not point1_near_by_point2(self.stuck_before_position, self.current_position, 3):
            # 大于3个像素就产生了位移
            self.logger.debug('产生了3以上的位移，清空历史列表')
            self.position_history.clear()

    def do_action_if_timeout(self):
        self.logger.debug('点位执行超时, 跳过该点位')
        if self.gc.is_climbing(): self.kb_press('x')
        time.sleep(0.1)
        self.kb_press_and_release(random.choice('wsad'))  # 任意方向
        time.sleep(0.1)
        self.kb_press_and_release(self.Key.space)
        # 判断是否产生了位移
        if not point1_near_by_point2(self.stuck_before_position, self.current_position, 3):
            # 大于3个像素就产生了位移
            self.logger.debug('产生了3以上的位移，清空历史列表')
            self.position_history.clear()

    def __do_move(self, coordinates, point_start_time):
        # 开技能
        if self.enable_loop_press_z: self.rate_limiter_press_z.execute(self.kb_press_and_release, 'z')
        if self.enable_loop_press_e: self.rate_limiter_press_e.execute(self.kb_press_and_release, 'e')

        # 限制1秒钟只能执行1次，这样就能记录每一秒的位移
        self.rate_limiter1_history.execute(self.position_history.append, self.current_position)
        total_displacement = self.calculate_total_displacement()  # 8秒内的位移
        if total_displacement < self.stuck_movement_threshold:
            self.stuck_before_position = coordinates
            raise MovingStuckException(f"8秒内位移总值为{total_displacement}, 判定为卡住了！")

        # 超时判断
        if time.time() - point_start_time > self.move_next_point_allow_max_time:
            self.stuck_before_position = coordinates
            raise MovingTimeOutException(f"执行点位超时, 跳过该点位！")

        # 转向: 注意，update_state()线程永远保证self.positions在首次赋值之后不再是空值,但是计算角度的函数可能会返回空值，因此还是要判断
        rot = self.get_next_point_rotation(coordinates)
        if rot: self.to_degree(self.get_next_point_rotation(coordinates))
        # 前进: 注意要先转向后再前进，否则可能会出错

        # 小碎步实现方法：先按下w等待一小段时间再松开w，反复循环
        # 小碎步的条件：当和目标点差距8个像素时候，就认为符合最基本条件
        nearby = self.next_point.type == self.next_point.TYPE_TARGET and point1_near_by_point2(self.current_position,
                                                                                               coordinates, 8)
        if nearby: self.logger.debug(f'接近下一个点位{self.next_point}, 当前在{coordinates}')
        # 接近上一个点位
        nearby_last_point = self.prev_point is not None and self.prev_point.type == self.prev_point.TYPE_TARGET and point1_near_by_point2(
            self.current_position, (self.prev_point.x, self.prev_point.y), 8)
        if nearby_last_point: self.logger.debug(f'接近上一个点位{self.prev_point}, 当前在{coordinates}')

        if nearby or nearby_last_point: self.on_nearby(coordinates)

        # 不是游泳状态但是设置了游泳模式，同样允许小碎步
        swimming = self.gc.is_swimming() and self.next_point.MOVE_MODE_SWIM
        small_step_enable = (nearby and self.allow_small_steps
                             and (self.next_point.type == self.next_point.TYPE_TARGET)
                             and not swimming)

        self.kb_press("w")
        # 按照一定的频率松开w实现小碎步
        if small_step_enable: self.rate_limiter_small_step_release_w.execute(self.kb_press_and_release, 'w')



    def is_nearby_path_point(self):
        """
        是否接近途径点
        :return:
        """
        if self.next_point.type == Point.TYPE_PATH:
            return point1_near_by_point2(self.current_position, (self.next_point.x,self.next_point.y), self.path_point_nearby_threshold)

    def is_nearby_target_point(self):
        """
        是否接近目标点
        :return:
        """
        if self.next_point.type == Point.TYPE_TARGET:
            return point1_near_by_point2(self.current_position, (self.next_point.x,self.next_point.y), self.target_nearby_threshold)

    # 移动(尽量不要阻塞））
    # 异常：原地踏步,超时, 位置突变(死亡后被传送)
    # 类型：途径点,目标点
    # 移动方式：跳跃, 飞行，小碎步，爬山（未实现）
    # 动作：停止飞行（下落攻击）
    # 拓展：自定义按键(未实现）
    def move(self, coordinates):
        if self.stop_listen: return
        point_start_time = time.time()
        self.position_history.clear()
        # 逐步接近目标点位
        # 达到途径点的阈值时，跳出循环，直接进入下一个点位
        # 退出的条件满足其一即可
        # 1. 到达途径点
        # 2. 到达目标点
        while not self.is_nearby_path_point() and not self.is_nearby_target_point():
            if self.stop_listen: return
            try:
                # 当前点位和历史点位差距过大, 可能死亡导致被传送
                # 游戏特性: 死亡后可能传送到附近,也可能传送到最近一次传送的锚点(非距离最近锚点)
                if len(self.position_history) > 1:
                    last_time_save_pos = self.position_history[-1]
                    if not point1_near_by_point2(self.current_position, last_time_save_pos, self.position_mutation_threshold):
                        msg = '当前记录与历史点位记录差距过大!可能由于死亡被传送!'
                        self.debug(msg)
                        raise MovingPositionMutationException(msg)

                self.__do_move(coordinates, point_start_time)  # 走一步

                # 如果距离点位超过n个像素值，则可以采取冲刺+跳跃行动
                if self.next_point.move_mode == Point.MOVE_MODE_FLY:
                    if not self.gc.is_flying(): self.rate_limiter_fly.execute(self.kb_press_and_release, self.Key.space)

                # 以下的行为可能会导致冲过头,因此设定一个阈值,超过该距离才允许执行
                elif not point1_near_by_point2(self.current_position, coordinates, 15):
                    # 冲刺
                    if self.enable_dash: self.rate_limiter_press_dash.execute(self.mouse_right_click)
                    # 跳跃
                    if self.enable_loop_jump or self.next_point.move_mode == Point.MOVE_MODE_JUMP: self.rate_limiter_press_jump.execute(self.kb_press_and_release, self.Key.space)


            except MovingStuckException as e:
                self.logger.error(e)
                self.do_action_if_moving_stuck()
            except MovingTimeOutException as e:
                self.logger.error(e)
                self.do_action_if_timeout()
                return  # 超时跳过
            except MovingPositionMutationException as e:
                self.logger.error('捕获到了位置突变异常但是这里处理不了,抛出去')
                raise e

        # 到达目的地时，是否使用下落攻击
        if self.next_point.action == self.next_point.ACTION_STOP_FLYING_ON_MOVE_DONE:
            self.logger.debug("下落攻击以停止飞行！")
            self.mouse_left_click()

        self.logger.debug(f'跑点{coordinates}用时：{time.time() - point_start_time}')
        self.kb_release('w')

    def on_move_after(self, point):
        self.log(f'到达点位{point}了')
        if self.enable_crazy_f and point.type == point.TYPE_TARGET:
            self.debug('疯狂按下f')
            self.crazy_f()

    def update_state(self):
        start = time.time()
        pos = self.tracker.get_position()
        if pos: self.current_position = pos
        rot = self.tracker.get_rotation()
        if rot: self.current_rotation = rot

        self.last_time_update_user_status = time.time()
        msg = f"更新状态: cost:{time.time() - start},next:{self.next_point}, current pos:{self.current_position}, rotation:{self.current_rotation},is_path_end:{self.is_path_end}, is_object_detected_end:{self._thread_object_detect_finished}"
        self.rate_limiter5_debug_print.execute(self.debug, msg)

    def get_next_point_rotation(self, next_point):
        from myutils.executor_utils import calculate_angle
        if self.current_position and next_point:
            nextp = (next_point[0], next_point[1])
            x0, y0 = self.current_position[0], self.current_position[1]
            deg = calculate_angle(x0, y0, nextp[0], nextp[1])
            # self.log(f"计算角度 ,当前:{self.current_position}, next{nextp}, 结果{deg}")
            return deg

    def _thread_path_viewer(self):
        if not cfg.get('show_path_viewer', 1): return  # 无需展示路径
        from myexecutor.KeyPointViewer import get_points_img_live
        #  当前路径结束后，应当退出循环，结束线程，以便于开启下一个线程展示新的路径
        logger.info(f"准备展示路径:{self.target_name}")
        win_name = f'path_viewer {threading.currentThread().name}'
        while not self.stop_listen and not self.is_path_end:
            time.sleep(0.3)
            if len(self.points) > 0:
                # win_name = 'path viewer'
                img = get_points_img_live(self.points, self.target_name, width=self.path_viewer_width, scale=2)
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
            time.sleep(self.update_user_status_interval)

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
            self.logger.debug(f'正在等待位置中，已经等待{time.time() - start_time:}')
            if time.time() - start_time > wait_times:
                return None
            time.sleep(0.001)
        return pos

    def execute(self):
        self.logger.debug(f'开始执行{self.json_file_path}')
        self.object_to_detect = self.target_name
        if len(self.points) < 1:
            self.logger.warning(f"空白路线, 跳过")
            return
        # 传送的时候可以顺便缓存局部地图，因此把传送放在第一行
        self.map_controller.transform((self.points[0].x, self.points[0].y), self.country, create_local_map_cache=True)
        # 更新位置
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

        moving_position_mutation_counter = 0

        i = 1  # 跳过传送点
        while i < len(self.points):
            point = self.points[i]
            if self.stop_listen: return

            # 阻塞等待位置刷新
            if not self.wait_for_position_update(10):
                self.debug(f"由于超过10秒没有获取到位置,跳过点位{point}")
                i += 1
                continue  # 上面的while循环未能成功加载位置，跳到下一个点位

            if not point1_near_by_point2(self.current_position, (point.x, point.y), 200):
                self.logger.error(f'距离下一个点位太远,跳过{point}')
                i += 1
                continue

            self.debug(f"当前位置{self.current_position}, 正在前往点位{point}")
            self.next_point = point
            try:
                self.move((point.x, point.y))
            except MovingPositionMutationException:

                # 角色位置突变如何处理?(死亡被传送到了较远的锚点)
                self.logger.error('捕捉到了位置突变异常,尝试查找最近的点')
                moving_position_mutation_counter += 1
                if moving_position_mutation_counter > self.position_mutation_max_time:
                    self.logger.error(f'位置突变次数{moving_position_mutation_counter}, 超过{self.position_mutation_max_time}, 执行结束')
                    self.is_path_end = True
                    return False
                # 查找最近的一个执行点的下标
                index = find_closest_point_index(coordinates=self.current_position, points=self.points,
                                                 distance_threshold=self.position_mutation_threshold)
                if index is not None:
                    self.logger.debug(f'查找到距离当前坐标最近的点是{self.points[index]},从这里开始执行任务')
                    i = index
                    continue
                else:
                    self.debug('最近的点位超过了阈值,执行结束!')
                    self.is_path_end = True
                    return False

            self.debug(f"已到达{point}")
            self.on_move_after(point)
            self.prev_point = point
            i += 1

        self.log("文件{}执行完毕")
        self.is_path_end = True
        # 等待线程结束
        thread_object_detect.join()
        thread_path_viewer.join()
        thread_update_state.join()
        thread_exception.join()
        self.log("线程已全部结束")

        return True


def execute_one(jsonfile):
    logger.info(f"开始执行{jsonfile}")
    debug_enable = cfg.get('debug_enable', True)
    BasePathExecutor(jsonfile, debug_enable=debug_enable).execute()
    logger.info(f"文件{jsonfile}执行完毕")
    return True


def execute_all():
    """
    执行全部脚本,则需要一个监听器监听是否停止运行
    :return:
    """
    from pynput.keyboard import Listener, Key
    def _on_press(key):
        try:
            c = key.char
        except AttributeError:
            # print('special key {0} pressed'.format(key))
            if key == Key.esc:
                logger.info('你按下了esc退出程序, 停止运行所有脚本')
                sys.exit(0)

    kb_listener = Listener(on_press=_on_press)
    kb_listener.setDaemon(True)
    kb_listener.start()

    all_start_time = time.time()
    points_path = cfg.get('points_path', os.path.join(PROJECT_PATH, 'resources', 'pathlist'))
    err_list = []
    if not os.path.exists(points_path):
        logger.error('路径不存在！')
        return
    filenames = os.listdir(points_path)
    for filename in filenames:
        try:
            execute_one(os.path.join(points_path, filename))
        except Exception as e:
            logger.error(f'发生错误: {e}')
            err_list.append(filename)
            raise e
    logger.info(f"全部执行完成, 共执行{len(filenames)}个脚本，总计用时{time.time() - all_start_time}，按下m")
    logger.info(f'错误列表:{err_list}')
    import controller.BaseController
    BaseController().kb_press_and_release('m')
    # print("30秒后进入睡眠")
    # time.sleep(30)


if __name__ == '__main__':
    # 测试点位
    import os
    from myutils.jsonutils import getjson_path_byname

    # execute_one(getjson_path_byname('风车菊_蒙德_8个_20240814_101536.json'))
    # execute_one(getjson_path_byname('jiuguan_蒙德_wfsd_20240808.json'))
    # execute_one(getjson_path_byname('jiuguan_枫丹_tiantianhua_20240808.json'))
    # execute_one(getjson_path_byname('甜甜花_枫丹_中央实验室遗址_test_2024-08-08_12_37_05.json'))
    # execute_one(getjson_path_byname('风车菊_蒙德_清泉镇_2024-08-08_14_46_25.json'))
    # execute_one(getjson_path_byname('调查_璃月_地中之岩_2024-04-29_06_23_28.json'))
    # execute_one(getjson_path_byname('月莲_须弥_降魔山下_6个.json'))
    # execute_one(getjson_path_byname('霓裳花_璃月_8个.json'))
    execute_one(getjson_path_byname('月莲_茸蕈窟_须弥_4个.json'))
    # execute_all()
