# 锚点传送测试
# 思路：
import math
import sys
import time
from controller.BaseController import BaseController
import random

# TODO 1. 传送点自动选择最近的国家。
#   <del>已知点击侧边栏的时候会自动跳转到城镇中心，把这些中心坐标存起来，在传送的时候距离哪个近就点击哪个国家。<del/>
#   未来会加入巨渊、渊下宫的支持，这些信息应当由记录的时候提供。
# TODO 2. 如何解决移动地图时的漂移问题
# TODO 3. 不同电脑缩放比例不同。
# TODO 4. 缩放到最大时，点击不精准（换纳兰那点位，似乎是传送锚点本身坐标的问题）
# TODO 5. 传送锚点名称如果不是副本，且同时存在其他标记，可能会无法点击

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
        self.target_anchor = None

        scale = self.tracker.get_user_map_scale()
        if scale is not None:
            (self.scale_x, self.scale_y) = scale
            self.log('大地图移动比例', self.scale_x, self.scale_y)
        else:
            self.log('无法获取大地图比例')

    def click_anchor(self, anchor_name=None):
        if anchor_name is None:
            anchor_name = '传送锚点'
        self.mouse_left_click()  # 点击锚点
        # TODO: 做成wait_for_screen_text(anchor_name)
        time.sleep(1)  # 等待这一步很重要
        # 尝试点击传送
        if self.ocr.find_text_and_click('传送', match_all=True):
            self.log('点击传送成功')
            return
            # 没有传送，说明可能出现了重合的锚点。
            # 如果是指定了名称锚点，则点击指定名称锚点, 否则点击默认名称'传送锚点'
        elif self.ocr.find_text_and_click(anchor_name):
            self.log(f"点击{anchor_name}")
            # 如果都没有，可能是重合了七天神像，点击七天神像
        elif self.ocr.find_text_and_click("七天神像"):
            self.log("点击七天神像")
        else:
            self.log(f"未能点击'{anchor_name}'")
        # 最后点击传送
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
        for i in range(3):
            if not self.ocr.is_text_in_screen("探索度"):
                self.kb_press_and_release('m')
                time.sleep(1)
            else:
                open_ok = True
                break
        self.log(f"打开地图状态：{open_ok}")
        return open_ok

    def close_middle_map(self):
        self.log("正在关闭大地图")
        self.ui_close_button()

    def zoom_out(self, delta=-1000):
        for _ in range(20):
            # win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            time.sleep(0.01)  # 短暂等待，防止事件过于密集
            self.ms_scroll(0, delta)
    def zoom_in(self, delta=1000):
        for _ in range(20):
            # win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            time.sleep(0.01)  # 短暂等待，防止事件过于密集
            self.ms_scroll(0, delta)

    # 2. 切换到固定的缩放大小（依赖层岩巨源）
    def scale_middle_map(self):
        scale = self.tracker.get_user_map_scale()
        for i in range(10):
            self.log(f"正在请求地图比例中，剩余{10-i}秒")
            if scale: break
            scale = self.tracker.get_user_map_scale()
            time.sleep(1)
        self.log(f'请求比例结果为{scale}')
        if scale[0] < 0.28 or scale[1] < 0.28:
            self.log('地图缩放不合理，尝试放大')
            self.zoom_in()
            self.scale_middle_map()
            return

        (self.scale_x, self.scale_y) = scale
        self.log("调整地图比例结束")

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

    def random_point(self):
        center = self.gc.get_genshin_screen_center()
        # 添加随机数，防止被标记挡住
        x = center[0] + random.randint(-80, 80)
        y = center[1] + random.randint(-120, 120)
        return (x, y)

    def move_to_point(self, point):
        if self.stop_listen: return

        self.move(point)  # 移动
        if not self.is_anchor_appear_in_screen(point=point):
            # 如果发现当前偏移太严重，则递归
            self.log("目标锚点没有出现在屏幕内，递归调用移动中！")
            self.move_to_point(point)
            return

    def is_anchor_appear_in_screen(self, point):
        """
        锚点是否出现在屏幕内
        :return:
        """
        anchor_appear_threshold = min(self.gc.h, self.gc.w) // 2 - 20
        delta_x, delta_y = self.get_dx_dy_from_target_position(point)
        diff = math.sqrt(delta_x ** 2 + delta_y ** 2)
        return diff < anchor_appear_threshold

    # 5. 根据偏差移动地图。 注意移动的时候鼠标的拖动位置不能点到锚点，否则会无法拖动，因此可以给鼠标加上一个随机偏差
    def move(self, point):  # 中心点与锚点的距离阈值, 超过这个阈值就一直移动
        if self.stop_listen: return
        start_time = time.time()

        # 锚点不在屏幕内则一直执行
        while not self.is_anchor_appear_in_screen(point):
            if self.stop_listen: return
            if time.time() - start_time > 15: raise MoveTimeoutException("移动地图超时！")

            # 计算实际距离
            delta_x, delta_y = self.get_dx_dy_from_target_position(point)

            # 转换成拖拽距离
            delta_screen_x = delta_x * self.scale_x
            delta_screen_y = delta_y * self.scale_y

            # 限制不要拖拽到屏幕外面
            if abs(delta_screen_x) > self.gc.w // 2 : delta_screen_x = (delta_x / abs(delta_x)) * self.gc.w//2
            if abs(delta_screen_y) > self.gc.h // 2 : delta_screen_y = (delta_y / abs(delta_y)) * self.gc.h//2

            diff = math.sqrt(delta_x ** 2 + delta_y ** 2)
            self.log(f'距离{point}还差{diff}, dx = {delta_x}, dy = {delta_y}')

            # 给起始拖拽位置添加随机数, 以防止拖动时点到标签无法拖动
            # 添加随机数，防止被标记挡住(但是添加随机数后有可能拖到屏幕外，暂时没啥异常，先不处理吧...)
            self.drag(self.random_point(), delta_screen_x, delta_screen_y)

        self.move_mouse_to_anchor_position(point)

    def choose_country(self, country):
        txts = self.ocr.find_match_text("探索度")
        if len(txts) > 1:
            self.log('发现多个探索度，缩放不合理,尝试放大地图')
            self.zoom_in()
            time.sleep(0.5)
        self.ocr.find_text_and_click("探索度")
        time.sleep(0.5)
        self.ocr.find_text_and_click(country, match_all=True)  # 全文字匹配避免点击到每日委托


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
        self.choose_country(country)
        time.sleep(0.5)
        self.scale_middle_map()  # 缩放比例调整

        try:
            self.move_to_point(position)  # 移动大地图直到目标锚点出现在可视范围内
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
    # x, y, country, anchor_name = -6333.766653971354, -7277.06206087, '枫丹', None
    # x, y, country, anchor_name = 2552.0, -5804.0, '蒙德', '传送锚点'
    # x, y, country, anchor_name = 1949.4441874999993, -4945.9832421875, '蒙德', '传送锚点'  # 蒙德清泉镇
    # x, y, country, anchor_name = 3040.0, -5620.0, '蒙德', None  # 蒙德钓鱼点1
    # x, y, country, anchor_name =256.94782031249997, 93.6250, '璃月', None  # 璃月港合成台
    # x, y, country, anchor_name = 254.45453417968747, 86.87346, '璃月', None  # 璃月港合成台
    x, y, country, anchor_name = 8851, 7627, '稻妻', None  # 稻妻越石村
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
    mpc.transform((x,y),country, anchor_name)
    # mpc.transform((x,y),country)
