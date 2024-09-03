"""
打怪执行器
"""
import sys
import time

from myexecutor.BasePathExecutor2 import BasePathExecutor
from server.BGIWebHook import BGIEventHandler
import threading
from controller.FightController import FightController

class FightPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path, debug_enabled=None):
        super().__init__(json_file_path=json_file_path, debug_enable=debug_enabled)
        self.fight_controller = FightController()

    def start_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.log('按下快捷键开始自动战斗')
        threading.Thread(target=self.fight_controller.execute_infinity).start()
        # while not BGIEventHandler.is_fighting:
        #     self.kb_press_and_release('`')
        #     time.sleep(1)

    def stop_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.log('按下快捷键停止自动战斗')
        self.fight_controller.stop_fight = True
        # while BGIEventHandler.is_fighting:
        #     self.kb_press_and_release('`')
        #     time.sleep(1)

    def on_nearby(self, coordinates):
        pass  #  啥也不干，屏蔽掉父类的疯狂f

    def wanye_pickup(self):
        time.sleep(1)  # 等待脚本结束
        # 切万叶
        self.logger.debug("万叶拾取中")
        self.fight_controller.switch_character('枫原万叶')
        time.sleep(0.1)

        # 万叶长e
        self.logger.debug('万叶长e')
        self.kb_press('e')
        time.sleep(1)
        self.kb_release('e')
        # 下落攻击
        time.sleep(0.02)
        self.mouse_left_click()  # 不知道为什么有时候下落攻击失败，多a几次
        time.sleep(0.02)
        self.mouse_left_click()
        time.sleep(0.2)
        for i in range(25):  # 疯狂f
            time.sleep(0.1)
            self.crazy_f()
        self.logger.debug("万叶拾取结束")

    def on_move_after(self, point):
        if point.type == point.TYPE_TARGET:
            self.start_fight()
            time.sleep(12)
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
    from myutils.jsonutils import getjson_path_byname
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

