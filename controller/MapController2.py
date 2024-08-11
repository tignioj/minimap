# 锚点传送测试
# 思路：
import math
import sys
import time
# from ocrtest.paddleocrtest.paddleocr_test3_findtext_click import find_text_and_click
from controller.BaseController import BaseController

import random

class LocationException(Exception):
    pass
class MoveTimeoutException(Exception):
    pass

class MapController(BaseController):

    def __init__(self, tracker=None, ocr=None, debug_enable=False):
        super(MapController, self).__init__(debug_enable)
        if tracker is None:
            from matchmap.minimap_interface import MinimapInterface
            tracker = MinimapInterface
        if ocr is None:
            from controller.OCRController import OCRController
            ocr = OCRController(debug_enable)

        self.stop_listen = False
        self.tracker = tracker
        self.debug_enable = debug_enable
        self.ocr = ocr

        # 如何得到scale_x和scale_y
        # 计算中心点的坐标A(匹配结果)，然后把地图移动到使得人物处于左上角边界状态坐标B(匹配结果)
        # B - A 坐标做差得到dx和dy，如此可以计算出分辨率和坐标的百分比
        # 对于1920*1080分辨率来说, 差值是dx=2019, 1120

        if self.gc.w == 1280 and self.gc.h == 720:
            dx, dy = 1720.52001953125, 946.502685546875
        elif self.gc.w == 1920 and self.gc.h == 1080:
            dx, dy = 2019, 1120
        elif self.gc.w == 1600 and self.gc.h == 900:
            dx, dy = 2008, 1125
        elif self.gc.w == 2560 and self.gc.h == 1440:
            dx, dy = 2349, 1303
        else:
            msg = f'不支持的分辨率{self.gc.w}*{self.gc.h}'
            self.logger.error(msg)

        self.scale_x = (self.gc.w / 2) / dx
        self.scale_y = (self.gc.h / 2) / dy
        self.log('大地图移动比例', self.scale_x, self.scale_y, dx, dy)

    def click_anchor(self, anchor_name=None):
        if anchor_name is None: anchor_name = '传送锚点'

        self.mouse_left_click()  # 点击锚点
        time.sleep(1)  # 等待这一步很重要
        if self.ocr.find_text_and_click(anchor_name):
            self.log(f"点击{anchor_name}")
        elif self.ocr.find_text_and_click("七天神像"):
            self.log("点击七天神像")
        else:
            self.log(f"未能点击'{anchor_name}'")
        time.sleep(1)
        self.ocr.find_text_and_click("传送", match_all=True)
        time.sleep(1)

    def kb_press(self, key):
        if self.stop_listen: return
        super().kb_press(key)

    def kb_release(self, key):
        # 即使停止了也要释放
        super().kb_release(key)

    # 1. 按下M键打开大地图
    def open_middle_map(self):
        time.sleep(1.5)
        open_ok = False
        self.log("按下m打开地图")
        for i in range(2):
            if not self.ocr.is_text_in_screen("探索度"):
                self.kb_press_and_release('m')
                time.sleep(0.5)
            else:
                open_ok = True
                break
        self.log(f"打开地图状态：{open_ok}")
        return open_ok

    def close_middle_map(self):
        self.log("正在关闭大地图")
        self.ui_close_button()

    # 2. 切换到固定的缩放大小（依赖层岩巨源）
    def scale_middle_map(self, country):
        self.log("正在调整地图比例")
        self.ocr.find_text_and_click("探索度")
        time.sleep(0.5)
        self.ocr.find_text_and_click("尘歌壶")
        time.sleep(0.5)
        self.ocr.find_text_and_click("洞天仙力")
        time.sleep(0.5)
        self.ocr.find_text_and_click(country, match_all=True) # 全文字匹配避免点击到每日委托
        time.sleep(0.5)
        self.log("调整地图比例结束")

    # def middle_to_country(self, country):
    #     if self.stop_listen: return
    #     """
    #     切换大地图到指定国家
    #     :param country:
    #     :return:
    #     """
    #     self.log("打开侧边栏的国家切换面板")
    #     self.ocr.find_text_and_click("探索度")
    #     time.sleep(1)
    #     self.log("寻找'{}'并尝试点击".format(country))
    #     if self.ocr.find_text_and_click(country, match_all=True):
    #         self.log("成功点击{}".format(country))
    #     else:
    #         self.log("未能点击{}，开始递归!".format(country))
    #         self.close_middle_map()
    #         self.open_middle_map()
    #         # 递归
    #         self.middle_to_country(country)

    # 3. 匹配地图，得到地图的中心点位置。
    def get_middle_map_position(self):
        return self.tracker.get_user_map_position()

    # 4. 计算地图的中心点位置和指定锚点位置的偏差，得到水平偏差dx和垂直偏差dy
    #     dx = target_position[0] - current_position[0]
    #     dy = target_position[1] - current_position[1]
    def get_dx_dy_from_target_position(self, target_position=None):
        if target_position is None: raise LocationException('传送目标未设置！')

        current_position = self.get_middle_map_position()
        if current_position is not None:
            try:
                dx = current_position[0] - target_position[0]
                dy = current_position[1] - target_position[1]
                return dx, dy
            except TypeError:
                self.logger.error('type err')
        else:
            self.logger.error('无法获取大地图位置！')
            raise LocationException('无法获取大地图位置!')

    def from_point(self):
        center = self.gc.get_genshin_screen_center()
        random_size = 120
        # 添加随机数，防止被标记挡住
        x = center[0] + random.randint(-random_size, random_size)
        y = center[1] + random.randint(-random_size, random_size)
        return (x, y)

    def move_to_point(self, point, country):
        if self.stop_listen: return
        nearby_threshold = min(self.gc.h,self.gc.w) // 2 - 20


        self.move(point, nearby_threshold)
        delta_x, delta_y = self.get_dx_dy_from_target_position(point)
        if delta_x is None or abs(delta_x) > nearby_threshold or abs(delta_y) > nearby_threshold:
            # 如果发现当前偏移太严重，则递归
            self.log("偏移严重，递归调用move_to_point中!")
            self.move_to_point(point, country)
            return

    # 5. 根据偏差移动地图。 注意移动的时候鼠标的拖动位置不能点到锚点，否则会无法拖动，因此可以给鼠标加上一个随机偏差
    def move(self, point, nearby_threshold=None):
        if nearby_threshold is None: nearby_threshold = min(self.gc.h, self.gc.w) // 2 - 20
        if self.stop_listen: return
        # 根据当前位置与下一个点位的差值决定移动方向和距离
        start_time = time.time()
        delta_x, delta_y = self.get_dx_dy_from_target_position(point)
        diff = math.sqrt(delta_x ** 2 + delta_y ** 2)
        while diff > nearby_threshold:
            if self.stop_listen: return
            if time.time() - start_time > 15: raise MoveTimeoutException("移动地图超时！")
            delta_x, delta_y = self.get_dx_dy_from_target_position(point)
            diff = math.sqrt(delta_x ** 2 + delta_y ** 2)
            step = diff
            if step > nearby_threshold: step = nearby_threshold

            if abs(delta_x) > step: delta_x = (delta_x / abs(delta_x)) * step
            if abs(delta_y) > step: delta_y = (delta_y / abs(delta_y)) * step

            self.log(f'距离{point}还差{diff}, dx = {delta_x}, dy = {delta_y}')
            # 计算下一个拖动的起始位置
            self.drag(self.from_point(), delta_x, delta_y)

            delta_x, delta_y = self.get_dx_dy_from_target_position(point)
            if diff < nearby_threshold:
                self.log("结束移动地图")
                break

        self.move_mouse_to_anchor_position(point)


    def move_mouse_to_anchor_position(self, point):
        dx, dy = self.get_dx_dy_from_target_position(point)
        center = self.gc.get_genshin_screen_center()
        self.log(f'当前游戏中心位置{center},距离目标锚点 dx = {dx}, dy = {dy}')
        anchor_x = center[0] - dx * self.scale_x
        anchor_y = center[1] - dy * self.scale_y
        anchor_pos = (anchor_x, anchor_y)
        self.log('移动鼠标到最终位置{}'.format(anchor_pos))
        self.set_ms_position(anchor_pos)

    def transform(self, position, country, anchor_name=None, create_local_map_cache=True):
        """
        传送到指定锚点
        :param point:
        :return:
        """
        if self.stop_listen: return
        self.log(f"开始传送到{country}{position}, is_stop_listen = {self.stop_listen}")
        self.open_middle_map()  # 打开地图
        # self.middle_to_country(country)  # 切换侧边栏到指定地区
        self.scale_middle_map(country)  # 缩放比例调整（以及防止点到海域无法识别大地图)，并切换到指定地区

        try:
            self.move_to_point(position, country)  # 移动大地图到锚点位置（中心点)
        # 避免minimap全局匹配，直接指定区域缓存局部地图作为匹配
            self.tracker.create_cached_local_map(center=position)
            self.click_anchor(anchor_name)  # 点击传送锚点
        except (LocationException,MoveTimeoutException) as e:
            self.logger.error(f'移动过程中出现异常，正在重试传送{e}')
            self.close_middle_map()
            time.sleep(1)
            self.close_middle_map()
            self.transform(position,country,anchor_name, create_local_map_cache)
            return

        # 判断是否成功传送
        time.sleep(3)  # 等待传送完成
        # if self.ocr.is_text_in_screen("探索度", "地图"):
        #     self.log("屏幕上发现 '探索度' 和 ‘地图' 字样，认为传送失败，递归传送！")
        #     self.transform(position, country, create_local_map_cache)
        pos = self.tracker.get_position()  # 获取用户落地位置
        wait_time = 10
        while not pos:
            if self.stop_listen: return
            wait_time -= 1
            self.log(f"第{10 - wait_time}次数查询落地位置，请稍后")
            pos = self.tracker.get_position()
            time.sleep(1)
            if wait_time < 0:
                self.log("获取落地位置失败！递归传送中！")
                self.transform(position, country=country, anchor_name=anchor_name, create_local_map_cache=create_local_map_cache)
                return  # 避免执行后面的语句

        if self.stop_listen: return
        diff = math.sqrt((pos[0] - position[0]) ** 2 + (pos[1] - position[1]) ** 2)
        self.log(f"判断落地位置是否准确, 目标位置{position}, 当前位置{pos}, 计算距离{diff}")
        if diff > 200:
            self.log("落地误差太大！, 递归传送中！")
            self.transform(position, country, create_local_map_cache)
        else:
            self.log("落地误差符合预期，传送成功!")


# 6. 重复移动过程直到目的位置在地图的视野内。
# 7. * 计算该点位在当前视野中的相对位置(难点)
# 8. 点击该位置并传送（先不考虑锚点重叠的情况）


if __name__ == '__main__':
    # x, y, country, anchor_name = -7087.9789375, -6178.1590937, '枫丹', '临瀑之城'
    x, y, country, anchor_name = -6333.766653971354, -7277.06206087, '枫丹', None
    # x, y, country, anchor_name = 2552.0, -5804.0, '蒙德', '传送锚点'
    # x, y, country, anchor_name = 3040.0, -5620.0, '蒙德', None  # 蒙德钓鱼点1
    # x, y, country, anchor_name =256.94782031249997, 93.6250, '璃月', None  # 璃月港合成台
    # x, y, country, anchor_name = 254.45453417968747, 86.87346, '璃月', None  # 璃月港合成台
    # x, y, country, anchor_name = 8851, 7627, '稻妻', None  # 稻妻越石村

    mpc = MapController(debug_enable=True)
    # 传送锚点流程
    # 1. 按下M键打开大地图
    # res = mpc.open_middle_map()
    # 2. 切换到指定地区（依赖尘歌壶）
    # mpc.scale_middle_map(country)
    # mpc.move((x,y))
    # 3. 计算缩放比例
    # mp = mpc.tracker.get_user_map_position()
    # dx, dy = mpc.get_dx_dy_from_target_position((x, y))
    # print(mp, dx, dy)

    # 3. 将大地图移动到指定区域
    # mpc.move((x,y))
    # mpc.click_anchor(anchor_name)
    # 960 -> 2019
    # 4. 使用模板匹配检测屏幕内所有的锚点
    # center = gc.get_genshin_screen_center()
    # mpc.ms.position = center
    # mpc.ms.click(mpc.Button.left)

    # 5. 找到距离目标最近的锚点并点击
    # mpc.click_center_anchor()

    # 6. 筛选叠层锚点
    # 7. 选择筛选后的锚点并传送
    # mpc.transform((x,y),country, anchor_name)
    mpc.transform((x,y),country)
