import numpy as np
# ModuleNotFoundError: No module named 'win32.distutils.command'
# pip install pywin32 instead win32gui
import win32gui, win32ui, win32con
import win32api
import math
from myutils.configutils import cfg
from ctypes import windll


# https://www.youtube.com/watch?v=WymCpVUPWQ4
# https://github.com/learncodebygaming/opencv_tutorials/blob/master/004_window_capture/windowcapture.py

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

    # constructor
    def __init__(self, window_name='原神'):
        # DPI不是100%的时候，需要调用下面的方法正确才能获取窗口大小
        # https://stackoverflow.com/questions/40869982/dpi-scaling-level-affecting-win32gui-getwindowrect-in-python/45911849
        # Make program aware of DPI scaling
        user32 = windll.user32
        user32.SetProcessDPIAware()

        # find the handle for the window we want to capture
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(window_name))

        # get the window size
        window_rect = win32gui.GetWindowRect(self.hwnd)  # 窗口的四个坐标
        client_rect = win32gui.GetClientRect(self.hwnd)  # 窗口的实际大小

        self.w = window_rect[2] - window_rect[0]
        self.h = window_rect[3] - window_rect[1]

        # account for the window border and titlebar and cut them off
        border_pixels = math.floor((self.w - client_rect[2]) / 2)
        titlebar_pixels = self.h - client_rect[3] - border_pixels

        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels

        # set the cropped coordinates offset so we can translate screenshot
        # images into actual screen positions
        self.offset_x = window_rect[0] + self.cropped_x
        self.offset_y = window_rect[1] + self.cropped_y
        # print(self.w, self.h, self.offset_x, self.offset_y)

    def get_screenshot(self, use_alpha=False):
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
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
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

        # drop the alpha channel, or cv.matchTemplate() will throw an error like:
        #   error: (-215:Assertion failed) (depth == CV_8U || depth == CV_32F) && type == _templ.type()
        #   && _img.dims() <= 2 in function 'cv::matchTemplate'

        # img = img[..., :3]

        # make image C_CONTIGUOUS to avoid errors that look like:
        #   File ... in draw_rectangles
        #   TypeError: an integer is required (got type tuple)
        # see the discussion here:
        # https://github.com/opencv/opencv/issues/14866#issuecomment-580207109
        # img = np.ascontiguousarray(img)

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
        return (pos[0] + self.offset_x, pos[1] + self.offset_y)


if __name__ == '__main__':
    windows_name = cfg['window_name']
    wc = WindowCapture(windows_name)
    import time
    import cv2 as cv

    loop_time = time.time()
    while True:
        sc = wc.get_screenshot()
        # cv.namedWindow('window capture', cv.WINDOW_GUI_EXPANDED)
        cv.imshow('window capture', sc)
        cost_time = time.time() - loop_time
        # print("fps:", 1 / cost_time, 'cost time:', cost_time)
        loop_time = time.time()
        key = cv.waitKey(1)
        if key & 0xFF == ord('q'): break
    cv.destroyAllWindows()
