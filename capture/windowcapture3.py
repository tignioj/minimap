import sys
import threading

import numpy
import numpy as np
# ModuleNotFoundError: No module named 'win32.distutils.command'
# pip install pywin32 instead win32gui
import win32gui, win32ui, win32con
import win32api
import math
from myutils.configutils import get_config
from ctypes import windll
from mylogger.MyLogger3 import MyLogger

logger = MyLogger('window_capture')
import logging
logging.getLogger('werkzeug').setLevel('INFO')

# https://www.youtube.com/watch?v=WymCpVUPWQ4
# https://github.com/learncodebygaming/opencv_tutorials/blob/master/004_window_capture/windowcapture.py
class WindowsNotFoundException(Exception):
    def __init__(self, windows_name):
        super(WindowsNotFoundException, self).__init__(f"没有找到名称为'{windows_name}'的窗口!")

class WindowCapture:
    """
    窗口捕获器，通过传入窗口的名称获取截图
    """

    # properties
    w = 0
    h = 0
    hwnd = None
    cropped_x = 0
    cropped_y = 0
    offset_x = 0
    offset_y = 0

    # constructor
    def __init__(self, window_name='原神'):
        # DPI不是100%的时候，需要调用下面的方法正确才能获取窗口大小
        # https://stackoverflow.com/questions/40869982/dpi-scaling-level-affecting-win32gui-getwindowrect-in-python/45911849
        # Make program aware of DPI scaling
        user32 = windll.user32
        user32.SetProcessDPIAware()
        self.lock = threading.Lock()
        self.window_name = window_name
        try:
            # find the handle for the window we want to capture
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            if not self.hwnd: raise WindowsNotFoundException(self.window_name)

            # get the window size
            window_rect = win32gui.GetWindowRect(self.hwnd)  # 窗口的四个坐标
            client_rect = win32gui.GetClientRect(self.hwnd)  # 窗口的实际大小
            window_w = window_rect[2] - window_rect[0]
            window_h = window_rect[3] - window_rect[1]

            # account for the window border and titlebar and cut them off
            border_pixels = math.floor((window_w - client_rect[2]) / 2)
            titlebar_pixels = window_h - client_rect[3] - border_pixels

            self.w = window_w - (border_pixels * 2)
            self.h = window_h - titlebar_pixels - border_pixels
            self.cropped_x = border_pixels
            self.cropped_y = titlebar_pixels
            self.last_screen = None

            # set the cropped coordinates offset so we can translate screenshot
            # images into actual screen positions
            self.offset_x = window_rect[0] + self.cropped_x
            self.offset_y = window_rect[1] + self.cropped_y
            # print(self.w, self.h, self.offset_x, self.offset_y)
        except WindowsNotFoundException as e:
            logger.error(e)
            sys.exit(1)

    def get_screen_scale_factor(self):
        """
        获取屏幕缩放
        :return:
        """
        user32 = windll.user32
        user32.SetProcessDPIAware()

        dpi = user32.GetDpiForWindow(user32.GetForegroundWindow())
        scale_factor = dpi / 96  # 96 DPI is the standard DPI for 100% scaling

        return scale_factor * 100

    def activate_window(self):
        """
        将窗口置于前台
        :return:
        """
        if self.hwnd is not None:
            win32gui.SetForegroundWindow(self.hwnd)
    def is_active(self):
        """
        判断窗口是否处于前台
        :return:
        """
        current_win_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        # logger.debug(f'当前窗口名称：{current_win_name}')
        return current_win_name == self.window_name

    def __update_rect(self):
        # find the handle for the window we want to capture
        self.hwnd = win32gui.FindWindow(None,self.window_name)
        if not self.hwnd:
            raise WindowsNotFoundException(self.window_name)

        # get the window size
        window_rect = win32gui.GetWindowRect(self.hwnd)  # 窗口的四个坐标
        client_rect = win32gui.GetClientRect(self.hwnd)  # 窗口的实际大小
        old_w = self.w
        old_h = self.h

        window_w = window_rect[2] - window_rect[0]
        window_h = window_rect[3] - window_rect[1]

        # account for the window border and titlebar and cut them off
        border_pixels = math.floor((window_w - client_rect[2]) / 2)
        titlebar_pixels = window_h - client_rect[3] - border_pixels


        self.w = window_w - (border_pixels * 2)
        self.h = window_h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels

        # set the cropped coordinates offset so we can translate screenshot
        # images into actual screen positions
        self.offset_x = window_rect[0] + self.cropped_x
        self.offset_y = window_rect[1] + self.cropped_y
        # print(self.w, self.h, self.offset_x, self.offset_y)

        if client_rect[2] != old_w or client_rect[3] != old_h:
            logger.info(f'Resolution changed to{self.w}*{self.h}')
            self.notice_update_event()

    def get_screenshot(self, use_alpha=True):
        self.__update_rect()
        img = self.__get_screenshot_alpha()
        if use_alpha:
            return img

        img = img[..., :3]

        # make image C_CONTIGUOUS to avoid errors that look like:
        #   File ... in draw_rectangles
        #   TypeError: an integer is required (got type tuple)
        # see the discussion here:
        # https://github.com/opencv/opencv/issues/14866#issuecomment-580207109
        img = np.ascontiguousarray(img)
        return img

    def __get_screenshot_alpha(self):
        # get the window image data
        try:
            with self.lock:
                wDC = win32gui.GetWindowDC(self.hwnd)
                dcObj = win32ui.CreateDCFromHandle(wDC)
                cDC = dcObj.CreateCompatibleDC()
                dataBitMap = win32ui.CreateBitmap()
                try:
                    dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
                except win32ui.error as e:
                    raise RuntimeError(e)
                cDC.SelectObject(dataBitMap)
                cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (self.cropped_x, self.cropped_y), win32con.SRCCOPY)
                # convert the raw data into a format opencv can read
                # dataBitMap.SaveBitmapFile(cDC, 'debug.bmp')
                signedIntsArray = dataBitMap.GetBitmapBits(True)
                # img = np.fromstring(signedIntsArray, dtype='uint8')
                img = np.frombuffer(signedIntsArray, dtype='uint8')
                img.shape = (self.h, self.w, 4)

                # free resources
                dcObj.DeleteDC()
                cDC.DeleteDC()
                win32gui.ReleaseDC(self.hwnd, wDC)
                win32gui.DeleteObject(dataBitMap.GetHandle())
                self.last_screen = img
        except Exception as e:
            logger.error(e)
            # 不知道如何解决
            # dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
            # win32ui.error: CreateCompatibleDC failed
            return self.last_screen
        return img

    # find the name of the window you're interested in.
    # once you have it, update window_capture()
    # https://stackoverflow.com/questions/55547940/how-to-get-a-list-of-the-name-of-every-open-window
    def list_window_names(self):
        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                print(hex(hwnd), win32gui.GetWindowText(hwnd))

        win32gui.EnumWindows(winEnumHandler, None)

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the __init__ constructor.
    def get_screen_position(self, pos):
        self.__update_rect()
        return (pos[0] + self.offset_x, pos[1] + self.offset_y)

    def notice_update_event(self):
        """
        分辨率改变时调用，子类实现
        :return:
        """
        pass

if __name__ == '__main__':
    # windows_name = get_config('window_name')
    wc = WindowCapture()
    import time
    import cv2 as cv

    if not wc.is_active():
        wc.activate_window()

    loop_time = time.time()
    while True:
        t = time.time()
        sc = wc.get_screenshot()
        # print(win32gui.GetWindowText(wc.hwnd))
        print(wc.is_active(),time.time()-t)
        # cv.namedWindow('window capture', cv.WINDOW_GUI_EXPANDED)
        cv.imshow('window capture', sc)
        # cost_time = time.time() - loop_time
        # print("fps:", 1 / cost_time, 'cost time:', cost_time)
        # loop_time = time.time()
        key = cv.waitKey(1)
        if key & 0xFF == ord('q'): break
    cv.destroyAllWindows()
