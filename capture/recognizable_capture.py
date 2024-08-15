import os.path
import time

import cv2
from capture.genshin_capture import GenShinCaptureObj
from myutils.configutils import resource_path, get_paimon_icon_path
from myutils.timerutils import Timer

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


        self.sift = cv2.SIFT.create()
        # 匹配器
        self.bf_matcher = cv2.BFMatcher()
        paimon_png = cv2.imread(get_paimon_icon_path(), cv2.IMREAD_GRAYSCALE)
        kp, des = self.sift.detectAndCompute(paimon_png, None)  # 判断是否在大世界
        self.map_paimon = { 'img': paimon_png, 'des': des, 'kp': kp }
        self.__paimon_appear_delay = 1  # 派蒙出现后，多少秒才可以进行匹配
        # 如果要求首次不进行计时器检查，则需要设置一个0的计时器
        self.__paimon_appear_delay_timer = Timer(0)  # 派蒙延迟计时器
        self.__paimon_appear_delay_timer.start()

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
        elif self.w == 1600: self.__resize_icon_to_fit_scale(0.8)
        elif self.w == 1280: self.__resize_icon_to_fit_scale(0.71)

    def __resize_icon_to_fit_scale(self, scale):
        self.icon_user_status_up = cv2.resize(self.__icon_user_status_up_org, None, fx=scale, fy=scale)
        self.icon_user_status_down = cv2.resize(self.__icon_user_status_down_org, None, fx=scale, fy=scale)
        self.icon_user_status_swim = cv2.resize(self.__icon_user_status_swim_org, None, fx=scale, fy=scale)

        self.icon_user_status_key_x = cv2.resize(self.__icon_user_status_key_x_org, None, fx=scale, fy=scale)
        self.icon_user_status_key_space = cv2.resize(self.__icon_user_status_key_space_org, None, fx=scale, fy=scale)

    def is_swimming(self):
        return self.__has_icon(self.get_user_status_area(),self.icon_user_status_swim)
    def is_climbing(self):
        has_space = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_space)
        has_x = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_x)
        return has_space and has_x
    def is_flying(self):
        has_space = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_space)
        has_x = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_x)
        return has_space and not has_x
        # has_up = self.__has_icon(self.get_user_status_area(), self.icon_user_status_swim)
        # has_down = self.__has_icon(self.get_user_status_area(), self.icon_user_status_down)
        # return has_up and not has_down

    def has_paimon(self):
        """
        判断小地图左上角区域是否有小派蒙图标,如果没有说明不在大世界界面（可能切地图或者菜单界面了)
        :return:
        """
        # 将图像转换为灰度
        img = self.get_paimon_area()
        try:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            raise e

        # 检测和计算图像和模板的关键点和描述符
        kp1, des1 = self.sift.detectAndCompute(img, None)
        matches = self.bf_matcher.knnMatch(des1, self.map_paimon['des'], k=2)

        # 应用比例测试来过滤匹配点
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
        # 如果找到匹配，返回True

        # // FIXED BUG: 可能截取到质量差的派蒙图片, 此时会错误的进行全局匹配
        # 设计当出现派蒙由False转为True时，延迟0.5秒再返回True

        if len(good_matches) >= 7:
            if self.__paimon_appear_delay_timer is None:
                self.__paimon_appear_delay_timer = Timer(self.__paimon_appear_delay)
                self.__paimon_appear_delay_timer.start()
            has = self.__paimon_appear_delay_timer.check()
            return has
        else:
            self.__paimon_appear_delay_timer = None
        return False


    def notice_update_event(self):
        super().notice_update_event()
        self.__icon_fit_resolution()

    def check_icon(self):
        t = time.time()
        down = self.__has_icon(self.get_user_status_area(), self.icon_user_status_down)
        up = self.__has_icon(self.get_user_status_area(), self.icon_user_status_up)
        swim = self.__has_icon(self.get_user_status_area(), self.icon_user_status_swim)
        space = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_space)
        x = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_x)
        print(f'down: {down}, up: {up}, swim: {swim}, space: {space}, x: {x}, cost: {time.time() -t }')

        cv2.imshow('st',self.get_user_status_area())
        cv2.imshow('stk',self.get_user_status_key_area())
        cv2.imshow('up',self.icon_user_status_up)
        cv2.imshow('down',self.icon_user_status_down)
        cv2.imshow('swim',self.icon_user_status_swim)
        cv2.imshow('space',self.icon_user_status_key_space)
        cv2.imshow('x',self.icon_user_status_key_x)

if __name__ == '__main__':
    rc = RecognizableCapture()
    while True:
        sc = rc.get_paimon_area()
        flying = rc.is_flying()
        climbing = rc.is_climbing()
        swimming = rc.is_swimming()
        start_time = time.time()
        hasp = rc.has_paimon()
        cost = time.time() - start_time
        # rc.check_icon()
        print(f'flying: {flying}, swimming: {swimming}, climbing: {climbing}, paimon, {hasp}, cost: {cost}')
        # cv2.imshow('screenshot', sc)
        key = cv2.waitKey(2)
        if key == ord('q'):
            break
    cv2.destroyAllWindows()
