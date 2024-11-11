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
# TODO 3. 未开启的锚点会一直循环传送
# TODO [紧急] 4. 传送过程鼠标点击到游戏外面导致游戏失去焦点！

class LocationException(Exception):
    pass


class WorldCoordinateException(Exception): pass


class MoveTimeoutException(Exception):
    pass

class ScaleChangeException(Exception):
    pass

class TeleportTimeoutException(Exception):pass


class MapController(BaseController):

    def __init__(self, ocr=None, debug_enable=False):
        super(MapController, self).__init__(debug_enable)
        if ocr is None:
            from controller.OCRController import OCRController
            ocr = OCRController(debug_enable)
        self.stop_listen = False
        self.debug_enable = debug_enable
        self.ocr = ocr
        self.target_waypoint = None

        self.ui_map_scale = None # 注意这个scale是值地图的缩放，而不是像素和世界坐标比例

        pix2world_scale = self.tracker.get_user_map_scale()
        if pix2world_scale is not None:
            (self.pix2world_scale_x, self.pix2world_scale_y) = pix2world_scale
            self.log('大地图移动比例', self.pix2world_scale_x, self.pix2world_scale_y)
        else:
            self.log('无法获取大地图比例')

    def click_waypoint(self, waypoint_name=None):
        if waypoint_name is None:
            waypoint_name = '传送锚点'
        self.mouse_left_click()  # 点击锚点
        try:
            time.sleep(0.3)
            if self.click_if_appear(self.gc.icon_button_teleport, timeout=1):
                return
        except TimeoutError:
            self.logger.debug("查找传送图标超时，尝试使用ocr")

        # 尝试点击传送
        if self.ocr.find_text_and_click('传送', match_all=True):
            self.log('点击传送成功')
            return
            # 没有传送，说明可能出现了重合的锚点。
            # 如果是指定了名称锚点，则点击指定名称锚点, 否则点击默认名称'传送锚点'
        elif self.ocr.find_text_and_click(waypoint_name):
            self.log(f"点击{waypoint_name}")
            # 如果都没有，可能是重合了七天神像，点击七天神像
        elif self.ocr.find_text_and_click("七天神像"):
            self.log("点击七天神像")
        else:
            self.log(f"未能点击'{waypoint_name}'")
        # 最后点击传送
        try:
            if self.click_if_appear(self.gc.icon_button_teleport, timeout=1):
                return
        except TimeoutError:
            self.logger.debug("查找传送图标超时，尝试使用ocr")
            self.ocr.find_text_and_click("传送", match_all=True)

    def get_world_coordinate(self, screen_points):
        """
        传入一组坐标，根据屏幕坐标得到世界坐标
        :param screen_points:
        :return:
        """
        user_map_position = self.tracker.get_user_map_position()
        scale = self.tracker.get_user_map_scale()
        w, h = self.gc.w, self.gc.h

        mission_world_points = []
        for screen_point in screen_points:
            if not user_map_position or not scale: raise WorldCoordinateException("获取世界坐标失败，请重试")
            dx = screen_point[0] - w / 2
            dy = screen_point[1] - h / 2
            world_x = user_map_position[0] + dx / scale[0]
            world_y = user_map_position[1] + dy / scale[1]
            mission_world_points.append((world_x, world_y))
        return mission_world_points

    def kb_press(self, key):
        if self.stop_listen: return
        super().kb_press(key)

    def kb_release(self, key):
        # 即使停止了也要释放
        super().kb_release(key)

    # 1. 按下M键打开大地图
    def open_middle_map(self):
        # time.sleep(1.5)
        open_ok = False
        self.log("按下m打开地图")
        start_time = time.time()
        while time.time() - start_time < 5:
            # 出现按钮，可能是死亡复苏弹窗
            confirm_buttons = self.gc.get_icon_position(self.gc.icon_message_box_button_confirm)
            if len(confirm_buttons) > 0:
                if self.ocr.find_text_and_click('复苏'):
                    self.logger.error('角色死亡，点击复苏')

            if self.gc.has_map_sidebar_toggle():
                open_ok = True
                break
            self.kb_press_and_release('m')
            time.sleep(1)
        self.log(f"打开地图状态：{open_ok}")
        return open_ok

    def close_middle_map(self):
        self.log("正在关闭大地图")
        self.click_ui_close_button()


    # 2. 切换到固定的缩放大小
    def scales_adjust(self, percentage=None):
        # 实测滚动从地图最小缩放到最大需要滚动61次, 而且每次滚轮缩放变化是线性的
        # 因此调整比例的时候，只需要先把它拉到最小，然后按照比例调整缩放次数即可
        max_scale = 61
        if percentage:
            self.zoom_out(max_scale)
            time.sleep(0.3)
            self.ui_map_scale = percentage
            self.zoom_in(int(max_scale*percentage))

        if self.ui_map_scale is None or self.ui_map_scale < 0.35 or self.ui_map_scale > 0.8:
            # 如果人为改变了地图的scale，是没办法感知的, 因此必须要每次都调整。
            self.ui_map_scale = 0.5
            self.zoom_out(max_scale)
            time.sleep(0.3)
            self.zoom_in(int(max_scale*self.ui_map_scale))

        time.sleep(0.5)

        scale = self.tracker.get_user_map_scale()
        start_time = time.time()
        while not scale:
            self.log(f"正在请求地图比例中，剩余{10 - (time.time()-start_time)}秒")
            if time.time() - start_time > 10:
                raise ScaleChangeException("无法请求缩放比例")
            scale = self.tracker.get_user_map_scale()
            time.sleep(1)

        self.pix2world_scale_x,self.pix2world_scale_y = scale[0], scale[1]
        self.log(f"调整地图比例结束, 最终结果为{scale}")

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
        if not self.is_waypoint_appear_in_screen(point=point):
            # 如果发现当前偏移太严重，则递归
            self.log("目标锚点没有出现在屏幕内，递归调用移动中！")
            self.move_to_point(point)
            return

    def is_waypoint_appear_in_screen(self, point):
        """
        锚点是否出现在屏幕内
        :return:
        """
        # 计算实际距离
        delta_x, delta_y = self.get_dx_dy_from_target_position(point)
        # 转换成拖拽距离
        delta_screen_x = delta_x * self.pix2world_scale_x
        delta_screen_y = delta_y * self.pix2world_scale_y

        if delta_screen_x < 0:
            return abs(delta_screen_x) < self.gc.w // 2 - 150 and abs(delta_screen_y) < self.gc.h // 2 - 150
        else:
            # 避免点击到左上角的文字
            return abs(delta_screen_x) < self.gc.w // 3-50 and abs(delta_screen_y) < self.gc.h //2 - 150

        # delta_x, delta_y = self.get_dx_dy_from_target_position(point)
        # diff = math.sqrt(delta_x ** 2 + delta_y ** 2)
        # return diff < waypoint_appear_threshold

    # 5. 根据偏差移动地图。 注意移动的时候鼠标的拖动位置不能点到锚点，否则会无法拖动，因此可以给鼠标加上一个随机偏差
    # def move2(self, point):  # 中心点与锚点的距离阈值, 超过这个阈值就一直移动
    #     if self.stop_listen: return
    #     start_time = time.time()
    #
    #     # 锚点不在屏幕内则一直执行
    #     while not self.is_waypoint_appear_in_screen(point):
    #         if self.stop_listen: return
    #         if time.time() - start_time > 15: raise MoveTimeoutException("移动地图超时！")
    #
    #         # 计算实际距离
    #         delta_x, delta_y = self.get_dx_dy_from_target_position(point)
    #
    #         # 转换成拖拽距离
    #         delta_screen_x = delta_x * self.pix2world_scale_x
    #         delta_screen_y = delta_y * self.pix2world_scale_y
    #
    #         # 限制不要拖拽到屏幕外面
    #         if abs(delta_screen_x) > self.gc.w // 2: delta_screen_x = (delta_x / abs(delta_x)) * self.gc.w // 2
    #         if abs(delta_screen_y) > self.gc.h // 2: delta_screen_y = (delta_y / abs(delta_y)) * self.gc.h // 2
    #
    #         diff = math.sqrt(delta_x ** 2 + delta_y ** 2)
    #         self.log(f'距离{point}还差{diff}, dx = {delta_x}, dy = {delta_y}')
    #
    #         # 给起始拖拽位置添加随机数, 以防止拖动时点到标签无法拖动
    #         # 添加随机数，防止被标记挡住(但是添加随机数后有可能拖到屏幕外，暂时没啥异常，先不处理吧...)
    #         self.drag(self.random_point(), delta_screen_x, delta_screen_y)
    #     self.move_mouse_to_waypoint_position(point)

    def move(self, point):
        if self.stop_listen: return
        start_time = time.time()
        while not self.is_waypoint_appear_in_screen(point):
            if time.time() - start_time > 15: raise MoveTimeoutException("移动地图超时！")
            # 计算实际距离
            delta_x, delta_y = self.get_dx_dy_from_target_position(point)

            # 转换成拖拽距离
            delta_screen_x = delta_x * self.pix2world_scale_x
            delta_screen_y = delta_y * self.pix2world_scale_y

            # 计算拖拽次数
            # 假设一次仅移动100像素，那么x和y就确定了, 但是似乎drag方法实现不够好，达不到拖动的距离
            # 总距离 / 100 = 总x/drag_x = 总y/drag_y
            total_displacement = math.sqrt(delta_x ** 2 + delta_y ** 2)
            drag = 1000
            count = total_displacement / drag
            count = int(count) + 1
            if count > 25:
                raise LocationException(f"移动次数为{count}, 过大!")

            if delta_screen_x != 0: drag_x = (delta_screen_x*drag) / total_displacement
            else: drag_x = 0
            if delta_screen_y != 0: drag_y = (delta_screen_y*drag) / total_displacement
            else: drag_y = 0
            self.logger.debug(f'{drag_x}, {drag_y}')
            for _ in range(count):
                self.drag(self.random_point(), drag_x, drag_y)



    def choose_country(self, country):
        self.click_screen((self.gc.w - 80, self.gc.h-50))  # 打开选择器
        time.sleep(0.5)
        # 有些文字无法全文匹配，则用模糊匹配
        from matchmap.sifttest.sifttest6 import MiniMap
        if country == '层岩巨渊':
            self.ocr.find_text_and_click('层岩巨渊')  # 不使用全文匹配
        else:
            self.ocr.find_text_and_click(country, match_all=True)  # 全文字匹配避免点击到每日委托
        self.tracker.choose_map(country)

    def move_mouse_to_waypoint_position(self, point):
        dx, dy = self.get_dx_dy_from_target_position(point)
        center = self.gc.get_genshin_screen_center()
        self.log(f'当前游戏中心位置{center},距离目标锚点 dx = {dx}, dy = {dy}')
        waypoint_x = center[0] - dx * self.pix2world_scale_x
        waypoint_y = center[1] - dy * self.pix2world_scale_y
        waypoint_pos = (waypoint_x, waypoint_y)
        self.log('移动鼠标到最终位置{}'.format(waypoint_pos))
        self.set_ms_position(waypoint_pos)

        # 检查鼠标位置是否超过了屏幕窗口，超过则抛异常
        in_game = abs(dx*self.pix2world_scale_x) * 2 < self.gc.w and abs(dy*self.pix2world_scale_y)*2 < self.gc.h
        if not in_game:
            self.logger.error("超出游戏窗口范围!")
            raise LocationException("鼠标位置超出游戏窗口范围异常！")

    def teleport(self, position, country, waypoint_name=None, create_local_map_cache=True, start_teleport_time=None, validate_position=True):
        """
        传送到指定锚点
        :param point: 必填，目标地址
        :param country: 必填，所在地图
        :param waypoint_name: 为了避免一些标记遮挡，如果是副本请填写副本名称。默认为传送锚点
        :param create_local_map_cache: 创建目标地点的定位缓存
        :param start_teleport_time: 外界调用时候，传入 time.time()作为起始传送时间，避免无限递归, 超时默认时间为60秒
        :param validate_position: 传送后是否校验落地位置，当前版本水下位置无法校验，此时需要关掉校验，例如枫丹的副本'苍白的遗容'，需要设置为False
        :return:
        """
        if waypoint_name == '苍白的遗荣':
            self.logger.warn(f'水下副本由于无法定位，强制关闭落地校验: {waypoint_name}')
            validate_position = False
        if start_teleport_time is not None:
            if time.time() - start_teleport_time > 60:
                raise TeleportTimeoutException("超过1分钟传送失败, 停止传送")

        if self.stop_listen: return
        self.log(f"开始传送到{country}{position}, is_stop_listen = {self.stop_listen}")
        self.open_middle_map()  # 打开地图
        self.choose_country(country)
        time.sleep(0.5)
        try:
            self.scales_adjust()  # 缩放比例调整
            self.move_to_point(position)  # 移动大地图直到目标锚点出现在可视范围内
            # 避免minimap全局匹配，直接指定区域缓存局部地图作为匹配
            self.move_mouse_to_waypoint_position(position)
            self.tracker.create_cached_local_map(center=position)
            self.click_waypoint(waypoint_name)  # 点击传送锚点
            time.sleep(1)
            if self.gc.has_tob_bar_close_button() or self.gc.has_origin_resin_in_top_bar():
                self.logger.debug("仍然在地图界面, 重试中")
                self.close_middle_map()
                time.sleep(0.5)
                self.close_middle_map()
                self.teleport(position, country, waypoint_name, create_local_map_cache,start_teleport_time=start_teleport_time)
                return
        except (LocationException, MoveTimeoutException, ScaleChangeException) as e:
            self.logger.error(f'移动过程中出现异常，正在重试传送{e}')
            self.close_middle_map()
            time.sleep(0.5)
            self.close_middle_map()
            self.teleport(position, country, waypoint_name, create_local_map_cache, start_teleport_time=start_teleport_time)
            return

        # 判断是否成功传送
        time.sleep(3)  # 等待传送完成
        if not validate_position:
            self.logger.debug("你取消了传送落地校验")
            return

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
                self.teleport(position, country=country, waypoint_name=waypoint_name,
                              create_local_map_cache=create_local_map_cache, start_teleport_time=start_teleport_time)
                return  # 避免执行后面的语句

        if self.stop_listen: return
        diff = math.sqrt((pos[0] - position[0]) ** 2 + (pos[1] - position[1]) ** 2)
        self.log(f"判断落地位置是否准确, 目标位置{position}, 当前位置{pos}, 计算距离{diff}")
        if diff > 200:
            self.log("落地误差太大！, 递归传送中！")
            self.teleport(position, country, waypoint_name, create_local_map_cache, start_teleport_time=start_teleport_time)
        else:
            self.log("落地误差符合预期，传送成功!")

    def go_to_seven_anemo_for_revive(self):
        """
        前往七天神像回血
        :return:
        """
        self.logger.debug("前往七天神像")
        # x,y, country = 287.70, -3805.00, "璃月"
        x,y, country = 2840.7353515625, -3591.64, "蒙德"
        # x,y, country = 1944.8270,-4954.61, "蒙德"
        self.teleport((x, y), country, "七天神像", start_teleport_time=time.time())
        time.sleep(2)  # 等待回血完成


    def turn_off_custom_tag(self):
        self.logger.debug("关掉自定义标签")
        """
        关掉自定义标记,避免遮挡
        :return:
        """
        self.click_if_appear(self.gc.icon_map_setting_gear)
        time.sleep(0.5)
        self.click_if_appear(self.gc.icon_map_setting_on)
        time.sleep(0.5)
        self.click_if_appear(self.gc.icon_close_while_arrow)


# 6. 重复移动过程直到目的位置在地图的视野内。
# 7. * 计算该点位在当前视野中的相对位置(难点)
# 8. 点击该位置并传送（先不考虑锚点重叠的情况）


if __name__ == '__main__':
    # x, y, country, waypoint_name = -7087.9789375, -6178.1590937, '枫丹', '临瀑之城'
    # x, y, country, waypoint_name = -6333.766653971354, -7277.06206087, '枫丹', None
    # x, y, country, waypoint_name = 2552.0, -5804.0, '蒙德', '传送锚点'
    # x, y, country, waypoint_name = 1949.4441874999993, -4945.9832421875, '蒙德', '传送锚点'  # 蒙德清泉镇
    # x, y, country, waypoint_name = 3040.0, -5620.0, '蒙德', None  # 蒙德钓鱼点1
    # x, y, country, waypoint_name =256.94782031249997, 93.6250, '璃月', None  # 璃月港合成台
    # x, y, country, waypoint_name = 254.45453417968747, 86.87346, '璃月', None  # 璃月港合成台
    # x, y, country, waypoint_name = 8851, 7627, '稻妻', None  # 稻妻越石村
    # x, y, country, waypoint_name = 1306.567, -6276.533, '蒙德', '塞西莉亚苗圃'  # 稻妻越石村
    # x, y, country, waypoint_name = 1219.2486572265625, 516.2448, '层岩巨渊', '传送锚点'
    # x, y, country, waypoint_name = 1807.72, 1708.72, '渊下宫', '传送锚点'
    x, y, country, waypoint_name = 686.87,2448.96, '渊下宫', '传送锚点'
    mpc = MapController(debug_enable=True)
    # mpc.turn_off_custom_tag()
    # mpc.go_to_seven_anemo_for_review()
    # while True:
    #     from matchmap.minimap_interface import MinimapInterface
    #     sc = MinimapInterface.get_user_map_scale()
    #     print(sc)
    #     time.sleep(1)

    # 传送锚点流程
    # 1. 按下M键打开大地图
    # res = mpc.open_middle_map()
    # 2. 切换到指定地区
    # time.sleep(0.2)
    # mpc.scale_middle_map(country)
    # mpc.move((x,y))
    # 3. 计算缩放比例
    # mp = mpc.tracker.get_user_map_position()
    # dx, dy = mpc.get_dx_dy_from_target_position((x, y))
    # print(mp, dx, dy)

    # 3. 将大地图移动到指定区域
    # mpc.move_to_point((x,y))
    # mpc.click_waypoint(waypoint_name)
    # 960 -> 2019
    # 4. 使用模板匹配检测屏幕内所有的锚点
    # center = gc.get_genshin_screen_center()
    # mpc.ms.position = center
    # mpc.ms.click(mpc.Button.left)

    # 5. 找到距离目标最近的锚点并点击
    # mpc.click_center_waypoint()

    # 6. 筛选叠层锚点
    # 7. 选择筛选后的锚点并传送
    # mpc.teleport((x, y), country, waypoint_name, start_teleport_time=time.time())
    # mpc.go_to_seven_anemo_for_revive()
    mpc.teleport((x,y),country)
