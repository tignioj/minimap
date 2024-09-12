import threading
import time
import concurrent.futures

from fightmapper.BaseFightMapper import BaseFightMapper
from threading import Thread


class CharacterSkillWithCodeDuration:
    name:str = None
    e_cd:float = 0
    # 上次释放e技能时间
    e_last_exec_time:float = 0

    # 上次释放q技能时间
    q_cd:float = 0
    q_last_exec_time:float = 0



class FightMapperImpl(BaseFightMapper):
    def __init__(self, character_name=None):
        super().__init__()
        self.character_name = character_name


    def __circle_loop(self, duration):
        # 转圈
        t = time.time()
        y = 1000
        i = 0
        while time.time() - t < float(duration):
            i += 1
            if i % 10 == 0: y = -y
            self.camera_chage(dx=-500, dy=y)
            time.sleep(0.02)

    # def up_down_grab_leaf(self):
    #     time.sleep(0.5)
    #     x, y = 0, -1000  # y代表垂直方向上的视角移动, x为水平方向
    #     i = 40
    #     # self.kb_press('w')  # 飞行
    #     while i > 0 and not self.stop_listen:
    #         if i % 10 == 0:
    #             y = -y
    #         i -= 1
    #         self.logger.debug("上下晃动视角中")
    #         win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, y, 0, 0)
    #         time.sleep(0.04)


    def charge(self, duration=None):
        """
        重击,也就是长按攻击
        :param duration: 持续时间
        :return:
        """
        t = None
        if self.character_name == '那维莱特':
            t = threading.Thread(target=self.__circle_loop, args=(duration,))
            t.start()
        super().charge(duration=duration)
        if t: t.join()

    def skill(self, hold=None):
        """
        元素战技，skill的简写
        :param hold: 是否长按元素战技
        :return:
        """
        t = None
        if self.character_name == '纳西妲' and hold:
            t = threading.Thread(target=self.__circle_loop, args=(1,))
            t.start()
        super().skill(hold)
        if t: t.join()



if __name__ == '__main__':
    # fm = FightMapperImpl(character_name='那维莱特')
    fm = FightMapperImpl(character_name='钟离')
    fm.kb_press('w')
    time.sleep(1)
    fm.s(0.1)
    # fm = FightMapperImpl(character_name='芙宁娜')
    fm.e(hold=True)
    # fm.charge(3)