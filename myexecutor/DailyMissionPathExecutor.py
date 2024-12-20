import time
from controller.BaseController import StopListenException
from controller.MapController2 import MapController

# 委托流程：
# 已知委托的地点都是固定的

# 保存委托
# 把所有的委托全部存起来，用json文件存放

from myexecutor.BasePathExecutor2 import BasePathExecutor, Point, BasePath, ExecuteTerminateException
import os,cv2
import numpy as np
from typing import List
import json
from capture.capture_factory import capture
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("daily_mission_executor")
from controller.FightController import FightController, CharacterDieException
from myutils.configutils import DailyMissionConfig

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
# 诗歌交流


# 目前仅能完部分的战斗委托, 并且比较依赖那维莱特、水神
# 如果队伍伤害不够可能还得再来一遍

class UnfinishedException(Exception): pass  # 只录制了一半的委托
class DailyMissionPathExecutorException(Exception): pass

# https://stackoverflow.com/questions/15562446/how-to-stop-flask-application-without-using-ctrl-c
# @app.get('/shutdown')
# def shutdown():
#     shutdown_server()
#     return 'Server shutting down...'

class Event:
    def __init__(self, event_type, targets=None):
        self.type = event_type,
        self.targets = targets

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
    EVENT_GEAR_START = 'gear_start'  # 开启齿轮机关

    def __init__(self, x, y, type=Point.TYPE_PATH, move_mode=Point.MOVE_MODE_NORMAL, action=None, event=None):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        self.event = event

class DailyMissionPath(BasePath):
    def __init__(self, name, country, positions: List[DailyMissionPoint], anchor_name=None, enable=None):
        super().__init__(name=name, country=country, positions=positions, anchor_name=anchor_name)
        self.enable = enable
        self.mission_position_index = -1  # 默认情况下取最后一个点位作为委托在地图上的位置
        self.note = None  # 自定义备注
        # TODO：指定委托所在的位置，用于搜索；对于战斗类型通常是最后一个点的位置，其他的不一定
        # self.mission_position = None  #

class DailyMissionPathExecutor(BasePathExecutor):

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
                                      action=point.get('action'),
                                      event=point.get('event'))
                points.append(p)
            return DailyMissionPath(name=json_dict.get('name', 'undefined'),
                            country=json_dict.get('country','蒙德'),
                            positions=points,
                            anchor_name=json_dict.get('anchor_name', '传送锚点'),
                            enable=json_dict.get('enable', True))

    # 2. 模板匹配查找屏幕中的所有的任务的坐标
    # 3. 请求一次屏幕中心的世界坐标，和当前缩放
    # 4. 2和3的结果做运算，得到实际坐标

    # def __init__(self, json_file_path=None, fight_team:str=None, fight_timeout:int=None, debug_enable=None):
    #     super().__init__(json_file_path=json_file_path, fight_team=fight_team, fight_duration=fight_timeout, debug_enable=debug_enable)



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
        if min_distance > 70: return None  # 丢弃距离过远的委托
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
        missions_screen_points = capture.get_icon_position(capture.icon_daily_mission)
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
        map_controller.teleport((x, y), country, "七天神像", start_teleport_time=time.time())


    # 5. 遍历实际坐标，遍历所有已存放的委托列表, 查找最近的一个委托
    @staticmethod
    def execute_all_mission(emit=lambda val1,val2:None):  # 传一个空实现的方法，免去判断函数是否为空
        from server.service.DailyMissionService import SOCKET_EVENT_DAILY_MISSION_UPDATE, SOCKET_EVENT_DAILY_MISSION_END
        from controller.MapController2 import MapController
        from myutils.configutils import FightConfig, DailyMissionConfig

        # 读取委托配置
        daily_task_execute_timeout = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_EXECUTE_TIMEOUT, 500, min_val=60, max_val=3600)

        # 单次战斗超时配置
        fight_timeout = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TIMEOUT)
        if fight_timeout is None: fight_timeout = FightConfig.get(FightConfig.KEY_FIGHT_TIMEOUT, 12, min_val=1, max_val=1000)
        if fight_timeout is None: fight_timeout = 20

        # 战斗队伍配置
        from controller.UIController import TeamUIController, TeamNotFoundException
        tuic = TeamUIController()
        tuic.last_selected_team = None

        fight_team = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TEAM)
        if fight_team is None or len(fight_team) == 0: fight_team = FightConfig.get(
            FightConfig.KEY_DEFAULT_FIGHT_TEAM)
        if fight_team is None:
            emit(SOCKET_EVENT_DAILY_MISSION_END, f'请先配置队伍')
            raise Exception("请先配置队伍!")

        map_controller = MapController()
        start_time = time.time()
        try:
            # 循环执行委托，直到完成
            closet_missions = DailyMissionPathExecutor.get_screen_world_mission_json(map_controller)
            if len(closet_missions) > 0:  # 当检测到有委托才切换队伍，否则不切换
                # 切换队伍
                try:
                    tuic.navigation_to_world_page()
                    tuic.switch_team(fight_team)
                    tuic.navigation_to_world_page()
                except TeamNotFoundException as e:
                    emit(SOCKET_EVENT_DAILY_MISSION_END, str(e.args))

            while len(closet_missions) > 0:  # 不断执行委托直到屏幕上查找到的战斗委托为空
                msg = f"查找到战斗委托:{closet_missions}"
                logger.debug(msg)
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, msg)
                if time.time() - start_time > daily_task_execute_timeout: raise ExecuteTimeOutException("已超时!")
                for closest in closet_missions:
                    msg = f"开始执行战斗委托:{closest}"
                    logger.debug(msg)
                    emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, msg)

                    de = DailyMissionPathExecutor(json_file_path=closest, fight_team=fight_team, fight_duration=fight_timeout)
                    de.execute()

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

    def wait_until_fight_finished(self):
        daily_task_fight_timeout = DailyMissionConfig.get(
            DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TIMEOUT, default=20, min_val=10, max_val=400)

        start_time = time.time()
        time.sleep(0.5)
        # 有些委托一开始是检测不到战斗状态的，因此禁用 '检测脱战状态则结束战斗'的功能
        # 例如奔狼领的小宝，活动范围非常广，必须要在原地战斗一会才能吸引小宝的仇恨
        # 而且委托有特殊的检测结束机制, 就是判断绿色的对勾
        self.start_fight(stop_on_no_enemy=False)
        while time.time()-start_time < daily_task_fight_timeout:
            if self.stop_listen: break
            time.sleep(0.2)
            self.log(f"正在检测委托是否完成, 剩余{daily_task_fight_timeout-(time.time()-start_time)}秒")
            if self.fight_controller.stop_fight:
                self.log('已经停止战斗')
                break

            if self.gc.has_mission_ok():
                self.log("检测到绿色小箭头，委托已完成!")
                break
            # cv2.imwrite(f'mission{time.time()}.jpg', capture.screenshot)
            # if len(self.ocr.find_match_text('委托完成'))>0:
            #     cv2.imwrite('mission_ok.jpg', capture.screenshot)
        self.stop_fight()

    def wait_until_destroy(self):
        daily_task_destroy_timeout = DailyMissionConfig.get(
            DailyMissionConfig.KEY_DAILY_TASK_DESTROY_TIMEOUT, default=20, min_val=10, max_val=400)

        self.start_fight(stop_on_no_enemy=False)
        start_time = time.time()
        while time.time()-start_time < daily_task_destroy_timeout:
            if self.stop_listen: break
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{daily_task_destroy_timeout -(time.time()-start_time)}秒")
            if len(self.ocr.find_match_text('委托完成'))>0: break
        self.stop_fight()

    def on_nearby(self, coordinates):
        if self.next_point.type == DailyMissionPoint.TYPE_TARGET:
            if (self.next_point.event == DailyMissionPoint.EVENT_GEAR_START or
                    self.next_point.event == DailyMissionPoint.EVENT_DEFENSE):
                if self.gc.has_gear():
                    self.log('nearby:发现齿轮，疯狂f')
                    self.kb_press_and_release('f')

    def wait_until_gear_start(self):
        stat_time = time.time()
        while self.gc.has_gear() and time.time() - stat_time < 5:
            if self.stop_listen: break
            self.logger.debug("wait:发现齿轮, 狂按f")
            self.kb_press_and_release('f')
            time.sleep(0.02)

    def wait_until_defense_done(self):
        self.wait_until_fight_finished()


    def wait_until_ailin_destroy(self):
        """
        需要切人，要求一次性打掉木桩
        :return:
        """
        pass

    def on_move_before(self, point: DailyMissionPoint):
        # 战斗前自动开盾
        if (point.event == DailyMissionPoint.EVENT_DEFENSE or
                point.event == point.EVENT_FIGHT or
                point.event == point.EVENT_DESTROY):
            try:
                self.fight_controller.shield()
            except CharacterDieException as e:
                self.logger.error(e.args)
                from controller.MapController2 import MapController
                MapController().go_to_seven_anemo_for_revive()
                raise ExecuteTerminateException()
        super().on_move_before(point)

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
        # super().on_move_after(point)
        # 禁用f避免进入对话
        if point.action == point.ACTION_SHIELD:
            self.shield()

        if point.type == DailyMissionPoint.TYPE_TARGET:
            event_type = self.next_point.event.get('type')
            if event_type == DailyMissionPoint.EVENT_FIGHT:
                self.log("战斗!")
                self.wait_until_fight_finished()
            elif event_type == DailyMissionPoint.EVENT_DESTROY:
                self.log("破坏丘丘人柱子!")
                self.wait_until_destroy()
            elif event_type == DailyMissionPoint.EVENT_GEAR_START:
                self.log("开启齿轮开关!")
                self.wait_until_gear_start()
            elif event_type == DailyMissionPoint.EVENT_DEFENSE:
                self.log("守护镇石!")
                self.wait_until_gear_start()  # 开启挑战
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

