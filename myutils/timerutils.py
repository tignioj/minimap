import time
class Timer:
    """
    计时器，创建一个计时器对象，指定时间后返回True，否则返回False
    """
    def __init__(self, duration):
        self.duration = duration
        self.start_time = None

    def start(self):
        self.start_time = time.time()

    def check(self):
        if self.start_time is None:
            raise ValueError("Timer has not been started yet.")

        elapsed_time = time.time() - self.start_time
        if elapsed_time >= self.duration:
            return True
        else:
            return False