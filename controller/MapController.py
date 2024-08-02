# 锚点传送测试
# 思路：
import math
import sys
import time
# from ocrtest.paddleocrtest.paddleocr_test3_findtext_click import find_text_and_click
from controller.BaseController import BaseController

import random


class MapController(BaseController):
    def __init__(self, tracker=None, ocr=None, debug_enable=False):
        super(MapController, self).__init__()

        if tracker is None:
            # from matchmap.sifttest.sifttest6_simple_middle_map import SimpleMiddleMap
            # tracker = SimpleMiddleMap(self.gc)
            from matchmap.minimap_interface import MinimapInterface
            tracker = MinimapInterface
        if ocr is None:
            from controller.OCRController import OCRController
            ocr = OCRController()

        self.stop_listen = False
        self.tracker = tracker
        self.debug_enable = debug_enable
        self.ocr = ocr

    def click_center_anchor(self, anchor_name='传送锚点'):
        center = self.gc.get_genshin_screen_center()
        self.ms.position = center
        self.ms.click(self.Button.left)  # 点击中心
        time.sleep(2)  # 等待这一步很重要
        if self.ocr.find_text_and_click(anchor_name):
            self.log("点击{}".format(anchor_name))
        elif self.ocr.find_text_and_click("七天神像"):
            self.log("点击七天神像")
        else:
            self.log("未能点击{}".format(anchor_name))

        time.sleep(2)
        self.ocr.find_text_and_click("传送", match_all=True)
        time.sleep(2)

    def kb_press(self, key):
        if self.stop_listen: return
        self.keyboard.press(key)

    def kb_release(self, key):
        # 即使停止了也要释放
        self.keyboard.release(key)

    # 1. 按下M键打开大地图
    def open_middle_map(self):
        time.sleep(1.5)
        open_ok = False
        self.log("按下m打开地图")
        for i in range(2):
            if not self.ocr.is_text_in_screen("探索度"):
                self.kb_release('m')
                self.kb_press('m')
                self.kb_release('m')
                time.sleep(1)
            else:
                open_ok = True
                break
        self.log(f"打开地图状态：{open_ok}")
        return open_ok



    def close_middle_map(self):
        self.log("正在关闭大地图")
        self.ui_close_button()
        time.sleep(1)
        self.ms.click(self.Button.left)

    # 2. 切换到固定的缩放大小（依赖层岩巨源）
    def scale_middle_map(self):
        self.log("正在调整地图比例")
        self.ocr.find_text_and_click("探索度")
        time.sleep(0.5)
        self.ocr.find_text_and_click("尘歌壶")
        time.sleep(0.5)
        self.ocr.find_text_and_click("洞天仙力")
        time.sleep(0.5)
        self.ocr.find_text_and_click("璃月")
        time.sleep(0.5)
        self.log("调整地图比例结束")

    def middle_to_country(self, country):
        if self.stop_listen: return
        """
        切换大地图到指定国家
        :param country:
        :return:
        """
        self.log("打开侧边栏的国家切换面板")
        self.ocr.find_text_and_click("探索度")
        time.sleep(1)
        self.log("寻找'{}'并尝试点击".format(country))
        if self.ocr.find_text_and_click(country, match_all=True):
            self.log("成功点击{}".format(country))
        else:
            self.log("未能点击{}，开始递归!".format(country))
            self.close_middle_map()
            self.open_middle_map()
            # 递归
            self.middle_to_country(country)

    # 3. 匹配地图，得到地图的中心点位置。
    def get_middle_map_position(self):
        return self.tracker.get_user_map_position()

    # 4. 计算地图的中心点位置和指定锚点位置的偏差，得到水平偏差dx和垂直偏差dy
    #     dx = target_position[0] - current_position[0]
    #     dy = target_position[1] - current_position[1]
    def get_dx_dy_from_target_position(self, target_position=None):
        if target_position is None: return 0, 0
        current_position = self.get_middle_map_position()
        if current_position is not None:
            try:
                dx = current_position[0] - target_position[0]
                dy = current_position[1] - target_position[1]
                return dx, dy
            except TypeError:
                self.log('type err')
        else:
            return 0, 0

    def from_point(self):
        center = self.gc.get_genshin_screen_center()
        random_size = 120
        # 添加随机数，防止被标记挡住
        x = center[0] + random.randint(-random_size, random_size)
        y = center[1] + random.randint(-random_size, random_size)
        return (x, y)

    def move_to_point(self, point, country):
        if self.stop_listen: return
        # self.move(point, 400, 800)  # 大步伐，大阈值使目标点出现在屏幕
        self.move2(point)  # 大步伐，大阈值使目标点出现在屏幕
        # self.move(point, 200, 300)  # 小阈值慢慢调整到中心
        # self.move(point, 100, 200)  # 小阈值慢慢调整到中心
        # self.move(point, 50, 100)  # 小阈值慢慢调整到中心
        # self.move(point, 30, 30)  # 小阈值慢慢调整到中心

        # 如果发现当前偏移太严重，则递归
        delta_x, delta_y = self.get_dx_dy_from_target_position(point)
        if abs(delta_x) > 50 or abs(delta_y) > 50:
            self.log("偏移严重，递归调用move_to_point中!")
            self.move_to_point(point, country)

    # 5. 根据偏差移动地图。 注意移动的时候鼠标的拖动位置不能点到锚点，否则会无法拖动，因此可以给鼠标加上一个随机偏差
    def move(self, point, step=150, near_by_threshold=400):
        if self.stop_listen: return
        # 根据当前位置与下一个点位的差值决定移动方向和距离
        x_stop, y_stop = False, False
        move_times = 50
        while not x_stop or not y_stop:
            if self.stop_listen:
                break
            move_times -= 1
            if move_times < 0:
                self.log("移动次数过多，停止执行")
                break
            delta_x, delta_y = self.get_dx_dy_from_target_position(point)
            if abs(delta_y) < near_by_threshold: y_stop = True
            if abs(delta_x) < near_by_threshold: x_stop = True

            self.log("dx,dy", delta_x, delta_y)
            # 如何避免漂移？
            if abs(delta_y) > near_by_threshold * 2 or abs(delta_x) > near_by_threshold * 2:
                self.log("似乎出现了漂移，重新调整移动阈值")
                step = near_by_threshold * 2
                near_by_threshold = near_by_threshold * 2
                if step > 400: step = 400
                if near_by_threshold > 500: near_by_threshold = 500

            if not x_stop:
                if delta_x > 0:
                    self.log("向右移动")
                    self.drag(self.from_point(), step, 0)
                else:
                    self.log("向左移动")
                    self.drag(self.from_point(), -step, 0)
            if not y_stop:
                if delta_y > 0:
                    self.log("向下移动")
                    self.drag(self.from_point(), 0, step)
                else:
                    self.drag(self.from_point(), 0, -step)
                    self.log("向上移动")

        # 已经接近，停止
        self.log("结束移动")

    def move2(self, point):
        if self.stop_listen: return
        # 根据当前位置与下一个点位的差值决定移动方向和距离
        x_stop, y_stop = False, False
        near_by_threshold_final = 30  # 锚点在中心的误差(像素)

        move_limit_counter = 40  # 移动次数限制
        while not x_stop or not y_stop:
            if self.stop_listen: break  # 监听调试用
            move_limit_counter -= 1
            if move_limit_counter < 0:
                self.log("移动次数过多，停止执行")
                break

            # 当前地图的位置距离目标锚点的横向距离delta_x以及纵向距离delta_y
            delta_x, delta_y = self.get_dx_dy_from_target_position(point)

            # 设置步长为距离的1/2以防止原地打转
            x_step_dynamic = abs(delta_x) // 2
            y_step_dynamic = abs(delta_y) // 2

            # 限制步长
            if x_step_dynamic > 500: x_step_dynamic = 500
            elif x_step_dynamic < 30: x_step_dynamic = 30
            if y_step_dynamic > 500: y_step_dynamic = 500
            elif y_step_dynamic < 30: y_step_dynamic = 30

            # 认为接近，则停止移动
            if abs(delta_y) < near_by_threshold_final: y_stop = True
            if abs(delta_x) < near_by_threshold_final: x_stop = True
            self.log("dx,dy", delta_x, delta_y)

            if not x_stop:
                if delta_x > 0:
                    self.log("向右移动")
                    self.drag(self.from_point(), x_step_dynamic, 0)
                else:
                    self.log("向左移动")
                    self.drag(self.from_point(), -x_step_dynamic, 0)
            if not y_stop:
                if delta_y > 0:
                    self.log("向下移动")
                    self.drag(self.from_point(), 0, y_step_dynamic)
                else:
                    self.drag(self.from_point(), 0, -y_step_dynamic)
                    self.log("向上移动")

        # 已经接近，停止
        self.log("结束移动")

    def transform(self, position, country, create_local_map_cache=True):
        """
        传送到指定锚点
        :param point:
        :return:
        """
        self.log("开始传送到{}{}".format(country, position))
        self.open_middle_map()  # 打开地图
        self.scale_middle_map()  # 缩放比例调整（以及防止点到海域无法识别大地图)
        self.middle_to_country(country)  # 切换侧边栏到指定国家
        self.move_to_point(position, country)  # 移动大地图到锚点位置（中心点)
        # 避免minimap全局匹配，直接指定区域缓存局部地图作为匹配
        self.tracker.create_cached_local_map(use_middle_map=create_local_map_cache)
        self.click_center_anchor()  # 点击中心点传送
        # 判断是否成功传送
        time.sleep(3)  # 等待传送完成
        if self.ocr.is_text_in_screen("探索度", "地图"):
            self.log("屏幕上发现 '探索度' 和 ‘地图' 字样，认为传送失败，递归传送！")
            self.transform(position, country, create_local_map_cache)

        pos = self.tracker.get_position()  # 获取用户落地位置
        wait_time = 10
        while not pos:
            wait_time -= 1
            self.log(f"第{10 - wait_time}次数查询落地位置，请稍后")
            pos = self.tracker.get_position()
            time.sleep(1)
            if wait_time < 0:
                self.log("获取落地位置失败！递归传送中！")
                self.transform(position, country, create_local_map_cache)
                return  # 避免执行后面的语句

        if pos is None:
            self.log('获取位置为空！')
            return
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
    import cv2

    mpc = MapController(debug_enable=True)
    # 传送锚点流程
    # 1. 按下M键打开大地图
    # res = mpc.open_middle_map()
    # 2. 切换到固定的缩放大小（依赖尘歌壶）
    # mpc.scale_middle_map()
    # 3. 将大地图移动到指定区域
    # move((2552.0, -5804.0), country='蒙德')  # 蒙德城
    # mpc.move_to_point((9117.5, 7240.5), country='须弥')  # 钓鱼点1
    # mpc.tracker.create_cached_local_map(use_middle_map=True)
    # mpc.transform((3040.0, -5620.0), country='蒙德')  # 蒙德钓鱼点1
    # mpc.transform((8851, 7627), '稻妻')
    # mpc.transform((253, 92), '璃月')  # 璃月港合成台

    x = -7211.0463203125
    y = -10998.844579589844
    mpc.transform((x,y), '枫丹')
    # 4. 使用模板匹配检测屏幕内所有的锚点
    # center = gc.get_genshin_screen_center()
    # mpc.ms.position = center
    # mpc.ms.click(mpc.Button.left)

    # 5. 找到距离目标最近的锚点并点击
    # mpc.click_center_anchor()

    # 6. 筛选叠层锚点
    # 7. 选择筛选后的锚点并传送
