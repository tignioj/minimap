import threading
import time
import concurrent.futures

from fightmapper.BaseFightMapper import BaseFightMapper
from threading import Thread

# supportSkills = [
#     ['wait','wait(秒):等待多少秒'],
#     ['walk', 'walk(方向, 秒):方向包括wsad'],
#     ['j', 'jump简写，跳跃'],
#     ['jump', '跳跃'],
#     ['dash', 'dash(秒)冲刺'],
#     ['e', 'skill的别称,e技能元素战技'],
#     ['q', 'burst的别称, 元素爆发'],
#     ['skill', '元素战技，可以用字母e简写'],
#     ['w', 'w(秒)向前走多少秒'],
#     ['s', 's(秒)向后走多少秒'],
#     ['a', 'a(秒)向左走多少秒'],
#     ['d','d(s)向右走多少秒'],
#     ['burst', '元素爆发，可以用q简写'],
#     ['attack', 'attack(秒):连续攻击多少秒,不传参就是点一下'],
#     ['charge', 'charge(秒):长按攻击多少秒，特殊角色会自动处理'],
#     ['keyup', 'keyup(key):抬起按键'],
#     ['keydown', 'keydown(key):按下按键'],
#     ['keypress', 'keyprees(key):也就是先按下再松开'],
#     ['mousedown', 'mousedown(left|middle|right):按下鼠标, 不传参数就是左键left'],
#     ['mouseup', 'mouseup(left|middle|right):松开鼠标'],
#     ['click', 'click(left|middle|right):点击按钮, 不传参数就是左键left']
# ]

class FightMapperImpl(BaseFightMapper):
    def __init__(self, character_name=None):
        super().__init__()
        self.character_name = character_name

    def __circle_loop(self, duration):
        # 转圈
        t = time.time()
        while time.time() - t < float(duration):
            self.camera_chage(dx=-500, dy=0)
            time.sleep(0.02)

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

    def e(self, hold=None):
        """
        元素战技，skill的简写
        :param hold: 是否长按元素战技
        :return:
        """
        t = None
        if self.character_name == '纳西妲':
            t = threading.Thread(target=self.__circle_loop, args=(1,))
            t.start()
        self.skill(hold)
        if t: t.join()



if __name__ == '__main__':
    # fm = FightMapperImpl(character_name='那维莱特')
    fm = FightMapperImpl(character_name='纳西妲')
    fm.e(True)