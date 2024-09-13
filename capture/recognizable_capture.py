import os.path
import sys
import time

import cv2
import numpy as np

from capture.genshin_capture import GenShinCaptureObj
from myutils.configutils import resource_path, get_paimon_icon_path
from myutils.timerutils import Timer
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('recognizable_capture', save_log=True)

class RecognizableCapture(GenShinCaptureObj):
    def __init__(self):
        super(RecognizableCapture, self).__init__()
        template_path = os.path.join(resource_path, 'template')
        self.icon_paimon = cv2.imread(os.path.join(template_path, 'paimeng_icon_trim.png'), cv2.IMREAD_GRAYSCALE)

        # 1080p截图下来的图片, 做模板匹配的时候要缩放
        # TODO: 换成游戏内截图而非手动截图
        self.__icon_user_status_up_org = cv2.imread(os.path.join(template_path, 'template_up.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_user_status_up = self.__icon_user_status_up_org.copy()

        self.__icon_user_status_down_org = cv2.imread(os.path.join(template_path, 'template_down.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_user_status_down = self.__icon_user_status_down_org.copy()

        self.__icon_user_status_swim_org = cv2.imread(os.path.join(template_path, 'template_swim.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_user_status_swim = self.__icon_user_status_swim_org.copy()

        self.__icon_user_status_key_x_org = cv2.imread(os.path.join(template_path, 'key_x.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_user_status_key_x = self.__icon_user_status_key_x_org.copy()
        self.__icon_user_status_key_space_org = cv2.imread(os.path.join(template_path, 'key_space.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_user_status_key_space = self.__icon_user_status_key_space_org.copy()

        # ui关闭按钮(黑色箭头)
        self.__icon_close_top_bar_org = cv2.imread(os.path.join(template_path, 'button_top_bar_close.png'), cv2.IMREAD_GRAYSCALE)  # 普通ui的关闭按钮
        self.icon_close_tob_bar = self.__icon_close_top_bar_org.copy()

        # 地图的关闭按钮(白色箭头,黑底)
        self.__icon_close_while_arrow_org = cv2.imread(os.path.join(template_path, 'button_while_arrow.png'), cv2.IMREAD_GRAYSCALE)  # 切换国家时候的关闭按钮
        self.icon_close_while_arrow = self.__icon_close_while_arrow_org.copy()

        # 领取奖励的弹窗关闭按钮，包括秘境，boss，地脉。(灰色箭头，白底)
        self.__button_close_gray_arrow_org = cv2.imread(os.path.join(template_path, "button_close_gray_arrow.png"), cv2.IMREAD_GRAYSCALE)
        self.button_close_gray_arrow = self.__button_close_gray_arrow_org.copy()

        # 队伍中, 有一个小三角对应当前的角色
        self.__icon_team_current_triangle_org = cv2.imread(os.path.join(template_path,  "icon_team_current_triangle.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_team_current_triangle = self.__icon_team_current_triangle_org.copy()

        # 提瓦特煎蛋
        self.__icon_eggs_org = cv2.imread(os.path.join(template_path, "icon_food_eggs.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_eggs = self.__icon_eggs_org.copy()

        # 领取奖励-小宝箱图标
        self.__icon_reward_org = cv2.imread(os.path.join(template_path, "icon_dimai_reward.jpg"), cv2.IMREAD_GRAYSCALE)
        self.icon_reward = self.__icon_reward_org.copy()

        # 地脉齿轮
        self.__icon_gear_org = cv2.imread(os.path.join(template_path, "icon_gear.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_gear = self.__icon_reward_org.copy()

        # 领取奖励-钥匙
        self.__icon_key_org = cv2.imread(os.path.join(template_path, "icon_key.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_key = self.__icon_key_org.copy()

        # 地脉-经验
        self.__icon_dimai_exp_org =  cv2.imread(os.path.join(template_path, "icon_dimai_exp.jpg"), cv2.IMREAD_GRAYSCALE)
        self.icon_dimai_exp = self.__icon_dimai_exp_org.copy()
        # 地脉-黄金
        self.__icon_dimai_money_org =  cv2.imread(os.path.join(template_path, "icon_dimai_money.jpg"), cv2.IMREAD_GRAYSCALE)
        self.icon_dimai_money = self.__icon_dimai_money_org.copy()

        # 原粹树脂
        self.__icon_origin_resin_org = cv2.imread(os.path.join(template_path, "icon_origin_resin.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_origin_resin = self.__icon_origin_resin_org.copy()

        # 原粹树脂（对话框）
        self.__icon_button_original_resin_org = cv2.imread(os.path.join(template_path, "button_original_resin_big.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_button_original_resin = self.__icon_button_original_resin_org.copy()
        # 浓缩树脂（对话框）
        self.__icon_button_condensed_resin_org = cv2.imread(os.path.join(template_path, "button_condensed_resin_big.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_button_condensed_resin = self.__icon_button_condensed_resin_org.copy()

        # 地图设置齿轮
        self.__icon_map_setting_gear_org = cv2.imread(os.path.join(template_path, "button_map_setting_gear.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_map_setting_gear = self.__icon_map_setting_gear_org.copy()

        # 地图设置开关图标
        self.__icon_map_setting_on_org = cv2.imread(os.path.join(template_path, "button_map_setting_on.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_map_setting_on = self.__icon_map_setting_on_org.copy()
        self.__icon_map_setting_off_org = cv2.imread(os.path.join(template_path, "button_map_setting_off.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_map_setting_off = self.__icon_map_setting_off_org.copy()

        # 传送按钮
        self.__icon_teleport_org = cv2.imread(os.path.join(template_path, "icon_button_teleport.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_button_teleport= self.__icon_teleport_org.copy()

        # 确认与取消
        self.__icon_message_box_button_confirm_org = cv2.imread(os.path.join(template_path, "icon_message_box_button_confirm.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_message_box_button_confirm = self.__icon_message_box_button_confirm_org.copy()
        self.__icon_message_box_button_cancel_org = cv2.imread(os.path.join(template_path, "icon_message_box_button_cancel.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_message_box_button_cancel = self.__icon_message_box_button_confirm_org.copy()

        # 烹饪
        self.__icon_cook_hat_org = cv2.imread(os.path.join(template_path, 'icon_cook_hat.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_cook_hat = cv2.imread(os.path.join(template_path, 'icon_cook_hat.png'), cv2.IMREAD_GRAYSCALE)

        # 地图切换栏菜单-星星按钮
        self.__icon_map_star_org = cv2.imread(os.path.join(template_path, 'icon_map_star.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_map_star = self.__icon_map_star_org.copy()

        # 地图切换栏菜单-尘歌壶按钮
        self.__icon_map_tea_org = cv2.imread(os.path.join(template_path, 'icon_map_tea.png'), cv2.IMREAD_GRAYSCALE)
        self.icon_map_tea = self.__icon_map_tea_org.copy()

        # 委托图标
        self.__icon_daily_mission_org = cv2.imread(os.path.join(template_path, "icon_daily_mission.jpg"), cv2.IMREAD_GRAYSCALE)
        self.icon_daily_mission = self.__icon_daily_mission_org.copy()
        self.__icon_mission_ok_org = cv2.imread(os.path.join(template_path, "icon_mission_ok.png"), cv2.IMREAD_GRAYSCALE)
        self.icon_mission_ok = self.__icon_mission_ok_org.copy()

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



    def __has_icon(self, image, icon, threshold=0.65):
        # 读取目标图片
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 模板匹配
        result = cv2.matchTemplate(gray_image, icon, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        # 设定阈值
        return max_val >= threshold

    def __icon_fit_resolution(self):
        if self.w == 1920: self.__resize_icon_to_fit_scale(1)
        elif self.w == 2560: self.__resize_icon_to_fit_scale(1.25)
        elif self.w == 1600: self.__resize_icon_to_fit_scale(0.8)
        elif self.w == 1280: self.__resize_icon_to_fit_scale(0.71)

    def get_team_current_number(self):
        """
        在队伍区域中匹配三角形，根据匹配的位置判断当前切的是几号角色
        :return:
        """
        team_area = cv2.cvtColor(self.get_team_area(), cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(team_area, self.icon_team_current_triangle, cv2.TM_CCOEFF_NORMED)
        # 设定阈值
        threshold = 0.95
        # 获取匹配位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            # 把team area按照垂直方向四等分，判断三角形在四等分中的哪个范围内
            # 将大图片高度四等分
            large_height, large_width = team_area.shape
            section_height = large_height // 4

            y_position = max_loc[1]
            section_number = y_position // section_height + 1
            logger.debug(f"图片像素{team_area.shape},最佳匹配位置: {max_loc}, 匹配度: {max_val}, 所在区域{section_number}")
            return section_number
        else:
            logger.debug("没有找到匹配度超过阈值的结果")


    def __resize_icon_to_fit_scale(self, scale):
        self.icon_user_status_up = cv2.resize(self.__icon_user_status_up_org, None, fx=scale, fy=scale)
        self.icon_user_status_down = cv2.resize(self.__icon_user_status_down_org, None, fx=scale, fy=scale)
        self.icon_user_status_swim = cv2.resize(self.__icon_user_status_swim_org, None, fx=scale, fy=scale)

        self.icon_user_status_key_x = cv2.resize(self.__icon_user_status_key_x_org, None, fx=scale, fy=scale)
        self.icon_user_status_key_space = cv2.resize(self.__icon_user_status_key_space_org, None, fx=scale, fy=scale)

        self.icon_close_tob_bar = cv2.resize(self.__icon_close_top_bar_org, None, fx=scale, fy=scale)
        self.icon_close_while_arrow = cv2.resize(self.__icon_close_while_arrow_org, None, fx=scale, fy=scale)

        self.icon_team_current_triangle = cv2.resize(self.__icon_team_current_triangle_org, None, fx=scale, fy=scale)

        self.icon_eggs = cv2.resize(self.__icon_eggs_org, None, fx=scale, fy=scale)
        self.icon_reward = cv2.resize(self.__icon_reward_org, None, fx=scale, fy=scale)
        self.icon_gear = cv2.resize(self.__icon_gear_org, None, fx=scale, fy=scale)
        self.icon_key = cv2.resize(self.__icon_key_org, None, fx=scale, fy=scale)

        self.icon_dimai_exp= cv2.resize(self.__icon_dimai_exp_org, None, fx=scale, fy=scale)
        self.icon_dimai_money = cv2.resize(self.__icon_dimai_money_org, None, fx=scale, fy=scale)

        self.icon_origin_resin = cv2.resize(self.__icon_origin_resin_org, None, fx=scale, fy=scale)

        self.icon_map_setting_gear = cv2.resize(self.__icon_map_setting_gear_org, None, fx=scale, fy=scale)

        self.icon_map_setting_on = cv2.resize(self.__icon_map_setting_on_org, None, fx=scale, fy=scale)
        self.icon_map_setting_off = cv2.resize(self.__icon_map_setting_off_org, None, fx=scale, fy=scale)

        self.icon_button_teleport = cv2.resize(self.__icon_teleport_org, None, fx=scale, fy=scale)
        self.icon_message_box_button_confirm = cv2.resize(self.__icon_message_box_button_confirm_org, None, fx=scale, fy=scale)
        self.icon_message_box_button_cancel = cv2.resize(self.__icon_message_box_button_cancel_org, None, fx=scale, fy=scale)

        self.icon_cook_hat = cv2.resize(self.__icon_cook_hat_org, None, fx=scale, fy=scale)

        self.icon_map_tea = cv2.resize(self.__icon_map_tea_org, None, fx=scale, fy=scale)
        self.icon_map_star = cv2.resize(self.__icon_map_star_org, None, fx=scale, fy=scale)

        self.button_close_gray_arrow = cv2.resize(self.__button_close_gray_arrow_org, None, fx=scale, fy=scale)

        self.icon_button_condensed_resin = cv2.resize(self.__icon_button_condensed_resin_org,None, fx=scale, fy=scale)
        self.icon_button_original_resin = cv2.resize(self.__icon_button_original_resin_org, None, fx=scale, fy=scale)

        self.icon_daily_mission = cv2.resize(self.__icon_daily_mission_org, None, fx=scale, fy=scale)
        self.icon_mission_ok = cv2.resize(self.__icon_mission_ok_org, None, fx=scale, fy=scale)

    def has_mission_ok(self):
        """
        每日委托完成时，会有一个绿色的小箭头在小地图下面短暂停留
        :return:
        """
        self.update_screenshot_if_none()
        mission_area = self.screenshot[150:self.h//3+50, 20:110]
        # cv2.imshow('mission_area', mission_area)
        # key = cv2.waitKey(2)
        # if key == ord('q'):
        #     cv2.destroyAllWindows()
        #     sys.exit(0)
        return self.__has_icon(mission_area, self.icon_mission_ok, threshold=0.9)

    def has_origin_resin_in_top_bar(self):
        self.update_screenshot_if_none()
        top_bar = self.screenshot[0:102, int(self.w*0.5):self.w]
        # cv2.imshow('top_bar', top_bar)
        # cv2.waitKey(2)
        return self.__has_icon(top_bar, self.icon_origin_resin, 0.75)

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
            # raise e
            logger.exception(e)
            return False

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

    def get_icon_position(self, icon, threshold=0.85):
        self.update_screenshot_if_none()
        gray_template = icon
        original_image = self.screenshot.copy()
        gray_original = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        # 获取模板图像的宽度和高度
        w, h = gray_template.shape[::-1]
        # 将小图作为模板，在大图上进行匹配
        result = cv2.matchTemplate(gray_original, gray_template, cv2.TM_CCOEFF_NORMED)

        # 设定阈值
        # 获取匹配位置
        locations = np.where(result >= threshold)
        t = time.time()
        points = []
        # 绘制匹配结果
        prev_point = None
        for pt in zip(*locations[::-1]):
            pt = (int(pt[0]), int(pt[1]))  # 确保 pt 是整数
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            from myutils.executor_utils import euclidean_distance

            if prev_point is None:  # 去掉重合的点
                points.append((center_x, center_y))
            elif euclidean_distance(prev_point, pt) > 20:
                points.append((center_x, center_y))
            prev_point = pt
            # cv2.rectangle(original_image, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)
            # cv2.circle(original_image, (center_x, center_y), 5, (0, 0, 255), -1)  # 在中心点绘制一个红色圆点

        # cv2.imshow('icon_position', original_image)
        # cv2.waitKey(2)
        # print(time.time() - t)
        return points


    def has_map_setting_gear(self):
        self.update_screenshot_if_none()
        img = self.screenshot[self.h-130:self.h-10, 0:120]
        # cv2.imshow('map_setting_gear', img)
        # cv2.waitKey(2)
        return self.__has_icon(img, self.icon_map_setting_gear,0.8)

    def notice_update_event(self):
        super().notice_update_event()
        self.__icon_fit_resolution()

    def has_tob_bar_close_button(self): # 注意，Map侧边切换国家的关闭按钮不是同一个按钮
        return self.__has_icon(self.get_tobbar_area(), self.icon_close_tob_bar) or self.__has_icon(self.get_tobbar_area(), self.icon_close_while_arrow)

    def has_revive_eggs(self):
        """
        提瓦特煎蛋
        :return:
        """
        # img_box = self.screenshot[int(self.w*0.25):int(self.w*0.75), int(self.h*0.25):int(self.h*0.75)]
        self.update_screenshot_if_none()
        img_box = self.screenshot[int(self.h*0.25):int(self.h*0.45), int(self.w*0.25):int(self.w*0.75)]
        return self.__has_icon(img_box, self.icon_eggs)

    def has_reward(self):
        self.update_screenshot_if_none()
        return self.__has_icon(self.screenshot, self.icon_reward, threshold=0.8)

    def has_map_sidebar_toggle(self):
        self.update_screenshot_if_none()
        return (self.__has_icon(self.screenshot, self.icon_map_star, threshold=0.8)
                or self.__has_icon(self.screenshot, self.icon_map_tea, threshold=0.8))

    def has_gear(self):
        self.update_screenshot_if_none()
        return self.__has_icon(self.pick_up_area, self.icon_gear, threshold=0.8)

    def has_key(self):
        self.update_screenshot_if_none()
        return self.__has_icon(self.pick_up_area, self.icon_key, threshold=0.8)

    def has_cook_hat(self):
        self.update_screenshot_if_none()
        return self.__has_icon(self.pick_up_area, self.icon_cook_hat, threshold=0.8)

    def check_icon(self):
        t = time.time()
        down = self.__has_icon(self.get_user_status_area(), self.icon_user_status_down)
        up = self.__has_icon(self.get_user_status_area(), self.icon_user_status_up)
        swim = self.__has_icon(self.get_user_status_area(), self.icon_user_status_swim)
        space = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_space)
        x = self.__has_icon(self.get_user_status_key_area(), self.icon_user_status_key_x)
        print(f'down: {down}, up: {up}, swim: {swim}, space: {space}, x: {x}, cost: {time.time() -t }')

        cv2.imshow('status area',self.get_user_status_area())
        cv2.imshow('status key',self.get_user_status_key_area())
        cv2.imshow('up',self.icon_user_status_up)
        cv2.imshow('down',self.icon_user_status_down)
        cv2.imshow('swim',self.icon_user_status_swim)
        cv2.imshow('space',self.icon_user_status_key_space)
        cv2.imshow('x',self.icon_user_status_key_x)
        cv2.imshow('triangle',self.icon_team_current_triangle)

if __name__ == '__main__':
    rc = RecognizableCapture()
    while True:
        # print(rc.has_revive_eggs())
        t = time.time()
        # rc.update_screenshot_if_none()
        # print(rc.has_origin_resin_in_top_bar(),time.time()-t)
        # pos = rc.get_icon_position(rc.icon_daily_mission)
        # print(pos, time.time()-t)
        print(rc.has_origin_resin_in_top_bar(), time.time() - t)
        # print(rc.has_paimon(), time.time()-t)
        # rc.check_icon()
        # sc = rc.get_paimon_area()
        # flying = rc.is_flying()
        # cost = time.time() - t
        # if cost > 1:
        #     print(f'超时!{cost}')
        # climbing = rc.is_climbing()
        # swimming = rc.is_swimming()
        # start_time = time.time()
        # hasp = rc.has_paimon()
        # cost = time.time() - start_time
        # print('close', rc.has_ui_close_button())
        # rc.check_icon()

        # print(rc.has_geer(), time.time()-t)

        # print(f'flying: {flying}, swimming: {swimming}, climbing: {climbing}, paimon, {hasp}, cost: {cost}')
        # cv2.imshow('screenshot', sc)
        # key = cv2.waitKey(2)
        # if key == ord('q'):
        #     break
    # cv2.destroyAllWindows()
