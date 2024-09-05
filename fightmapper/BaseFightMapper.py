from controller.BaseController import BaseController

import time

# 按键映射
# https://bgi.huiyadan.com/feats/domain.html

class FightException(Exception): pass

class BaseFightMapper(BaseController):
    def __init__(self):
        super().__init__()

    def wait(self, duration):
        """
        等待持续时间
        :param duration: 秒
        :return:
        """
        time.sleep(float(duration))

    def walk(self, direction, duration):
        """
        行走
        :param direction: w|s|a|d 向四个方向行走
        :param duration: 走多少秒
        :return:
        """
        if not duration:
            raise FightException('walk必须要有时间参数！')
        self.kb_press(direction)
        time.sleep(float(duration))
        self.kb_release(direction)

    def j(self):
        """
        跳跃，jump的简写
        :return:
        """
        self.jump()
    def jump(self):
        """
        跳跃，可以用字符'j'简写
        :return:
        """
        self.kb_press_and_release(self.Key.space)


    def dash(self, duration=None):
        """
        向角色面前方向冲刺
        :param duration: 冲刺时长
        :return:
        """
        self.ms_press(self.Button.right)
        if duration: time.sleep(float(duration))
        self.ms_release(self.Button.right)

    def e(self, hold=None):
        """
        元素战技
        :param hold: 传入hold则表示长按，不传参数则短按.注：纳西妲长按会自动转圈
        :return:
        """
        self.skill(hold)

    def q(self):
        """
        元素爆发, burst的简写
        :return:
        """
        self.burst()

    def skill(self, hold=None):
        """
        元素战技, 可以用字符'e'简写
        :param hold: 传入hold则表示长按，不传参数则短按.注：纳西妲长按会自动转圈
        :return:
        """
        self.kb_press('e')
        if hold: time.sleep(1)
        self.kb_release('e')

    def w(self, duration):
        """
        向前面行走
        :param duration: 持续时间
        :return:
        """
        self.walk('w', duration=duration)
    def s(self, duration):
        """
        向后面行走
        :param duration: 持续时间
        :return:
        """
        self.walk('s', duration=duration)
    def a(self, duration):
        """
        向左边行走
        :param duration: 持续时间
        :return:
        """
        self.walk('a', duration=duration)
    def d(self, duration):
        """
        向右边行走
        :param duration:  持续时间
        :return:
        """
        self.walk('d', duration=duration)


    def burst(self):
        """
        元素爆发,可以用q简写
        :return:
        """
        self.kb_press_and_release('q')

    def attack(self, duration=None):
        """
        攻击
        :param duration: 持续攻击多少秒, 0.2秒攻击一次
        :return:
        """
        self.mouse_left_click()
        if duration:
            start = time.time()
            while time.time() - start < float(duration):
                time.sleep(0.2)
                self.mouse_left_click()
        else:
            time.sleep(0.2)

    def charge(self, duration=None):
        """
        重击，即长按攻击
        :param duration: 长按攻击时长
        :return:
        """
        self.ms_press(self.Button.left)
        if not duration: time.sleep(1.2)
        else: time.sleep(float(duration))
        self.ms_release(self.Button.left)


    # 高级

    def keydown(self, key):
        """
        键盘按下
        :param key:
        :return:
        """
        key = str(key).lower()
        if hasattr(self.Key, key): self.kb_press(getattr(self.Key,key))
    def keyup(self, key):
        """
        抬起按键
        :param key:
        :return:
        """
        key = str(key).lower()
        if hasattr(self.Key, key): self.kb_release(getattr(self.Key,key))
    def keypress(self, key):
        """
        按下后抬起
        :param key:
        :return:
        """
        key = str(key).lower()
        if hasattr(self.Key, key): self.kb_press_and_release(getattr(self.Key,key))

    def mousedown(self, button=None):
        """
        鼠标按下按键
        :param button: left|middle|right 分别表示鼠标左键、中键、右键，不传参数则默认左键
        :return:
        """
        if not button:
            self.ms_press(self.Button.left)
            return

        button = str(button).lower()
        if hasattr(self.Button, button):
            self.ms_press(getattr(self.Button, button))

    def mouseup(self, button=None):
        """
        鼠标按键抬起
        :param button: left|middle|right 分别表示鼠标左键、中键、右键，不传参数则默认左键
        :return:
        """
        if not button:
            self.ms_release(self.Button.left)
            return

        button = str(button).lower()
        if hasattr(self.Button, button):
            self.ms_release(getattr(self.Button, button))

    def click(self, button=None):
        """
        点击鼠标
        :param button: left|middle|right 分别表示鼠标左键、中键、右键，不传参数则默认左键
        :param button:
        :return:
        """
        if not button:
            self.ms_click(self.Button.left)
            return

        button = str(button).lower()
        if hasattr(self.Button, button):
            self.ms_click(getattr(self.Button, button))

def __get_methods(obj):
    # 获取对象的所有属性和方法
    all_attributes = dir(obj)
    # 过滤出可调用的方法
    methods = [attr for attr in all_attributes if callable(getattr(obj, attr))]
    return methods

def __get_own_methods(cls):
    import inspect
    # 获取类自身定义的所有属性和方法
    own_methods = [
        name for name, method in cls.__dict__.items()
        if inspect.isfunction(method) or inspect.ismethod(method)
    ]
    return own_methods


def __get_method_annotations(cls):
    import inspect
    method_annotations = {}

    # 获取类自身定义的所有方法
    for name, method in cls.__dict__.items():
        if inspect.isfunction(method) or inspect.ismethod(method):
            # 获取方法的注解
            annotations = method.__annotations__
            method_annotations[name] = annotations

    return method_annotations

def __generate_docs_array(cls):
    methods_docs = []

    # 遍历类中的所有属性
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        # 过滤掉内置方法和非可调用对象
        if callable(method) and not method_name.startswith("__"):
            methods_docs.append({
                "method_name": method_name,
                "doc": method.__doc__
            })

    return methods_docs


def __generate_docs_array2(cls):
    methods_docs = []

    # 获取当前类定义的方法，不包括父类的方法
    for method_name, method in cls.__dict__.items():
        # 确保它是一个函数或方法
        if callable(method) and not method_name.startswith("__"):
            methods_docs.append({
                "method_name": method_name,
                "doc": method.__doc__
            })

    return methods_docs

if __name__ == '__main__':
    # docs = __generate_docs_array2(BaseFightMapper)
    # for doc in docs:
    #     print(doc)
    bf = BaseFightMapper()
    bf.charge()


