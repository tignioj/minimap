import os
import logging
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from myutils.configutils import PROJECT_PATH
import sys

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    style="%",
    datefmt="%Y-%m-%d_%H:%M",
    level=logging.DEBUG,
    handlers=[
        # logging.FileHandler(f'{os.path.basename(__file__)}.log'),
        logging.StreamHandler(sys.stdout),
    ])

class CustomFormatter(logging.Formatter):

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                 datefmt='%Y-%m-%d %H:%M:%S', style='%'):
        super().__init__(fmt, datefmt)
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.blue + self.fmt + self.reset,
            logging.INFO: self.grey + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)

class MyLogger(logging.Logger):
    def __init__(self, name, level=logging.DEBUG, save_log=False):
        super().__init__(name, level)

        # __current_file_path = os.path.dirname(os.path.abspath(__file__))
        __log_path = os.path.join(PROJECT_PATH, 'log')
        # 日志控制台
        console_handler = logging.StreamHandler(sys.stdout)  # 不传入参数默认是stderr，输出红色
        self.addHandler(console_handler)
        console_handler.setLevel(level)
        max_byte = 5*1024*1024

        # 格式化显示
        formatter_console = CustomFormatter()

        formatter_file = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%m-%d %H:%M'
        )

        # 保存日志文件
        if save_log:
            if not os.path.exists(__log_path):
                os.mkdir(__log_path)

            __err_path = f'{__log_path}\\error'
            __info_path = f'{__log_path}\\info'
            if not os.path.exists(__err_path): os.mkdir(__err_path)
            if not os.path.exists(__info_path): os.mkdir(__info_path)

            timestr = datetime.now().strftime("%Y-%m-%d")
            err_filename = f"{__err_path}/{timestr}.log"
            info_filename = f"{__info_path}/{timestr}.log"

            file_handler = RotatingFileHandler(err_filename, mode="a", encoding="utf-8", maxBytes=max_byte, backupCount=10)
            file_handler.setLevel(logging.ERROR)  # 仅保存错误级别以上的日志
            self.addHandler(file_handler)
            file_handler.setFormatter(formatter_file)

            # 普通日志文件
            info_file_handler = RotatingFileHandler(info_filename, mode="a", encoding="utf-8", maxBytes=max_byte, backupCount=10)
            info_file_handler.setLevel(logging.INFO)  # 仅INFO级别以上的日志
            info_file_handler.setFormatter(formatter_file)
            self.addHandler(info_file_handler)

        # 控制台格式化显示
        console_handler.setFormatter(formatter_console)



if __name__ == '__main__':
    mylogger = MyLogger('mylogger', save_log=True)
    n = 20
    while n > 0:
        n -= 1
        mylogger.debug('debug')
        mylogger.info('info')
        mylogger.warning('warning')
        mylogger.error('error')
        mylogger.critical('critical')

        try:
            a,b = 1,0
            res = a/b
        except ZeroDivisionError:
            mylogger.error('division by zero', exc_info=True)  # 保留堆栈信息
            # mylogger.exception('division by zero')  # 正常处理

    print(mylogger.parent, mylogger.getEffectiveLevel())

    # print(mylogger.handlers)