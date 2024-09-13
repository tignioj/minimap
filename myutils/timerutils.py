import threading
import time


class Timer:
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

    def reset(self):
        self.start_time = None

class RateLimiter:
    def __init__(self, interval):
        """
        初始化RateLimiter实例
        :param interval: 两次执行之间的最小间隔时间（以秒为单位）
        """
        self.interval = interval
        self.last_executed = 0

    def execute(self, func, *args, **kwargs):
        """
        尝试执行指定的函数

        :param func: 要执行的函数
        :param args: 传递给函数的参数
        :param kwargs: 传递给函数的关键字参数
        :return: 如果在指定时间内执行成功，则返回True；否则返回False
        """
        current_time = time.time()
        if current_time - self.last_executed >= self.interval:
            self.last_executed = current_time
            func(*args, **kwargs)
            return True
        else:
            return False

class RateLimiterAsync:
    def __init__(self, interval):
        """
        初始化RateLimiter实例
        :param interval: 两次执行之间的最小间隔时间（以秒为单位）
        """
        self.interval = interval
        self.last_executed = 0
        self.lock = threading.Lock()
        self.executing = False

    def execute(self, func, *args, **kwargs):
        if self.executing:
            # print("拒绝执行")
            return
        self.executing = True
        threading.Thread(target=self.run, args=(func, *args), kwargs=kwargs).start()

    def run(self, func, *args, **kwargs):
        """
        尝试执行指定的函数

        :param func: 要执行的函数
        :param args: 传递给函数的参数
        :param kwargs: 传递给函数的关键字参数
        :return: 如果在指定时间内执行成功，则返回True；否则返回False
        """
        try:
            current_time = time.time()
            if current_time - self.last_executed >= self.interval:
                self.last_executed = current_time
                func(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
            with self.lock:
                self.executing = False



def demo1():
    # 2秒钟输出一次
    t = Timer(3)
    while True:
        try:
            if t.check():
                print('Time elapsed: ', time.time() - t.start_time)
                t.reset()
        except:
            t.start()
        time.sleep(0.1)
def demo2():
    t = Timer(3)
    while True:
        if t.start_time is None:
            t.start()
        else:
            if t.check():
                print('Time elapsed: ', time.time() - t.start_time)
                t.reset()
        time.sleep(0.1)

def demo3():
    t = None
    while True:
        print('checking')
        if t is None:
            t = Timer(3)
            t.start()
        if t.check():
            print('Time elapsed: ', time.time() - t.start_time)
            t = None


def buy_somthing():
    time.sleep(1)
    print('buy ok')

if __name__ == '__main__':
    rl = RateLimiterAsync(3)
    while True:
        rl.execute(buy_somthing)

