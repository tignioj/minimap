import sys
import time
import numpy as np
import cv2
# from capture.windowcapture3 import WindowCapture
from capture.observable_capture import ObservableCapture
from myutils.configutils import cfg
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('genshin_capture')

class GenShinCaptureObj(ObservableCapture):
    # 实现单例模式
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__(cfg['window_name'])
        # super().__init__('Genshin Impact')
        # 16:9
        self.minimap_radius = None
        self.__update_minimap_size()
        self.mask = None
        self.paimon_area = None
        self.minimap = None

    def get_paimon_ariea(self, update_screenshot=True):
        """
        获取小地图派梦区域头像
        :return:
        """
        if update_screenshot: self.update_screenshot()
        return self.screenshot[0:100, 10:120]

    def crop_image(self, image, width, height, left_offset, top_offset):
        return image[top_offset:top_offset + height, left_offset:left_offset + width]

    def update_screenshot(self):
        self.screenshot = self.get_screenshot(use_alpha=True)

    def notice_update_event(self):
        super().notice_update_event()
        self.__update_minimap_size()

    def __update_minimap_size(self):
        if self.w == 1280 and self.h == 720:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 144, 144, 40, 11
        elif self.w == 1600 and self.h == 900:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 180, 180, 50, 14
        elif self.w == 1920 and self.h == 1080:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 216, 216, 60, 17
        elif self.w == 2560 and self.h == 1440:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 288, 288, 80, 23  # 23
            # self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 286, 286, 81, 23 # 23
        else:
            msg = 'Resolution error, current resolution is: {}x{}, support 16:9 only'.format(self.w, self.h)
            logger.error(msg)
            # raise ResolutionException(msg)

        # 小地图掩码
        self.circle_mask = np.zeros((self.mini_map_width, self.mini_map_height), np.uint8)
        # 定义圆的参数：圆心坐标和半径
        center = (self.mini_map_width // 2, self.mini_map_height // 2)
        radius = min(self.mini_map_width, self.mini_map_height) // 2 - (12 + abs(int((200 - self.mini_map_width))))
        # 在掩码上绘制圆形
        cv2.circle(self.circle_mask, center, radius, (255), thickness=cv2.FILLED)



    def get_mini_map(self, use_alpha=False, use_circled_mask=False, use_tag_mask=False, use_tag_mask_v2=False, update_screenshot=True):
        """
        获取1920x1080分辨率下的小地图
        :param use_alpha:
        :param use_circled_mask:
        :param use_tag_mask:
        :return:
        """
        if update_screenshot: self.update_screenshot()

        cropped_image = self.crop_image(self.screenshot, width=self.mini_map_width, height=self.mini_map_height,
                                        left_offset=self.mini_map_left_offset, top_offset=self.mini_map_top_offset)

        if use_circled_mask or use_tag_mask or use_tag_mask_v2:
            cropped_image = cv2.bitwise_and(cropped_image, cropped_image, mask=self.mask)
            self.mask = np.zeros((cropped_image.shape[0], cropped_image.shape[1]), np.uint8)
            self.mask.fill(255)

            if use_circled_mask:
                self.mask = cv2.bitwise_and(self.mask, self.circle_mask)

            if use_tag_mask:  # 必须依赖alpha
                # 去掉小地图上的标记，例如神曈、锚点、人物、怪物标记
                b, g, r, alpha = cv2.split(cropped_image)
                # 检测出来的, 在这个阈值内，提取的标记最清晰
                bin_lower_threshold = 150
                bin_upper_threshold = 245
                tag_mask_v1 = cv2.inRange(alpha, bin_lower_threshold, bin_upper_threshold)
                cv2.imshow('tag_mask_v1', tag_mask_v1)
                self.mask = cv2.bitwise_and(self.mask, tag_mask_v1)

            elif use_tag_mask_v2:
                b, g, r, alpha = cv2.split(cropped_image)
                img = alpha
                # 找到边界
                edges = cv2.Canny(alpha, 500, 464, apertureSize=5)
                # cv2.imshow("edges", edges)

                # 首先，我们需要找到图像中的所有轮廓。这可以通过cv2.findContours函数实现12。
                contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                # 然后，我们可以通过计算每个轮廓的面积，并与阈值进行比较，找到面积小于一定值的轮廓2。
                # small_contours = [cnt for cnt in contours if cv2.contourArea(cnt) < threshold_area]
                threshold_area = 1000  # 设置面积阈值
                tag_mask_v2 = np.zeros(img.shape, np.uint8)  # 创建一个和原图像同样大小的掩码
                tag_mask_v2.fill(255)  # 白色
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area < threshold_area:
                        cv2.drawContours(tag_mask_v2, [cnt], -1, (0), thickness=cv2.FILLED)  # 将轮廓绘制到掩码上
                self.mask = cv2.bitwise_and(self.mask, tag_mask_v2)

        if not use_alpha:
            cropped_image = np.ascontiguousarray(cropped_image[..., :3])
        return cropped_image

    def get_genshin_screen_center(self):

        """
        获取原神窗口的中心在屏幕中的实际位置
        :return:
        """
        return self.get_screen_position((self.w / 2, self.h / 2))

    def thread_genshin_capture(self):
        while True:
            # print("shape", self.screenshot.shape)
            print("shape", self.get_screenshot().shape)

GenShinCapture = GenShinCaptureObj()

def saveimg():
    time.sleep(4)
    # cv2.imwrite(f'{GenShinCapture.w}x{GenShinCapture.h}.png', GenShinCapture.get_mini_map(update_screenshot=True))
    # print('image saved')
    from matchmap.sifttest.sifttest_minimap_resolution import detect
    detect(GenShinCapture.get_mini_map(True))

class __Observer:
    def update(self, width, height):
        print(f"Observer notified with width: {width}, height: {height}")
        # threading.Thread(target=saveimg).start()

if __name__ == '__main__':
    import cv2
    gc = GenShinCapture
    obs = __Observer()
    gc.add_observer(obs)

    import threading

    # threading.Thread(target=gc.thread_genshin_capture).start()
    while True:
        # map = gc.get_mini_map(use_alpha=True, use_circled_mask=True, use_tag_mask_v2=True)
        # b, g, r, alpha = cv2.split(map)
        # print("screen center{}".format(gc.get_genshin_screen_center()))
        # cv2.imshow("screen", gc.get_screenshot())
        t = time.time()
        gc.update_screenshot()
        # print('up',time.time() - t)

        img = gc.get_paimon_ariea(update_screenshot=False)
        # print('pai',time.time() - t)

        mp = gc.get_mini_map(update_screenshot=False)
        # print('time cost',time.time() - t)

        cv2.imshow("paimon", img)
        mp = cv2.resize(mp, None, fx=4, fy=4)
        cv2.imshow("mp", mp)
        key = cv2.waitKey(20)
        if key & 0xFF == ord('q'): break
    cv2.destroyAllWindows()
