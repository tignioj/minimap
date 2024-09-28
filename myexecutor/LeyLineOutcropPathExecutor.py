import threading
import time
from controller.BaseController import StopListenException
from controller.MapController2 import MapController, LocationException
from myexecutor.BasePathExecutor2 import BasePathExecutor, Point, BasePath, ExecuteTerminateException
import os,cv2
import numpy as np
from typing import List
import json
from capture.capture_factory import capture
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("leyline_outcrop_executor")
from controller.FightController import FightController, CharacterDieException
from myutils.configutils import LeyLineConfig
class MoveToLocationTimeoutException(Exception): pass

# TODO: 委托会挡住图标, 只能放大

class ExecuteTimeOutException(Exception): pass

# 树脂耗尽
class NoResinException(Exception): pass


class LeyLineOutcropPoint(Point):
    ACTION_FIGHT = 'fight'  # 战斗地点
    ACTION_REWARD = 'reward'  # 领取奖励的点

    def __init__(self, x, y, type=Point.TYPE_PATH, move_mode=Point.MOVE_MODE_NORMAL, action=None, events=None):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        self.events = events

class LeyLineOutcropPath(BasePath):
    def __init__(self, name, country, positions: List[LeyLineOutcropPoint], anchor_name=None):
        super().__init__(name=name, country=country, positions=positions, anchor_name=anchor_name)

class LeyLineOutcropPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path, debug_enable=None, fight_team=None, fight_duration=None):
        super().__init__(json_file_path=json_file_path, debug_enable=debug_enable,
                         fight_team=fight_team, fight_duration=fight_duration)
        self.reward_ok = False

    LEYLINE_TYPE_MONEY = 'money'
    LEYLINE_TYPE_EXPERIENCE = 'experience'

    @staticmethod
    def load_basepath_from_json_file(json_file_path) -> LeyLineOutcropPath:
        with open(json_file_path, encoding="utf-8") as r:
            json_dict = json.load(r)
            points: List[LeyLineOutcropPoint] = []
            for point in json_dict.get('positions', []):
                p = LeyLineOutcropPoint(x=point.get('x'),
                          y=point.get('y'),
                          type=point.get('type', Point.TYPE_PATH),
                          move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                          action=point.get('action'),events=point.get('events'))
                points.append(p)
            return LeyLineOutcropPath(
                name=json_dict['name'], country=json_dict['country'], positions=points,
                anchor_name=json_dict['anchor_name'],
            )

    __leyline_type = None

    # 2. 模板匹配屏幕上的图标
    # 3. 请求一次屏幕中心的世界坐标，和当前缩放
    # 4. 2和3的结果做运算，得到实际坐标

    @staticmethod
    def get_specify_point_closest_mission_json(target_point):
        """
        查找指定位置最近的json任务
        :param target_point:
        :return:
        """
        if target_point is None: raise Exception("目标点不能为空")

        from myutils.executor_utils import euclidean_distance
        from myutils.configutils import resource_path
        # 经验和摩拉都是一样的路径，只是图标不一样
        mission_path = os.path.join(resource_path, 'pathlist', '地脉')

        closet_mission_json = None
        min_distance = None
        for mission_file_name in os.listdir(mission_path):
            with open(os.path.join(mission_path, mission_file_name), encoding='utf-8') as f:
                dme = json.load(f)
                # 地脉位置在倒数第二个点
                # 倒数第一个点是领取奖励的位置
                mission_point = dme.get('positions')[-1]
                d = euclidean_distance(target_point, (mission_point['x'], mission_point['y']))
                if min_distance is None:
                    min_distance = d
                    closet_mission_json = os.path.join(mission_path, mission_file_name)
                    continue

                if min_distance > d:
                    min_distance = d
                    closet_mission_json = os.path.join(mission_path, mission_file_name)
        if min_distance > 100: return None  # 丢弃距离过远的任务
        return closet_mission_json

    @staticmethod
    def move_map_to(map_controller,point, start_time):
        try:
            map_controller.move_to_point(point)
        except LocationException as e:
            logger.error(f'移动过程中出现问题:{e.args}, 递归重试中')
            map_controller.close_middle_map()
            map_controller.open_middle_map()
            map_controller.choose_country('蒙德')
            if time.time() - start_time > 30: raise MoveToLocationTimeoutException("移动超时！")

    @staticmethod
    def get_closet_leyline_outcrop(map_controller):
        closet_missions = []
        map_controller.scales_adjust(0.38)
        # 模板匹配屏幕中出现的地脉图标,得到他们的屏幕坐标

        if LeyLineOutcropPathExecutor.__leyline_type == 'money': gray_template = capture.icon_dimai_money
        else: gray_template = capture.icon_dimai_exp
        missions_screen_points = capture.get_icon_position(gray_template)
        # 计算得到世界坐标
        mission_world_points = map_controller.get_world_coordinate(missions_screen_points)
        for mission_world_point in mission_world_points:
            closest:str = LeyLineOutcropPathExecutor.get_specify_point_closest_mission_json(mission_world_point)
            if closest is None: continue
            closet_missions.append(closest)
        return closet_missions

    @staticmethod
    def get_screen_world_mission_json(map_controller:MapController):
        """
        逐个七天神像查找屏幕中出现的地脉事件
        :param map_controller:
        :return:
        """
        # 打开地图
        # map_controller.open_middle_map()
        # time.sleep(0.8)
        # 前往清泉镇的七天神像，将地图缩放拉到最小后,可以看到尽可能多的地脉任务
        # 必须要传送的原因：如果某个地脉没打完，人物还站在原地，打开地图时，人物会遮挡当前未完成的地脉
        # map_controller.choose_country('蒙德')

        map_controller.open_middle_map()  # 再次打开地图
        # 先查当前大地图有没有地脉，没有则回神像逐个检测
        leyline_outcrop = LeyLineOutcropPathExecutor.get_closet_leyline_outcrop(map_controller)
        if len(leyline_outcrop) == 0:
            LeyLineOutcropPathExecutor.go_to_seven_anemo(map_controller)
            map_controller.open_middle_map()  # 再次打开地图
            time.sleep(1)
        else: return leyline_outcrop

        # 查找最近的地脉
        # 这里是蒙德清泉镇地脉
        leyline_outcrop = LeyLineOutcropPathExecutor.get_closet_leyline_outcrop(map_controller)

        if len(leyline_outcrop) == 0:
            # 星落湖像查找
            x, y = 4046.090671875001,-6906.5086328
            logger.debug("前往星落湖查找")
            LeyLineOutcropPathExecutor.move_map_to(map_controller, (x,y), time.time())
            leyline_outcrop = LeyLineOutcropPathExecutor.get_closet_leyline_outcrop(map_controller)


        if len(leyline_outcrop) == 0:
            # 风龙废墟查找
            logger.debug("前往风龙废墟查找")
            x, y = 253.69223437500114, -7079.59408203
            LeyLineOutcropPathExecutor.move_map_to(map_controller, (x,y), time.time())
            leyline_outcrop = LeyLineOutcropPathExecutor.get_closet_leyline_outcrop(map_controller)

        if len(leyline_outcrop) == 0:
            # 雪山查找
            x, y = 3460.412937500, -2891.8816
            logger.debug("前往雪山查找")
            LeyLineOutcropPathExecutor.move_map_to(map_controller, (x,y), time.time())
            leyline_outcrop = LeyLineOutcropPathExecutor.get_closet_leyline_outcrop(map_controller)

        return leyline_outcrop


    @staticmethod
    def go_to_seven_anemo(map_controller:MapController):
        x,y, country = 1944.8270,-4954.61, "蒙德"
        logger.debug("前往清泉镇七天神像")
        map_controller.teleport((x, y), country, "七天神像")

    @staticmethod
    def execute_all_mission(leyline_type='money',emit=lambda val1,val2:None):  # 传一个空实现的方法，免去判断函数是否为空
        logger.debug(f'地脉类型：{leyline_type}')
        LeyLineOutcropPathExecutor.__leyline_type = leyline_type
        from server.service.LeyLineOutcropService import SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE, SOCKET_EVENT_LEYLINE_OUTCROP_END
        leyline_execute_timeout:int = LeyLineConfig.get(
            LeyLineConfig.KEY_LEYLINE_OUTCROP_TASK_EXECUTE_TIMEOUT, default=500, min_val=60, max_val=3600)

        start_time = time.time()
        try:

            map_controller = MapController()
            map_controller.open_middle_map()
            map_controller.turn_off_custom_tag()

            closet_missions = LeyLineOutcropPathExecutor.get_screen_world_mission_json(map_controller)
            while len(closet_missions) > 0:  # 不断执行委托直到屏幕上查找到的战斗委托为空
                msg = f"查找到地脉:{closet_missions}"
                logger.debug(msg)
                emit(SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE, msg)
                if time.time() - start_time > leyline_execute_timeout: raise ExecuteTimeOutException("已超时!")
                for closest in closet_missions:
                    msg = f"开始执行地脉任务:{closest}"
                    logger.debug(msg)
                    emit(SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE, msg)
                    LeyLineOutcropPathExecutor(closest).execute()  # 可能会抛出体力耗尽异常
                closet_missions = LeyLineOutcropPathExecutor.get_screen_world_mission_json(map_controller)

        except MoveToLocationTimeoutException as e:
            logger.error('移动地图超时！')
            emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, f'{e.args}')
        except ExecuteTimeOutException as e:
            logger.error("超时结束")
            emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, f'{e.args}')
        except StopListenException:
            logger.debug('停止监听结束')
            emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, f'手动强制结束执行地脉任务')
        except NoResinException as e:
            logger.debug(e)
            emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, f'{e.args}')

        msg = f"执行地脉任务结束, 总时长{time.time() - start_time}"
        emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, msg)
        logger.debug(msg)

    def wait_until_fight_finished(self):
        leyline_fight_timeout = LeyLineConfig.get(
            LeyLineConfig.KEY_LEYLINE_OUTCROP_TASK_FIGHT_TIMEOUT, default=20, min_val=10,max_val=400)
        start_time = time.time()
        time.sleep(0.5)
        # 地脉战斗结束可以检测奖励花，无需检测敌人
        self.start_fight(stop_on_no_enemy=False)
        while time.time()-start_time < leyline_fight_timeout:
            if self.stop_listen: return
            time.sleep(1)
            self.log(f"正在检测地脉任务是否完成, 剩余{leyline_fight_timeout-(time.time()-start_time)}秒")
            if self.gc.has_reward():
                logger.debug('检测到地脉奖励图标, 停止战斗')
                break

            # sc = self.gc.get_screenshot()
            # cv2.imwrite(f'sc_{int(time.time())}.jpg', sc)
            # if len(self.ocr.find_match_text('挑战达成'))>0: break
        self.stop_fight()

    def on_nearby(self, coordinate):
        if self.next_point.type == LeyLineOutcropPoint.TYPE_TARGET:
            # if self.next_point.action == LeyLineOutcropPoint.ACTION_FIGHT:
            #     if self.gc.has_gear():
            #         self.log("nearby:发现齿轮")
            #         self.kb_press_and_release('f')  # 记录的路径没有篝火，直接f就行
            # elif self.next_point.action == LeyLineOutcropPoint.ACTION_REWARD:
            #     # 怪物掉落材料太多可能会遮挡钥匙图标, 所以还不如直接判断reward图标
            #     # if self.gc.has_reward():
            #     #     self.log("nearby:发现奖励图标")
                self.log('nearby:疯狂f同时判断树脂图标')
                self.kb_press_and_release('f')  # 记录的路径没有篝火，直接f就行
                self.click_use_resin()



    def on_move_before(self, point: LeyLineOutcropPoint):
        # 战斗前自动开盾
        if point.action == point.ACTION_FIGHT:
            self.shield()
        super().on_move_before(point)

    def click_use_resin(self):
        if self.click_if_appear(self.gc.icon_button_condensed_resin):
            self.logger.debug('成功点击浓缩树脂图标')
            self.reward_ok = True
        elif self.click_if_appear(self.gc.icon_button_original_resin):
            self.logger.debug('成功点击原粹树脂图标, 判断是否需要补充树脂')
            try:
                if self.click_if_appear(self.gc.icon_message_box_button_cancel, timeout=1):
                    self.logger.debug("成功点击取消按钮,说明树脂已经消耗完毕")
                    raise NoResinException("树脂消耗完毕")
                else:
                    self.logger.debug("没有找到取消按钮,点击原粹树脂图标成功")
                    self.reward_ok = True
            except TimeoutError:
                self.logger.debug("超时:没有找到取消按钮,使用原粹树脂领取成功")
                self.reward_ok = True
            # original_resin_positions = self.gc.get_icon_position(self.gc.icon_button_original_resin)
            # if len(original_resin_positions) > 0:
            #     self.logger.debug(f'发现原粹树脂图标，位置{original_resin_positions}')
            #     original_resin_position = original_resin_positions[0]
            #     if original_resin_position[0] < self.gc.w//2: # 按钮如果在左边则认为树脂完全消耗
            #         self.logger.debug('原粹树脂图标的x坐标小于屏幕的一半')
            #         raise NoResinException("树脂消耗完毕")
            #     else:
            #         self.click_screen(original_resin_position)
            #         self.logger.debug('成功点击原粹树脂图标')
            #         self.reward_ok = True



    def on_move_after(self, point: LeyLineOutcropPoint):
        if point.action == point.ACTION_SHIELD:
            self.fight_controller.shield()

        if point.type == LeyLineOutcropPoint.TYPE_TARGET:
            if point.action == LeyLineOutcropPoint.ACTION_FIGHT:
                self.crazy_f()
                # 开启地脉
                # 战斗
                if not self.gc.has_reward() and not self.gc.has_key():
                    self.wait_until_fight_finished()
                    self.logger.debug("战斗结束")
            elif point.action == LeyLineOutcropPoint.ACTION_REWARD:
                self.logger.debug("到达领取奖励的地点")
                # 前往领取奖励的点(地脉开启位置未必和领取奖励的位置相同)
                # 只拾取一次可能只拿到了怪物的掉落材料而无法领取奖励
                start_pick_time = time.time()
                while not self.reward_ok and time.time()-start_pick_time < 5:
                    self.log("after:疯狂f领取奖励")
                    self.kb_press_and_release('f')
                    self.click_use_resin()
                    time.sleep(0.02)

                if self.reward_ok and LeyLineConfig.get(
                        LeyLineConfig.KEY_LEYLINE_ENABLE_WANYE_PICKUP_AFTER_REWARD, True):
                        self.fight_controller.wanye_pickup()  # 万叶拾取




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
    LeyLineOutcropPathExecutor.execute_all_mission(leyline_type=LeyLineOutcropPathExecutor.LEYLINE_TYPE_EXPERIENCE)

