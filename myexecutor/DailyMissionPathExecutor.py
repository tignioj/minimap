import threading
import time

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
from matchmap.minimap_interface import MinimapInterface
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("daily_mission_executor")
from server.BGIWebHook import BGIEventHandler
from controller.FightController import FightController


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

# https://stackoverflow.com/questions/15562446/how-to-stop-flask-application-without-using-ctrl-c
# @app.get('/shutdown')
# def shutdown():
#     shutdown_server()
#     return 'Server shutting down...'

class DailyMissionPoint(Point):
    EVENT_DESTROY_AILIN = "destroy_ailin"  # 艾琳一次性破坏木桩
    DAILY_MISSION_TYPE_SKIP_DIALOG = 'dialog'
    DAILY_MISSION_TYPE_FIGHT = 'fight'
    DAILY_MISSION_TYPE_FAST_MOVE = 'fast_move'  # 极速前进
    DAILY_MISSION_TYPE_DESTROY_TOWER = 'destroy_tower'

    EVENT_FIGHT = 'fight'
    EVENT_STANDING_ON_PLATE = 'standing_on_plate'  # 极速前进, 要踩下机关
    EVENT_FAST_FIGHT = 'fast_fight'  # 极速前进，消灭怪物就可以加时长，要求尽快结束战斗，有各种元素类型史莱姆唯独没有风史莱姆，可以用散兵自动索敌平a
    EVENT_DESTROY = 'destroy'
    EVENT_DIALOG = 'dialog'
    EVENT_FIND_NPC = 'find_npc'
    EVENT_COLLECT = 'collect'
    EVENT_CLIMB = 'climb'  # 爬神像，做不到

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

    # @staticmethod
    # def scale_down():
    #     import win32api, win32con
    #     import time
    #     delta = -5000
    #     for _ in range(20):
    #         win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
    #         time.sleep(0.02)  # 短暂等待，防止事件过于密集

    # 1. 按下m，然后滚轮向下把视野放大。
    # @staticmethod
    # def scroll_down_for_looking_more_locations():
    #     DailyMissionPathExecutor.scale_down()

    # 2. 模板匹配查找屏幕中的所有的任务的坐标
    @staticmethod
    def find_all_mission_from_screen():
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
        original_image = cv2.resize(original_image, None, fx=0.5, fy=0.5)
        # cv2.imshow('Matched Image', original_image)
        # cv2.waitKey(20)
        # if key == ord('q'):
        #     cv2.destroyAllWindows()
        return mission_screen_points
    # 3. 请求一次屏幕中心的世界坐标，和当前缩放
    # 4. 2和3的结果做运算，得到实际坐标

    @staticmethod
    def get_world_missions(missions_screen_points):
        user_map_position = MinimapInterface.get_user_map_position()
        w,h = capture.w, capture.h
        mission_world_points = []
        for mission_screen_point in missions_screen_points:
            scale = MinimapInterface.get_user_map_scale()
            if user_map_position and scale:
                dx = mission_screen_point[0] - w/2
                dy = mission_screen_point[1] - h/2
                world_x = user_map_position[0] + dx/scale[0]
                world_y = user_map_position[1] + dy/scale[1]
                mission_world_points.append((world_x,world_y))
        return mission_world_points

    @staticmethod
    def search_closest_mission_json(target_point):
        """
        查找指定位置最近的委托
        :param target_point:
        :return:
        """
        if target_point is None:
            raise Exception("目标点不能为空")
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

    # 5. 遍历实际坐标，遍历所有已存放的委托列表, 查找最近的一个委托
    @staticmethod
    def execute_all_mission():
        from controller.MapController2 import MapController
        mp = MapController()
        mp.open_middle_map()
        time.sleep(0.8)
        mp.choose_country('蒙德')
        mp.zoom_out(-5000)
        mp.zoom_out(-5000)
        mp.zoom_out(-5000)
        time.sleep(1)

        # 模板匹配屏幕中出现的委托,得到他们的屏幕坐标
        missions_screen_points = DailyMissionPathExecutor.find_all_mission_from_screen()
        # 计算得到世界坐标
        mission_world_points = DailyMissionPathExecutor.get_world_missions(missions_screen_points)

        # 5. 执行委托
        for mission_world_point in mission_world_points:
            if DailyMissionPathExecutor.stop_listen: return
            closest = DailyMissionPathExecutor.search_closest_mission_json(mission_world_point)
            if closest is None: continue
            try:
                DailyMissionPathExecutor(closest).execute()
            except UnfinishedException as e:
                logger.error(e)
                continue

    def on_execute_before(self, from_index=None):
        self.base_path: DailyMissionPath
        if not self.base_path.enable:
            raise UnfinishedException("未完成路线，跳过")
        super().on_execute_before(from_index=from_index)

    def start_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.log('按下快捷键开始自动战斗')
        self.fight_controller.start_fighting()


    def stop_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.fight_controller.stop_fighting()

    def wait_until_fight_finished(self):
        start_time = time.time()
        time.sleep(0.5)
        self.start_fight()
        while time.time()-start_time < 40:
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{40-(time.time()-start_time)}秒")
            if self.ocr.find_match_text('委托完成'):
                break
        self.stop_fight()
    def wait_until_destroy(self):
        self.start_fight()
        start_time = time.time()
        while time.time()-start_time < 20:
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{20-(time.time()-start_time)}秒")
            if self.ocr.find_match_text('委托完成'):
                break
        self.stop_fight()

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
    from controller.MapController2 import MapController
    DailyMissionPathExecutor.execute_all_mission()

