import cv2

from capture.windowcapture3 import WindowCapture
class ObservableCapture(WindowCapture):
    def __init__(self, window_name):
        self._observers = []
        self._width = None
        self._height = None
        self._suppress_notifications = False  # 新增：用于控制通知的布尔变量

        super().__init__(window_name)

    def add_observer(self, observer):
        self._observers.append(observer)

    def notify_observers(self):
        if not self._suppress_notifications:  # 检查是否抑制通知
            for observer in self._observers:
                observer.update(self._width, self._height)

    def notice_update_event(self):
        if self._observers is None:
            return
        self._suppress_notifications = True  # 开始抑制通知
        self.width = self.w
        self.height = self.h
        self._suppress_notifications = False  # 恢复通知
        self.notify_observers()  # 通知观察者

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        self.notify_observers()

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        self._height = value
        self.notify_observers()

class Observer:
    def update(self, width, height):
        print(f"Observer notified with width: {width}, height: {height}")

if __name__ == '__main__':
    obc = ObservableCapture('原神')
    obs = Observer()
    obc.add_observer(obs)
    while True:
        sc = obc.get_screenshot()
        cv2.imshow('sc', sc)
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
    cv2.destroyAllWindows()
