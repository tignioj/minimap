import sys
import os
import threading
import time
from pynput import mouse
from pynput.mouse import Button
from pynput.keyboard import Key, Controller
from pynput import keyboard

"""
PyCharm需要用管理员方式启动，否则游戏内输入无效！
"""

import logging
from mylogger.MyLogger3 import MyLogger
import win32api, win32con
from matchmap.minimap_interface import MinimapInterface
from capture.capture_factory import capture
from myutils.configutils import get_config
logger = MyLogger('BaseController')

class StopListenException(Exception): pass

def wait_for_window():
    if BaseController.stop_listen:
        logger.debug('停止监听')
        raise StopListenException('停止监听')
        # sys.exit(0)

    while not capture.is_active():
        if BaseController.stop_listen:
            logger.debug('停止监听')
            raise StopListenException('停止监听')
            # sys.exit(0)  # 会导致当前线程直接关闭
        logger.debug('不是原神窗口，暂停运行')
        time.sleep(1)

class KeyBoardController(keyboard.Controller):
    def __init__(self, handler):
        super().__init__()
        self.handler = handler

    def press(self, key):
        wait_for_window()
        super().press(key)

    def release(self, key):
        wait_for_window()
        super().release(key)

class MouseController(mouse.Controller):
    def __init__(self):
        super().__init__()

    def scroll(self, dx,dy):
        wait_for_window()
        super().scroll(dx,dy)

    def press(self, button):
        wait_for_window()
        super().press(button)

    def release(self, button):
        wait_for_window()
        super().release(button)

    def move(self, x, y):
        wait_for_window()
        super().move(x,y)

    def click(self, button, count=1):
        wait_for_window()
        super().click(button, count)

    @property
    def position(self):
        """Custom behavior for getting the position."""
        return super().position  # Call parent getter method

    @position.setter
    def position(self, pos):
        """Custom behavior for setting the position."""
        # Example custom logic before calling the parent setter
        # if pos[0] < 0 or pos[1] < 0:
        #     raise ValueError("Position coordinates must be non-negative.")
        # Directly call the parent setter method
        wait_for_window()
        mouse.Controller.position.fset(self, pos)  # Call parent setter method


class BaseController:

    def log(self, *args):
        if self.debug_enable:
            self.logger.debug(args)

    stop_listen = False

    """
    提供操作人物的方法
    """
    def __init__(self, debug_enable=None, gc=None):
        self.Key = Key
        self.tracker = MinimapInterface

        if debug_enable is None:
            debug_enable = get_config('debug_enable', False)
            if debug_enable: self.logger = MyLogger(self.__class__.__name__, logging.DEBUG)
            else: self.logger = MyLogger(self.__class__.__name__, logging.INFO)
        else:
            self.logger = MyLogger(self.__class__.__name__, logging.DEBUG)
        if gc is None: self.gc = capture # genshin capture

        self.Button = Button
        self.__keyboard = KeyBoardController(self)
        self.__ms = MouseController()

        self.debug_enable = debug_enable
        # self.kb_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        # self.ms_listener = mouse.Listener(on_click=self._on_click)
        # self.kb_listener.start()
        # self.ms_listener.start()

    def set_ms_position(self, pos):
        self.__ms.position = pos

    def get_ms_position(self):
        return self.__ms.position

    def _on_click(self, x, y, button, pressed):
        pass

    def ms_scroll(self, dx,dy):
        self.__ms.scroll(dx,dy)

    def ms_middle_press(self):
        self.__ms.press(Button.middle)

    def ms_middle_release(self):
        self.__ms.release(Button.middle)

    def ui_close_button(self):
        """
        右上角关闭按钮, 用于关闭地图、关闭烹饪界面
        :return:
        """
        pos = (self.gc.w - 60, 40)
        pos = self.gc.get_screen_position(pos)
        self.__ms.position = pos
        self.mouse_left_click()

    def ms_click(self, button):
        self.__ms.click(button)

    def mouse_left_click(self):
        self.ms_click(self.Button.left)

    def mouse_right_click(self):
        self.ms_click(self.Button.right)

    def click_if_appear(self, icon, index=None, timeout:int=None):
        """
        点击图标
        :param icon:
        :param index:
        :param timeout:
        :return:
        """
        positions = self.gc.get_icon_position(icon)
        if timeout and type(timeout) is int:
            start_time = time.time()
            while len(positions) < 1:
                if time.time() - start_time > timeout:
                    raise TimeoutError()
                positions = self.gc.get_icon_position(icon)

        is_ok = False
        for (idx, position) in enumerate(positions):
            if index is None:
                self.click_screen(position)
                is_ok = True
            elif idx == index:
                self.click_screen(position)
                is_ok = True

        return is_ok

    def click_screen(self, pos, button:Button=Button.left):
        """
        点击游戏内坐标
        :param pos:
        :param button:
        :return:
        """
        sc_pos = self.gc.get_screen_position(pos)
        self.set_ms_position(sc_pos)
        self.ms_click(button)

    def kb_press_and_release(self, key):
        self.kb_press(key)
        self.kb_release(key)

    def kb_press(self, key):
        """
        按下键盘
        :param key:
        :return:
        """
        self.__keyboard.press(key)

    def kb_release(self, key):
        self.__keyboard.release(key)

    # def _on_press(self, key):
    #     try:
    #         c = key.char
    #     except AttributeError:
    #         # print('special key {0} pressed'.format(key))
    #         if key == Key.esc:
    #             self.log('你按下了esc退出程序')
    #             self.stop_listen = True
    #             self.ms_listener.stop()
    #             self.kb_listener.stop()
    #             sys.exit(0)

    # def _on_release(self, key):
    #     pass

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
        self.__ms.position = position_from
        x, y = position_from
        finalx, finaly = x + dx, y + dy
        self.ms_press(Button.left)
        move_times = 5  # 移动次数(不要设高了，避免漂移)
        gap_time = (duration_ms / move_times) * 0.001  # 移动次数除以间隔
        gap_x = dx / move_times
        gap_y = dy / move_times
        while move_times > 0:
            time.sleep(gap_time)
            x, y = self.get_ms_position()
            self.set_ms_position((x + gap_x, y + gap_y))
            move_times -= 1
        self.set_ms_position((finalx, finaly))  # 确保鼠标在最终位置
        self.ms_release(Button.left)

    def ms_press(self, button):
        self.__ms.press(button)

    def ms_release(self, button):
        self.__ms.release(button)

    def camera_chage(self, dx:int ,dy:int, scroll:int=0):
        """
        相机视角改变
        :param dx:
        :param dy:
        :param scroll:
        :return:
        """
        wait_for_window()
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(dx), int(dy), int(scroll), 0)

    def to_degree(self, degree):
        """
        将当前视角朝向转至多少度
        :param degree:
        :return:
        """
        if degree is None: return
        start = time.time()
        while capture.has_paimon():
            if time.time() - start > 5: break  # 避免超过5秒
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
            if s < 10: return

            s = s * 2
            max_rate = get_config('change_rotation_max_speed', 200)
            if max_rate > 1000: max_rate = 1000
            elif max_rate < 200: max_rate = 200

            if s > max_rate: s = max_rate
            # if s<20: s = 20
            # win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -int(direction * s), 0, 0, 0)
            self.camera_chage(-direction*s, 0,0)

    def crazy_f(self):
        # 若是不小心点到烹饪界面，先关闭, 然后滚轮向下
        if self.gc.has_tob_bar_close_button():
            self.ui_close_button()
            return
        elif self.gc.has_cook_hat():  # 避免点击到烹饪图标
            self.logger.debug('滚轮向上')
            self.ms_scroll(0,1)
        self.kb_press_and_release('f')

if __name__ == '__main__':
    bc = BaseController()
    bc.crazy_f()

        # win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 120, 0)
    # bc.crazy_f()
    from random import randint
    # bc.click_if_appear(capture.icon_message_box_button_confirm)
    # time.sleep(0.5)
    # bc.click_if_appear(capture.icon_map_setting_on)
    # time.sleep(0.4)
    # bc.click_if_appear(capture.icon_close_while_arrow)
    # time.sleep(0.4)
    # bc.click_if_appear(capture.icon_close_tob_bar)

    # for i in range(1,10):
        # 稍微动一下屏幕让模板匹配更容易成功
        # x = randint(-500,500)
        # y = randint(-500,500)
        # bc.camera_chage(x,y)
        # time.sleep(0.2)

        # bc.ms_middle_press()
        # time.sleep(1)
        # if i%2 == 0:
        #     bc.to_degree(-170)
        # else:
        #     bc.to_degree(170)
    #     time.sleep(2)

    # Logger.log("good", instance=BaseController)
    # bc.drag(GenShinCapture.get_genshin_screen_center(),1000, 200, 500)
    # bc.ms.position = (3858.0, 2322.0)
    # bc.ms.click(Button.left)
