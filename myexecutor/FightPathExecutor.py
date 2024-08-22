"""
打怪执行器
"""
import sys
import time

from myexecutor.BasePathExecutor2 import BasePathExecutor
from server.BGIWebHook import BGIEventHandler

class FightPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path, debug_enabled=None):
        super().__init__(json_file_path=json_file_path, debug_enable=debug_enabled)

    def start_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.log('按下快捷键开始自动战斗')
        while not BGIEventHandler.is_fighting:
            self.kb_press_and_release('`')
            time.sleep(1)

    def stop_fight(self):
        """
        进入战斗, 目前只能调用BGI的自动战斗, 这里我设置了快捷键
        :return:
        """
        self.log('按下快捷键停止自动战斗')
        while BGIEventHandler.is_fighting:
            self.kb_press_and_release('`')
            time.sleep(1)

    def wanye_pickup(self):
        time.sleep(1)  # 等待脚本结束
        # 跳跃一下打断所有动作
        self.kb_press_and_release(self.Key.space)
        time.sleep(0.5)
        # 切万叶
        self.kb_press_and_release('1')
        time.sleep(0.5)

        # 万叶长e
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

    def on_move_after(self, point):
        if point.type == point.TYPE_TARGET:
            self.start_fight()
            time.sleep(12)
            self.stop_fight()
            time.sleep(0.1)
            self.wanye_pickup()


if __name__ == '__main__':
    from myutils.jsonutils import getjson_path_byname
    import threading
    t = threading.Thread(target=BGIEventHandler.start_server)  # 监听BGI事件
    t.start()
    FightPathExecutor(getjson_path_byname('丘丘萨满_望风角_蒙德_3个_20240821_204922.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_望风山地_蒙德_2个_20240822_000003.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_望风山地2_蒙德_2个_20240822_001412.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_摘星崖_蒙德_1个_20240822_002554.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_千风神殿左下_蒙德_1个_20240822_005716.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_千风神殿左下2_蒙德_1个_20240822_014208.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_千风神殿下_蒙德_1个_20240822_014632.json')).execute()
    FightPathExecutor(getjson_path_byname('丘丘萨满_鹰翔海滩_蒙德_1个_20240822_014932.json')).execute()
    #
    # FightPathExecutor(getjson_path_byname('丘丘萨满_覆雪之路右上_蒙德_1个_20240822_124317.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_覆雪之路右上2_蒙德_2个_20240822_125149.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_清泉镇右下_蒙德_1个_20240822_125927.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_清泉镇左下_蒙德_2个_20240822_130931.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_奔狼领右_蒙德_2个_20240822_132055.json')).execute()
    # FightPathExecutor(getjson_path_byname('丘丘萨满_奔狼领右上_蒙德_1个_20240822_132448.json')).execute()

    BGIEventHandler.shutdown_server()
