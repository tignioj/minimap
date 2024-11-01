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

    def __nahida_e_hold(self):
        # 转圈
        self.kb_press('e')
        start_time = time.time()
        i = 0
        while time.time() - start_time < float(1):
            i += 1
            self.camera_chage(dx=-800, dy=0)
            time.sleep(0.02)
        self.kb_release('e')

    def __naweilaite_charge(self, duration):
        # 转圈
        self.ms_press(self.Button.left)
        start_time = time.time()
        y = 500
        i = 1000
        while time.time() - start_time < float(duration):
            i += 1
            if i % 5 == 0: y = -y
            self.camera_chage(dx=-500, dy=y)
            time.sleep(0.02)
        self.ms_release(self.Button.left)

    def charge(self, duration=None):
        """
        重击,也就是长按攻击
        :param duration: 持续时间
        :return:
        """
        if self.character_name == '那维莱特':
            self.__naweilaite_charge(duration)
        else: super().charge(duration=duration)

    def skill(self, hold=None):
        """
        元素战技，skill的简写
        :param hold: 是否长按元素战技
        :return:
        """
        if self.character_name == '纳西妲' and hold:
            self.__nahida_e_hold()
        else:super().skill(hold)



if __name__ == '__main__':
    fm = FightMapperImpl(character_name='那维莱特')
    # fm = FightMapperImpl(character_name='钟离')
    # fm = FightMapperImpl(character_name='纳西妲')
    fm.burst()
    # fm.wait(1)
    fm.charge(3)
    # fm.e(hold=True)
    # fm.charge(3)
    # fm.e()
    # fm.charge(3)
    # fm.e()
    # fm.charge(3)
