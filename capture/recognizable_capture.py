import os.path

import cv2
from capture.genshin_capture import GenShinCaptureObj
from myutils.configutils import resource_path

class RecognizableCapture(GenShinCaptureObj):
    def __init__(self):
        super(RecognizableCapture, self).__init__()
        template_path = os.path.join(resource_path, 'template')
        self.icon_paimon = cv2.imread(os.path.join(template_path, 'paimeng_icon_trim.png'), cv2.IMREAD_GRAYSCALE)

        # 1080p截图下来的图片, 做模板匹配的时候要缩放
        self.__icon_user_status_up_org = cv2.imread(os.path.join(template_path, 'template_up.png'), cv2.IMREAD_GRAYSCALE)
        self.__icon_user_status_down_org = cv2.imread(os.path.join(template_path, 'template_down.png'), cv2.IMREAD_GRAYSCALE)
        self.__icon_user_status_swim_org = cv2.imread(os.path.join(template_path, 'template_swim.png'), cv2.IMREAD_GRAYSCALE)

        self.__icon_user_status_key_x_org = cv2.imread(os.path.join(template_path, 'key_x.png'), cv2.IMREAD_GRAYSCALE)
        self.__icon_user_status_key_space_org = cv2.imread(os.path.join(template_path, 'key_space.png'), cv2.IMREAD_GRAYSCALE)

        self.icon_user_status_up = self.__icon_user_status_up_org.copy()
        self.icon_user_status_down = self.__icon_user_status_down_org.copy()
        self.icon_user_status_swim = self.__icon_user_status_swim_org.copy()

        self.icon_user_status_key_x = self.__icon_user_status_key_x_org.copy()
        self.icon_user_status_key_space = self.__icon_user_status_key_space_org.copy()

        self.__icon_fit_resolution()

    def __has_icon(self, image, icon):
        # 读取目标图片
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 模板匹配
        result = cv2.matchTemplate(gray_image, icon, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        # 设定阈值
        threshold = 0.65
        return max_val >= threshold

    def __icon_fit_resolution(self):
        if self.w == 1920: self.__resize_icon_to_fit_scale(1)
        elif self.w == 2560: self.__resize_icon_to_fit_scale(1.25)
        elif self.w == 1600: self.__resize_icon_to_fit_scale(0.75)
        elif self.w == 720: self.__resize_icon_to_fit_scale(0.5)

    def __resize_icon_to_fit_scale(self, scale):
        self.icon_user_status_up = cv2.resize(self.__icon_user_status_up_org, None, fx=scale, fy=scale)
        self.icon_user_status_down = cv2.resize(self.__icon_user_status_down_org, None, fx=scale, fy=scale)
        self.icon_user_status_swim = cv2.resize(self.__icon_user_status_swim_org, None, fx=scale, fy=scale)

        self.icon_user_status_key_x = cv2.resize(self.__icon_user_status_key_x_org, None, fx=scale, fy=scale)
        self.icon_user_status_key_space = cv2.resize(self.__icon_user_status_key_space_org, None, fx=scale, fy=scale)

    def is_swimming(self):
        return self.__has_icon(self.get_user_status_area(),self.icon_user_status_swim)
    def is_climbing(self):
        return self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_x)
    def is_flying(self):
        has_space = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_space)
        has_x = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_x)
        return has_space and not has_x

    def has_paimon(self):
        pass

    def notice_update_event(self):
        super().notice_update_event()
        self.__icon_fit_resolution()


if __name__ == '__main__':
    rc = RecognizableCapture()
    while True:
        sc = rc.get_user_status_key_area()
        flying = rc.is_flying()
        swimming = rc.is_swimming()
        climbing = rc.is_climbing()
        print(f'flying: {flying}, swimming: {swimming}, climbing: {climbing}')
        cv2.imshow('screenshot', sc)
        key = cv2.waitKey(20)
        if key == ord('q'):
            break
    cv2.destroyAllWindows()
