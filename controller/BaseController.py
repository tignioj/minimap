import sys
import os
import time
from pynput import mouse
from pynput.mouse import Button
from pynput.keyboard import Key, Controller
from pynput import keyboard

"""
PyCharm需要用管理员方式启动，否则游戏内输入无效！
"""

from datetime import datetime
from mylogger.MyLogger3 import MyLogger
import win32api, win32con
from matchmap.minimap_interface import MinimapInterface
from capture.genshin_capture import GenShinCapture

class BaseController:

    def log(self, *args):
        if self.debug_enable:
            self.logger.info(args)

    """
    提供操作人物的方法
    """

    def __init__(self, debug_enable=False, gc = None):
        self.Key = Key
        self.tracker = MinimapInterface
        self.logger = MyLogger(self.__class__.__name__, save_log=False)
        if gc is None:
            self.gc = GenShinCapture  # genshin capture
        self.Button = Button
        self.keyboard = Controller()
        self.ms = mouse.Controller()
        self.stop_listen = False
        self.debug_enable = debug_enable
        self.kb_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.ms_listener = mouse.Listener(on_click=self._on_click)
        self.kb_listener.start()
        self.ms_listener.start()

    def _on_click(self, x, y, button, pressed):
        pass
    def ui_close_button(self):
        """
        右上角关闭按钮, 用于关闭地图、关闭烹饪界面
        :return:
        """
        pos = (self.gc.w - 60, 40)
        pos = self.gc.get_screen_position(pos)
        self.ms.position = pos
        self.ms.click(self.Button.left)


    def kb_press_and_release(self, key):
        self.kb_press(key)
        self.kb_release(key)

    def kb_press(self, key):
        """
        按下键盘
        :param key:
        :return:
        """
        # if self.stop_listen: return
        self.keyboard.press(key)

    def kb_release(self, key):
        # if self.stop_listen:
        #     return
        # 即使停止了也要释放
        # self.log(f"松开按键'{key}'")
        self.keyboard.release(key)

    def _on_press(self, key):
        try:
            c = key.char
        except AttributeError:
            # print('special key {0} pressed'.format(key))
            if key == Key.esc:
                self.log('你按下了esc退出程序')
                self.stop_listen = True

    def _on_release(self, key):
        pass

    def drag(self, position_from, dx, dy, duration_ms=200):
        """
        鼠标拖动
        :param x: 起始位置
        :param y: 终止位置
        :param dx: 水平距离
        :param dy: 垂直距离
        :param duration_ms:持续时间（毫秒）
        :return:
        """
        self.ms.position = position_from
        x, y = position_from
        finalx, finaly = x + dx, y + dy
        self.ms.press(Button.left)
        move_times = 5  # 移动次数(不要设高了，避免漂移)
        gap_time = (duration_ms / move_times) * 0.001  # 移动次数除以间隔
        gap_x = dx / move_times
        gap_y = dy / move_times
        while move_times > 0:
            time.sleep(gap_time)
            x, y = self.ms.position
            self.ms.position = (x + gap_x, y + gap_y)
            move_times -= 1
        self.ms.position = (finalx, finaly)  # 确保鼠标在最终位置
        self.ms.release(Button.left)

    def to_degree(self, degree):
        """
        将当前视角朝向转至多少度
        :param degree:
        :return:
        """
        start = time.time()
        while True:
            if time.time() - start > 2: break  # 避免超过2秒

            current_rotation = self.tracker.get_rotation()
            # 假设要求转向到45，获取的是60，则 degree - current_rotation = -15
            # 假设要求转向到45，获取的是10则 degree - current_rotation = 30
            if current_rotation is None:
                self.log("获取视角失败！")
                continue

            diff = current_rotation - degree
            # 求方向
            s = abs(diff)
            if s < 10: return

            direction = diff / abs(diff)

            if degree * current_rotation > 0:  # 同向
                # 直接做差
                s = abs(diff)
                direction = -direction
            else:  # 异向
                # 做差后得到s， 判断s是否大于180, 大于180则距离取360-s
                # 求距离
                if abs(diff) > 180:
                    s = 360 - abs(diff)
                else:
                    s = abs(diff)
                    direction = -direction

            # print(f"current: {current_rotation}, target{degree},diff{diff}, 转向:{direction}, 转动距离:{s}")
            s = s * 2
            if s > 200: s = 200
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -int(direction * s), 0, 0, 0)


if __name__ == '__main__':
    bc = BaseController(debug_enable=True)
    # bc.ui_close_button()
    # 拖动测试
    pos = bc.ms.position
    center = bc.gc.get_genshin_screen_center()
    print(bc.gc.get_genshin_screen_center())
    bc.ms.position = center
    time.sleep(0.1)
    # scale_x = bc.gc.w / 2 / 2349
    # scale_y = bc.gc.h / 2 / 1303
    scale_x = bc.gc.w / 2 / 2019
    scale_y = bc.gc.h / 2 / 1120
    dx,dy = 168, 220
    anchor_x = center[0] - dx * scale_x
    anchor_y = center[1] - dy * scale_y
    print(scale_x, scale_y)
    bc.ms.position = (anchor_x, anchor_y)

    # Logger.log("good", instance=BaseController)
    # bc.drag(GenShinCapture.get_genshin_screen_center(),1000, 200, 500)
    # bc.ms.position = (3858.0, 2322.0)
    # bc.ms.click(Button.left)
