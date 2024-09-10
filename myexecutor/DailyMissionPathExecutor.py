import threading
import time
from controller.BaseController import StopListenException
from controller.MapController2 import MapController

# 委托流程：
# 已知委托的地点都是固定的

# 保存委托
# 把所有的委托全部存起来，用json文件存放

from myexecutor.BasePathExecutor2 import BasePathExecutor,Point, BasePath
import os,cv2
import numpy as np
from typing import List
import json
from capture.capture_factory import capture
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("daily_mission_executor")
from controller.FightController import FightController
from myutils.configutils import get_config

# 递归超时异常
class ExecuteTimeOutException(Exception): pass


# 纯战斗

# 邪恶的扩张 消灭所有魔物 0/8 0/5
# 持盾的危机 消灭所有魔物 0/5
# 邱邱人的一小步 消灭所有魔物0/8
# [为了执行官大人!] 击败所有敌人 0/3
# 圆滚滚的易爆品 消灭所有魔物 0/8
# 临危受命 消灭丘丘霜凯王 0/1 蒙德-覆雪之路

# 破坏
# 攀高危险 摧毁邱邱人哨塔

# 对话
# [冒险家]的能力极限 帮助赫尔曼先生
# 鸽子习惯一去不回 帮助杜拉夫先生 0/1
# 语言交流


# 目前仅能完部分的战斗委托, 并且比较依赖那维莱特、水神
# 如果队伍伤害不够可能还得再来一遍

class UnfinishedException(Exception): pass  # 只录制了一半的委托
class DailyMissionPathExecutorException(Exception): pass

# https://stackoverflow.com/questions/15562446/how-to-stop-flask-application-without-using-ctrl-c
# @app.get('/shutdown')
# def shutdown():
#     shutdown_server()
#     return 'Server shutting down...'

class DailyMissionPoint(Point):
    EVENT_DESTROY_AILIN = "destroy_ailin"  # 艾琳一次性破坏木桩
    EVENT_FIGHT = 'fight'
    EVENT_STANDING_ON_PLATE = 'standing_on_plate'  # 极速前进, 要踩下机关
    EVENT_FAST_FIGHT = 'fast_fight'  # 极速前进，消灭怪物就可以加时长，要求尽快结束战斗，有各种元素类型史莱姆唯独没有风史莱姆，可以用散兵自动索敌平a
    EVENT_DESTROY = 'destroy'
    EVENT_DIALOG = 'dialog'
    EVENT_FIND_NPC = 'find_npc'
    EVENT_COLLECT = 'collect'
    EVENT_CLIMB = 'climb'  # 爬神像，做不到
    EVENT_DEFENSE = 'defense'  # 固若金汤，守护镇石
    EVENT_GEER_START = 'geer_start'  # 开启齿轮机关

    def __init__(self, x, y, type=Point.TYPE_PATH, move_mode=Point.MOVE_MODE_NORMAL, action=None, events=None):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        self.events = events

class DailyMissionPath(BasePath):
    def __init__(self, name, country, positions: List[DailyMissionPoint], anchor_name=None, enable=None):
        super().__init__(name=name, country=country, positions=positions, anchor_name=anchor_name)
        self.enable=enable
        self.mission_position_index = -1  # 默认情况下取最后一个点位作为委托在地图上的位置
        self.note = None  # 自定义备注
        # TODO：指定委托所在的位置，用于搜索；对于战斗类型通常是最后一个点的位置，其他的不一定
        # self.mission_position = None  #

class DailyMissionPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path, debug_enable=None):
        self.next_point: DailyMissionPoint = None
        super().__init__(json_file_path=json_file_path, debug_enable=debug_enable)
        # self.fight_controller = FightController('那维莱特_莱伊拉_迪希雅_行秋(龙莱迪行).txt')
        # self.fight_controller = FightController('那维莱特_莱伊拉_行秋_枫原万叶(龙莱行万).txt')
        self.fight_controller = FightController(None)

    @staticmethod
    def load_basepath_from_json_file(json_file_path) -> DailyMissionPath:
        with open(json_file_path, encoding="utf-8") as r:
            json_dict = json.load(r)
            points: List[DailyMissionPoint] = []
            for point in json_dict.get('positions', []):
                p = DailyMissionPoint(x=point.get('x'),
                          y=point.get('y'),
                          type=point.get('type', Point.TYPE_PATH),
                          move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                          action=point.get('action'),events=point.get('events'))
                points.append(p)
            return DailyMissionPath(
                name=json_dict['name'], country=json_dict['country'], positions=points,
                enable=json_dict.get('enable', True)  # 未记录完成的委托标记为False
            )


    # 2. 模板匹配查找屏幕中的所有的任务的坐标
    @staticmethod
    def get_mission_template_matched_screen_position():
        """
        获取屏幕上的模板匹配
        :return:
        """
        from myutils.configutils import resource_path
        # 传送锚点流程
        # 加载地图位置检测器
        template_image = cv2.imread(os.path.join(resource_path, "template", "icon_mission.jpg"))
        gray_template = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)

        original_image = capture.get_screenshot().copy()
        gray_original = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

        # 获取模板图像的宽度和高度
        w, h = gray_template.shape[::-1]

        # 将小图作为模板，在大图上进行匹配
        result = cv2.matchTemplate(gray_original, gray_template, cv2.TM_CCOEFF_NORMED)

        # 设定阈值
        threshold = 0.85
        # 获取匹配位置
        locations = np.where(result >= threshold)

        mission_screen_points = []
        prev_point = None
        # 绘制匹配结果
        from myutils.executor_utils import euclidean_distance
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            if prev_point is None:
                prev_point = pt
                mission_screen_points.append((center_x, center_y))

            elif euclidean_distance(prev_point, pt) > 10:
                mission_screen_points.append((center_x, center_y))
                prev_point = pt

            cv2.rectangle(original_image, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)

        # 显示结果
        # original_image = cv2.resize(original_image, None, fx=0.5, fy=0.5)
        # # cv2.imshow('Matched Image', original_image)
        # cv2.waitKey(0)
        # if key == ord('q'):
        #     cv2.destroyAllWindows()
        return mission_screen_points
    # 3. 请求一次屏幕中心的世界坐标，和当前缩放
    # 4. 2和3的结果做运算，得到实际坐标

    @staticmethod
    def get_specify_point_closest_mission_json(target_point):
        """
        查找指定位置最近的委托
        :param target_point:
        :return:
        """
        if target_point is None: raise Exception("目标点不能为空")

        from myutils.executor_utils import euclidean_distance
        from myutils.configutils import resource_path
        mission_path = os.path.join(resource_path, 'pathlist', '委托')

        closet_mission_json = None
        min_distance = None
        for mission_file_name in os.listdir(mission_path):
            with open(os.path.join(mission_path, mission_file_name), encoding='utf-8') as f:
                dme = json.load(f)
                # TODO: 委托的起始位置如何确定？对于战斗类型是最后一个；对于其他呢？可能需要指定下标
                index = dme.get("mission_position_index")
                if index:
                    mission_point = dme.get('positions')[index]
                else:
                    mission_point = dme.get('positions')[-1]  # 没有位置变动的委托，例如战斗委托

                d = euclidean_distance(target_point, (mission_point['x'], mission_point['y']))
                if min_distance is None:
                    min_distance = d
                    closet_mission_json = os.path.join(mission_path, mission_file_name)
                    continue

                if min_distance > d:
                    min_distance = d
                    closet_mission_json = os.path.join(mission_path, mission_file_name)
        if min_distance > 100: return None  # 丢弃距离过远的委托
        return closet_mission_json


    @staticmethod
    def get_screen_world_mission_json(map_controller:MapController, only_fight_mission=True):
        """
        获取委托json
        :param map_controller:
        :param only_fight_mission: 仅获取战斗委托
        :return:
        """
        # 打开地图
        map_controller.open_middle_map()
        # time.sleep(0.8)
        # 前往清泉镇的七天神像，因为在这里将地图缩放拉到最小后,可以看到蒙德的所有委托
        # 必须要传送的原因：如果某个委托没打完，人物还站在原地，打开地图时，人物会遮挡当前未完成的委托
        # map_controller.choose_country('蒙德')
        DailyMissionPathExecutor.go_to_seven_anemo(map_controller)
        map_controller.open_middle_map()  # 再次打开地图
        map_controller.zoom_out(-5000)  # 缩放拉到最小
        map_controller.zoom_out(-5000)
        map_controller.zoom_out(-5000)
        time.sleep(1)
        # 查找最近的委托
        closet_missions = []
        # 模板匹配屏幕中出现的委托,得到他们的屏幕坐标
        missions_screen_points = DailyMissionPathExecutor.get_mission_template_matched_screen_position()
        # 计算得到世界坐标
        mission_world_points = map_controller.get_world_coordinate(missions_screen_points)
        for mission_world_point in mission_world_points:
            closest:str = DailyMissionPathExecutor.get_specify_point_closest_mission_json(mission_world_point)
            if closest is None: continue
            if only_fight_mission:
                if "未完成" in closest: continue  # 文件名称包含'未完成'的跳过
            closet_missions.append(closest)

        return closet_missions


    @staticmethod
    def go_to_seven_anemo(map_controller:MapController):
        x,y, country = 1944.8270,-4954.61, "蒙德"
        logger.debug("前往清泉镇七天神像")
        map_controller.teleport((x, y), country, "七天神像")

    # 5. 遍历实际坐标，遍历所有已存放的委托列表, 查找最近的一个委托

    @staticmethod
    def execute_all_mission(emit=lambda val1,val2:None):  # 传一个空实现的方法，免去判断函数是否为空
        from server.service.DailyMissionService import  SOCKET_EVENT_DAILY_MISSION_UPDATE, SOCKET_EVENT_DAILY_MISSION_END
        from controller.MapController2 import MapController
        daily_task_execute_timeout:int = get_config('daily_task_execute_timeout', 500)
        if daily_task_execute_timeout < 60: daily_task_execute_timeout = 60
        elif daily_task_execute_timeout > 1200: daily_task_execute_timeout = 1200

        map_controller = MapController()
        start_time = time.time()
        try:
            # 递归执行委托，直到完成
            closet_missions = DailyMissionPathExecutor.get_screen_world_mission_json(map_controller)
            while len(closet_missions) > 0:  # 不断执行委托直到屏幕上查找到的战斗委托为空
                msg = f"查找到战斗委托:{closet_missions}"
                logger.debug(msg)
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, msg)
                if time.time() - start_time > daily_task_execute_timeout: raise ExecuteTimeOutException("已超时!")
                for closest in closet_missions:
                    msg = f"开始执行战斗委托:{closest}"
                    logger.debug(msg)
                    emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, msg)
                    DailyMissionPathExecutor(closest).execute()

                closet_missions = DailyMissionPathExecutor.get_screen_world_mission_json(map_controller)

        except ExecuteTimeOutException as e:
            emit(SOCKET_EVENT_DAILY_MISSION_END, f'{e.args}')
        except StopListenException:
            emit(SOCKET_EVENT_DAILY_MISSION_END, f'手动强制结束执行委托')

        msg = f"执行战斗委托结束, 总时长{time.time() - start_time}"
        emit(SOCKET_EVENT_DAILY_MISSION_END, msg)
        logger.debug(msg)

    def on_execute_before(self, from_index=None):
        self.base_path: DailyMissionPath
        if not self.base_path.enable:
            raise UnfinishedException(f"未完成路线:{self.base_path.name}，跳过")
        super().on_execute_before(from_index=from_index)

    def start_fight(self):
        self.log('开始自动战斗')
        self.fight_controller.start_fighting()


    def stop_fight(self):
        self.log('停止自动战斗')
        self.fight_controller.stop_fighting()

    def wait_until_fight_finished(self):
        daily_task_fight_timeout = get_config('daily_task_fight_timeout', 20)
        if daily_task_fight_timeout < 10: daily_task_fight_timeout = 10
        elif daily_task_fight_timeout > 400: daily_task_fight_timeout = 400

        start_time = time.time()
        time.sleep(0.5)
        self.start_fight()
        while time.time()-start_time < daily_task_fight_timeout:
            if self.stop_listen: break
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{daily_task_fight_timeout-(time.time()-start_time)}秒")
            if len(self.ocr.find_match_text('委托完成'))>0: break
        self.stop_fight()

    def wait_until_destroy(self):
        daily_task_destroy_timeout = get_config('daily_task_destroy_timeout', 20)
        if daily_task_destroy_timeout < 10: daily_task_destroy_timeout = 10
        elif daily_task_destroy_timeout > 400: daily_task_destroy_timeout = 400

        self.start_fight()
        start_time = time.time()
        while time.time()-start_time < daily_task_destroy_timeout:
            if self.stop_listen: break
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{daily_task_destroy_timeout -(time.time()-start_time)}秒")
            if len(self.ocr.find_match_text('委托完成'))>0: break
        self.stop_fight()

    def on_nearby(self, coordinates):
        if self.next_point.type == DailyMissionPoint.TYPE_TARGET:
            for event in self.next_point.events:
                if event == DailyMissionPoint.EVENT_GEER_START:
                    if self.gc.has_gear():
                        self.log('nearby:发现齿轮，疯狂f')
                        self.crazy_f()

    def wait_until_geer_start(self):
        stat_time = time.time()
        while self.gc.has_gear() and time.time() - stat_time < 5:
            if self.stop_listen: break
            self.logger.debug("wait:发现齿轮, 狂按f")
            self.crazy_f()
            time.sleep(0.02)

    def wait_until_defense_done(self):
        self.wait_until_fight_finished()


    def wait_until_ailin_destroy(self):
        """
        需要切人，要求一次性打掉木桩
        :return:
        """
        pass


    def wait_until_dialog_finished(self):
        start = time.time()
        while time.time()-start < 50:
            self.log(f"正在等待对话结束, 剩余等待时间{50-(time.time()-start)}")
            if capture.has_paimon():
                self.log("发现派蒙，对话结束")
                break
            time.sleep(1)

    def wait_until_fast_fight_finished(self):
        # 目前很难判断快速战斗是否结束, 直接粗暴的给10秒
        start = time.time()
        while time.time() - start < 10:
            time.sleep(0.2)
            self.mouse_left_click()


    def on_move_after(self, point: DailyMissionPoint):
        super().on_move_after(point)
        if point.type == DailyMissionPoint.TYPE_TARGET:
            if point.events is None: return
            for event in point.events:
                event_type = event.get("type")
                if event_type == DailyMissionPoint.EVENT_FIGHT:
                    self.log("战斗!")
                    self.wait_until_fight_finished()
                elif event_type == DailyMissionPoint.EVENT_DESTROY:
                    self.log("破坏丘丘人柱子!")
                    self.wait_until_destroy()
                elif event_type == DailyMissionPoint.EVENT_GEER_START:
                    self.log("开启齿轮开关!")
                    self.wait_until_geer_start()
                elif event_type == DailyMissionPoint.EVENT_DEFENSE:
                    self.log("守护镇石!")
                    self.wait_until_defense_done()
                elif event_type == DailyMissionPoint.EVENT_DESTROY_AILIN:
                    self.log("艾琳要求一次性破坏木桩")
                    self.wait_until_ailin_destroy()
                elif event_type == DailyMissionPoint.EVENT_STANDING_ON_PLATE:
                    self.log("极速前进, 踩下使柱子")  # 目前做不到
                    time.sleep(5)
                elif event_type == DailyMissionPoint.EVENT_FAST_FIGHT:
                    self.log("快速战斗")
                    self.wait_until_fast_fight_finished()
                elif event_type == DailyMissionPoint.EVENT_FIND_NPC:
                    time.sleep(2)  # 等待2秒让人稳定下来，避免移动的时候对话框消失
                    self.log("查找npc")
                    time.sleep(0.5)
                    self.kb_press_and_release('f')
                    time.sleep(0.5)
                    self.kb_press_and_release('f')
                    time.sleep(0.5)
                    self.kb_press_and_release('f')
                elif event_type == DailyMissionPoint.EVENT_DIALOG:
                    self.log("对话")
                    time.sleep(1)
                    self.wait_until_dialog_finished()
                else:
                    self.log(f"暂时无法处理{event_type}类型的委托")



# 1. 按下m，然后滚轮向下把视野放大。
# 2. 模板匹配查找屏幕中的所有的任务相对于屏幕中心的坐标
# 3. 请求一次屏幕中心的世界坐标，和当前缩放
# 4. 2和3的结果做运算，得到实际坐标
# 5. 遍历实际坐标，遍历所有已存放的委托列表, 查找最近的一个委托
# 5. 执行委托

if __name__ == '__main__':
    # pos = (1282.2781718749993, -5754.44564453125)
    # t = threading.Thread(target=BGIEventHandler.start_server)
    # t.setDaemon(True)
    # t.start()
    DailyMissionPathExecutor.execute_all_mission()

