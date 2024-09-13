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


    def __circle_loop(self, duration, updown=False):
        # 转圈
        t = time.time()
        if updown: y = 1500
        else: y = 0
        i = 0
        while time.time() - t < float(duration):
            i += 1
            if i % 5 == 0: y = -y
            self.camera_chage(dx=-500, dy=y)
            time.sleep(0.02)

    def charge(self, duration=None):
        """
        重击,也就是长按攻击
        :param duration: 持续时间
        :return:
        """
        t = None
        if self.character_name == '那维莱特':
            t = threading.Thread(target=self.__circle_loop, args=(duration,True,))
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
            t = threading.Thread(target=self.__circle_loop, args=(1,False))
            t.start()
        super().skill(hold)
        if t: t.join()



if __name__ == '__main__':
    fm = FightMapperImpl(character_name='那维莱特')
    # fm = FightMapperImpl(character_name='钟离')
    # fm = FightMapperImpl(character_name='纳西妲')
    fm.e(hold=True)
    fm.charge(3)
    # fm.e()
    fm.charge(3)
    # fm.e()
    fm.charge(3)
    # fm.e()
    fm.charge(3)
