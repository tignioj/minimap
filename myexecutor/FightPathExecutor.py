"""
打怪执行器
"""
import sys
import time
import json
from myexecutor.BasePathExecutor2 import BasePathExecutor, BasePath, Point
from typing import List
from controller.FightController import FightController


class FightPath(BasePath):
    def __init__(self, name, country, positions: List[Point], anchor_name=None, fight_team=None):
        super().__init__(name=name, country=country, positions=positions, anchor_name=anchor_name)
        self.fight_team = fight_team


class FightPoint(Point): pass


from myutils.configutils import get_config, YAML_KEY_DEFAULT_FIGHT_TEAM, YAML_KEY_DEFAULT_FIGHT_DURATION


class FightPathExecutorException(Exception): pass


class FightPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path, debug_enabled=None):
        self.base_path: FightPath = None
        super().__init__(json_file_path=json_file_path, debug_enable=debug_enabled)
        self.fight_controller = FightController(self.base_path.fight_team)
        self.fight_duration = get_config(YAML_KEY_DEFAULT_FIGHT_DURATION, 12)
        if self.fight_duration < 1:
            self.fight_duration = 1
        elif self.fight_duration > 1000:
            self.fight_duration = 1000

    @staticmethod
    def load_basepath_from_json_file(json_file_path) -> FightPath:
        with open(json_file_path, encoding="utf-8") as r:
            json_dict = json.load(r)
            points: List[Point] = []
            for point in json_dict.get('positions', []):
                p = Point(x=point.get('x'),
                          y=point.get('y'),
                          type=point.get('type', Point.TYPE_PATH),
                          move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                          action=point.get('action'))
                points.append(p)
                fight_team = json_dict.get('fight_team')
                if fight_team is None: fight_team = get_config(YAML_KEY_DEFAULT_FIGHT_TEAM)
                if fight_team is None: raise FightPathExecutorException("请先配置队伍!")
            return FightPath(name=json_dict.get('name', 'undefined'),
                             country=json_dict.get('country', '蒙德'),
                             positions=points,
                             anchor_name=json_dict.get('anchor_name', '传送锚点'),
                             fight_team=fight_team)

    def start_fight(self):
        self.log(f'按下快捷键开始自动战斗{self.fight_controller.team_name}')
        self.fight_controller.start_fighting()

    def stop_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.log('按下快捷键停止自动战斗')
        self.fight_controller.stop_fighting()

    def on_nearby(self, coordinates):
        pass  # 啥也不干，屏蔽掉父类的疯狂f

    def wanye_pickup(self):
        # 切万叶
        self.logger.debug("万叶拾取中")
        self.fight_controller.switch_character('枫原万叶')
        time.sleep(0.1)
        # 万叶长e
        self.logger.debug('万叶长e')
        self.fight_controller.fight_mapper.e(hold=True)
        # 下落攻击
        # 不知道为什么有时候下落攻击失败，多a几次
        self.fight_controller.fight_mapper.attack(0.4)
        for i in range(25):  # 疯狂f
            time.sleep(0.1)
            self.crazy_f()
        self.logger.debug("万叶拾取结束")

    def on_move_after(self, point):
        if point.type == point.TYPE_TARGET:
            self.start_fight()
            time.sleep(self.fight_duration)
            self.stop_fight()
            time.sleep(0.1)
            self.wanye_pickup()

    def on_execute_before(self, from_index=None):
        super().on_execute_before(from_index=from_index)
        # self.logger.debug("开始监听BGI事件")
        # t = threading.Thread(target=BGIEventHandler.start_server)  # 监听BGI事件
        # t.setDaemon(True)  # 子线程随主线程一同关闭
        # t.start()


if __name__ == '__main__':
    from myutils.fileutils import getjson_path_byname

    # FightPathExecutor(getjson_path_byname('丘丘萨满_望风角_蒙德_3个_20240821_204922.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_望风山地_蒙德_2个_20240822_000003.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_望风山地2_蒙德_2个_20240822_001412.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_摘星崖_蒙德_1个_20240822_002554.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_千风神殿左下_蒙德_1个_20240822_005716.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_千风神殿左下2_蒙德_1个_20240822_014208.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_千风神殿下_蒙德_1个_20240822_014632.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_鹰翔海滩_蒙德_1个_20240822_014932.json')).execute()

    FightPathExecutor(getjson_path_byname('丘丘萨满_覆雪之路右上_蒙德_1个_20240822_124317.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_覆雪之路右上2_蒙德_2个_20240822_125149.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_清泉镇右下_蒙德_1个_20240822_125927.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_清泉镇左下_蒙德_2个_20240822_130931.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_奔狼领右_蒙德_2个_20240822_132055.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_奔狼领右上_蒙德_1个_20240822_132448.json')).execute()
