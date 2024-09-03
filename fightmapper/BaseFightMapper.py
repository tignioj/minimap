from controller.BaseController import BaseController

import time

# 按键映射
# https://bgi.huiyadan.com/feats/domain.html

class BaseFightMapper(BaseController):
    def __init__(self):
        super().__init__()

    def wait(self, duration):
        time.sleep(float(duration))

    def walk(self, direction, duration):
        self.kb_press(direction)
        time.sleep(duration)
        self.kb_release(direction)

    def e(self, hold=False):
        self.skill(hold)

    def q(self):
        self.burst()

    def skill(self, hold=False):
        self.kb_press('e')
        if hold: time.sleep(1)
        self.kb_release('e')

    def burst(self):
        self.kb_press_and_release('q')

    def attack(self, duration=None):
        self.mouse_left_click()
        if duration:
            start = time.time()
            while time.time() - start < duration:
                time.sleep(0.02)
                self.mouse_left_click()


    def charge(self, duration):
        self.ms_press(self.Button.left)
        time.sleep(float(duration))
        self.ms_release(self.Button.left)
