import sys
import time
import numpy as np
import cv2
from myutils.timerutils import RateLimiter
from capture.observable_capture import ObservableCapture
from myutils.configutils import cfg
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('genshin_capture')

class GenShinCaptureObj(ObservableCapture):
    def __init__(self):
        super().__init__(cfg.get('window_name', '原神'))
        # super().__init__('Genshin Impact')
        # 16:9
        self.minimap_radius = None
        self.mask = None
        self.paimon_area = None
        self.user_status_area = None
        self.minimap = None
        self.rate_limiter_update_screenshot = RateLimiter(0.01)  # 限制100帧
        self.user_status_area_offset = 0,0,0,0

        # 更新截图区域
        self.__update_crop_size()
        self.screenshot = self.get_screenshot(use_alpha=True)

    def get_paimon_area(self):
        """
        获取小地图派梦区域头像
        :return:
        """
        self.update_screenshot_if_none()
        return self.paimon_area


    def crop_image(self, image, width, height, left_offset, top_offset):
        return image[top_offset:top_offset + height, left_offset:left_offset + width]

    def update_screenshot_if_none(self):
        if self.screenshot is None:
            self.screenshot = self.get_screenshot(use_alpha=True)
        else:
            self.rate_limiter_update_screenshot.execute(self.update_screenshot)

    def update_screenshot(self):
        self.screenshot = self.get_screenshot(use_alpha=True)
        self.paimon_area = self.screenshot[0:100, 10:120]
        self.user_status_area = self.screenshot[self.user_status_area_offset[0]:self.user_status_area_offset[1], self.user_status_area_offset[2]:self.user_status_area_offset[3]]
        self.user_status_key_area = self.screenshot[self.user_status_area_offset[0]+50:self.user_status_area_offset[1],
                                    self.user_status_area_offset[2]:self.user_status_area_offset[3]]

    def get_user_status_area(self):
        self.update_screenshot_if_none()
        return self.user_status_area
    def get_user_status_key_area(self):
        self.update_screenshot_if_none()
        return self.user_status_key_area

    def notice_update_event(self):
        super().notice_update_event()
        self.__update_crop_size()

    def __update_crop_size(self):
        if self.w == 1280:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 144, 144, 40, 11
            self.user_status_area_offset = self.h-85,self.h-20, self.w-150, self.w-20
        elif self.w == 1600:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 180, 180, 50, 14
            self.user_status_area_offset = self.h-110,self.h-25, self.w-185, self.w-30
        elif self.w == 1920:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 216, 216, 60, 17
            self.user_status_area_offset = self.h-130, self.h-25, self.w-225, self.w-35
        elif self.w == 2560:
            self.mini_map_width, self.mini_map_height, self.mini_map_left_offset, self.mini_map_top_offset = 288, 288, 80, 23  # 23
            self.user_status_area_offset = self.h-165, self.h-35, self.w-290, self.w-55
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
        self.update_screenshot_if_none()
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


def _saveimg():
    time.sleep(4)
    cv2.imwrite(f'{gc.w}x{gc.h}.png', gc.get_mini_map(update_screenshot=True))
    print('image saved')

class __Observer:
    def update(self, width, height):
        print(f"Observer notified with width: {width}, height: {height}")
        threading.Thread(target=_saveimg).start()

if __name__ == '__main__':
    import cv2
    gc = GenShinCaptureObj()
    obs = __Observer()
    gc.add_observer(obs)
    import threading
    while True:
        # b, g, r, alpha = cv2.split(map)
        t = time.time()
        # gc.update_screenshot()
        ua = gc.get_user_status_key_area()
        cv2.imshow('ua', ua)
        key = cv2.waitKey(2)
        if key == ord('q'):
            cv2.destroyAllWindows()
            break
        print('time taken:', time.time() - t)
