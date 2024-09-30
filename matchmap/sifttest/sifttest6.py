import logging
import os.path
import sys
import time
from typing import List

import cv2
import numpy
import numpy as np
from capture.capture_factory import capture
from myutils.configutils import resource_path
from myutils.kp_gen import load
from myutils.timerutils import RateLimiterAsync
from myutils.imgutils import crop_img
from myutils.sift_utils import get_match_position, get_match_position_with_good_match_count, get_match_corner, \
    MatchException

gs = capture
from mylogger.MyLogger3 import MyLogger
from myutils.configutils import MapConfig, DebugConfig, PathExecutorConfig
import threading

# TODO: 优化思路：
# 可以把每个国家的地图分割开，以后版本也不用动以前的地图。
# 记录：记录时，必须传入国家或者地区名称，然后匹配器根据名称加载对应的大地图进行全局匹配。
# 鼠标点击某个国家时，一定会有一个确定的中心点，往后记录的点位路径都以此为中心
# 回放时，根据记录的
# TODO: 有没有办法不改动代码，只改动配置的情况下增加地图？


class SiftMap:

    def __init__(self, map_name, block_size,img, des, kep, center, scale=1, sift=None):
        self.map_name = map_name
        self.block_size = block_size
        self.img = img
        self.des:numpy.ndarray = des
        self.kep: List[cv2.KeyPoint] = kep
        self.center = center
        self.scale = scale
        self.sift = sift
        if self.sift is None: self.sift = cv2.SIFT.create()
class SiftMapNotFoundException(Exception):
    pass

# TODO: 越界时，得到的坐标异常？
class MiniMap:
    __map_dict = dict()

    @staticmethod
    def get_sift_map(map_name, block_size) -> SiftMap:
        # map_pinyin = MiniMap.cn_text_map.get(map_name)

        map_conf = MapConfig.get(map_name, None)
        if map_conf is None:
            raise SiftMapNotFoundException(f"指定的地图{map_name}未找到")
        key = f'{map_conf.get("img_name")}_{block_size}'
        map_obj = MiniMap.__map_dict.get(key)
        if map_obj is None:
            # logger.debug(f"加载{map_name}图片中...........")
            img_name = map_conf.get('img_name')
            map_center = map_conf.get('center')
            map_version = map_conf.get('version')
            map_path = os.path.join(resource_path, 'map', 'segments', f'{img_name}_{block_size}_v{map_version}.png')
            img = cv2.imread(map_path, cv2.IMREAD_GRAYSCALE)
            # cv2.imshow(map_pinyin, cv2.resize(img, None, fx=0.1,fy=0.1))
            # cv2.waitKey(0)

            kep, des = load(block_size=block_size, map_name=img_name, map_version=map_version)
            scale = map_conf.get('scale')
            if scale is not None:
                img = cv2.resize(img, None, fx=scale, fy=scale)
                for k in kep:
                    k.pt = (k.pt[0]*scale, k.pt[1]*scale)
            sigma = map_conf.get('sigma')
            contrastThreshold = map_conf.get('contrastThreshold')
            sift = cv2.SIFT.create()
            if sigma is not None: sift.setSigma(sigma)
            if contrastThreshold is not None: sift.setContrastThreshold(contrastThreshold)

            MiniMap.__map_dict[key] = SiftMap(map_name=map_name, block_size=block_size, img=img, des=des, kep=kep,
                                      center=map_center, sift=sift)
        return MiniMap.__map_dict[key]

    def __init__(self, debug_enable=None):
        """
        :param debug_enable:
        :param gc: GenshinCapture instance
        """
        self.logger = MyLogger(__class__.__name__, logging.DEBUG, save_log=True)
        if debug_enable is None:
            debug_enable = DebugConfig.get(DebugConfig.KEY_DEBUG_ENABLE, True)
            if debug_enable: self.logger = MyLogger(__class__.__name__,level=logging.DEBUG, save_log=True)

        self.debug_enable = debug_enable
        self.cache_lock = threading.Lock()
        self.set_good_count_lock = threading.Lock()
        # https://docs.opencv.org/4.x/d7/d60/classcv_1_1SIFT.html
        # from myutils.kp_gen import load
        t0 = time.time()
        # 地图资源加载
        self.map_2048:SiftMap = None
        self.map_256:SiftMap = None
        # 确定中心点
        self.PIX_CENTER_AX = None
        self.PIX_CENTER_AY = None

        self.choose_map('璃月')

        local_map_size = PathExecutorConfig.get(
            PathExecutorConfig.KEY_LOCAL_MAP_SIZE, 1024, min_val=512, max_val=4096)
        self.logger.info(f'搜索范围设置为{local_map_size}')
        self.local_map_size = local_map_size  # 缓存局部地图宽高
        self.local_map_descriptors, self.local_map_keypoints = None, None # 局部地图缓存

        # 局部地图的坐标缓存
        self.local_map_pos = None

        self.rate_limiter_async = RateLimiterAsync(5)

        # 局部匹配用bf(小地图bf匹配速度比flann快), 但是更消耗性能
        self.bf_matcher = cv2.BFMatcher()

        # 全局匹配用flann
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        self.flann_matcher = cv2.FlannBasedMatcher(index_params, search_params)



        self.create_local_map_cache_thread()

        # 当前地图全局匹配时，good match的结果, 用于判断是否要切换地图。如果同时匹配多张地图时，先设置第一个出结果的。
        # 后续才出结果的, 则判断是否比先出的质量好, 是的话则选择质量好的, good match由匹配的时候赋值
        self.good_match_count = 0

    def create_local_map_cache_thread(self):
        self.rate_limiter_async.execute(self.__global_match)

    def pix_axis_to_relative_axis(self, pos):
        """
        原图像素点的坐标转换为相对于指定点位的坐标
        :param pos:
        :return:
        """
        if pos is None:
            return None
        # 以璃月为中心的坐标
        # 初始化坐标原点(这里的初始值为局部地图匹配的x和y) 想要设置什么地方为中心点，则自己跑到该地方，执行get_local_map_from_global_map得到的xywh就是了
        # 或者自己用ps打开该地图，看看xy是多少
        res_x = pos[0] - self.PIX_CENTER_AX
        res_y = pos[1] - self.PIX_CENTER_AY
        return (res_x, res_y)

    def relative_axis_to_pix_axis(self, pos):
        """
        指定点位的坐标转换为原图像素点的坐标
        :param pos:
        :return:
        """
        if pos is None: return None
        return (self.PIX_CENTER_AX + pos[0], self.PIX_CENTER_AY + pos[1])

    def get_user_map_scale(self):
        """
        获取m地图和实际像素比例
        :return:
        """
        if capture.has_paimon():
            self.logger.debug('左上角发现派蒙，表示不在打开的地图界面，获取地图比例失败')
            return None
        screenshot = gs.get_screenshot()
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

        screenshot_resized = cv2.resize(screenshot, None, fx=0.5, fy=0.5)
        kp1, des1 = self.map_256.sift.detectAndCompute(screenshot_resized, None)
        large_img_corners = get_match_corner(screenshot_resized, kp1, des1, self.map_256.kep, self.map_256.des, self.flann_matcher)
        # large_img_corners = get_match_corner(screenshot_resized, kp1, des1, self.map_2048.kep, self.map_2048.des, self.flann_matcher)
        if large_img_corners is None:
            self.logger.debug("无法获取m地图边角点")
            return None

        large_width = np.linalg.norm(large_img_corners[1] - large_img_corners[0])
        large_height = np.linalg.norm(large_img_corners[2] - large_img_corners[1])

        h, w = screenshot.shape[:2]
        #TODO BUG:  divide by zero encountered in divide
        ratio = self.map_2048.block_size / self.map_256.block_size
        scale_y = h / large_height / ratio
        scale_x = w / large_width / ratio
        return (scale_x, scale_y)

    def get_user_map_position(self):
        """
        获取用户按下m键时候此时的地图位置
        :return:
        """
        if capture.has_paimon():
            self.logger.debug('左上角发现派蒙，表示不在打开的地图界面，获取位置失败')
            return None
        screenshot = gs.get_screenshot()
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        screenshot = cv2.resize(screenshot, None, fx=0.5, fy=0.5)
        # cv2.imshow('screenshot', screenshot)
        kp1, des1 = self.map_256.sift.detectAndCompute(screenshot, None)
        pos = get_match_position(screenshot, kp1, des1, self.map_256.kep, self.map_256.des, self.flann_matcher)  # 速度稍慢，但更节省性能, 且只有flann能匹配大图片
        # pos = get_match_position(screenshot, kp1, des1, self.map_256.kep, self.map_256.des, self.bf_matcher)  # 速度快，但更消耗CPU

        if pos is None:
            self.logger.debug("无法获取m地图所在位置")
            return None
        scale = self.map_2048.block_size / self.map_256.block_size
        pos = (pos[0] * scale, pos[1] * scale)
        pos = self.pix_axis_to_relative_axis(pos)
        return pos

    def choose_map(self, map_name):
        self.map_2048 = self.get_sift_map(map_name, 2048)
        try:  # TODO: 待测试：分层地图是否需要256的地图用于传送？
            # if map_name == '渊下宫':
            #     self.map_256 = self.map_2048
            self.map_256 = self.get_sift_map(map_name, 256)
        except Exception as e:
            self.logger.error(e.args)
            self.map_256 = self.map_2048
        self.PIX_CENTER_AX = self.map_2048.center[0]
        self.PIX_CENTER_AY = self.map_2048.center[1]

    def __global_match(self):
        global_match_pos = None
        small_image, keypoints_small, descriptors_small = None, None, None
        global_match_ok = False
        try:
            self.logger.debug('开始进行全局匹配')
            small_image = gs.get_mini_map()
            # keypoints_small, descriptors_small = self.map_2048.detectAndCompute(small_image, None)
            # if keypoints_small is None or descriptors_small is None:
            #     self.logger.error('计算小地图特征点失败, 无法创建全局缓存')

            t0 = time.time()
            # map = self.map_2048
            # TODO: 多线程匹配
            maps_name = MapConfig.get_yaml_object().keys()
            threads = []
            self.good_match_count = 0  # 先清空匹配质量

            # TODO: 执行路线的时候，应当选择指定地图匹配，而非全部遍历。
            def match(map_name):
                sift_map = self.get_sift_map(block_size=2048, map_name=map_name)
                keypoints_small, descriptors_small = sift_map.sift.detectAndCompute(small_image, None)
                self.logger.debug(f'开始尝试匹配{map_name}')
                try:
                    global_match_pos, good_match_count = get_match_position_with_good_match_count(small_image, keypoints_small, descriptors_small, sift_map.kep, sift_map.des,
                                                          self.flann_matcher)
                except MatchException as e:
                    self.logger.debug(f'{map_name}匹配失败:{e.args}')
                    return
                with self.set_good_count_lock:
                    if global_match_pos is not None:
                        if good_match_count > self.good_match_count:
                            self.logger.debug(f'{map_name}匹配成功, good match数量为{good_match_count}，替代旧的匹配结果{self.map_2048.map_name}')
                            # 如何减少错误匹配? 目前是增大good match阈值
                            self.good_match_count = good_match_count
                            self.choose_map(map_name)
                            scale = 2048 / sift_map.block_size
                            global_match_pos = (global_match_pos[0] * scale, global_match_pos[1] * scale)
                            self.global_match_cache(global_match_pos)

            for m in maps_name:
                thread = threading.Thread(target=match, args=(m,))
                threads.append(thread)
                thread.start()

            # for thread in threads:
            #     thread.join()
            start_wait_time = time.time()
            while time.time() - start_wait_time < 10 and self.map_2048 is None:
                time.sleep(0.5)
                self.logger.debug('等待匹配中...')

            match_map: SiftMap = self.map_2048
            if global_match_pos is None:
                self.logger.error('2048全局匹配坐标获取失败，请重试')
                return

            scale = 2048 / match_map.block_size
            self.logger.debug(f'全局匹配用时{time.time()-t0}')
            global_match_pos = (global_match_pos[0] * scale, global_match_pos[1] * scale)
            self.global_match_cache(global_match_pos)


        except Exception as e:
            self.logger.error(e, exc_info=True)

    def filterKeypoints(self, x, y, width, height, keypoints=None, descriptors=None):
        x_center, y_center = x, y
        width, height = width, height
        half_width, half_height = width / 2, height / 2

        # 矩形区域的边界
        x_min, x_max = int(x_center - half_width), int(x_center + half_width)
        y_min, y_max = int(y_center - half_height), int(y_center + half_height)

        filtered_keypoints = []
        filtered_descriptors = []

        for kp, desc in zip(keypoints, descriptors):
            x, y = kp.pt
            if x_min <= x <= x_max and y_min <= y <= y_max:
                filtered_keypoints.append(kp)
                filtered_descriptors.append(desc)

        # 将描述符转换为numpy数组
        filtered_descriptors = np.array(filtered_descriptors)
        return filtered_keypoints, filtered_descriptors

    def global_match_cache(self, pos):
        """
        指定坐标缓存局部区域的特征点
        :param pos:
        :return:
        """
        with self.cache_lock:
            if pos is None:
                self.logger.error('位置为空，创建局部缓存失败!')
                return False
            #  注意传入的pos不要作为最终定位的指标，仅用来筛选出局部匹配区域和判断小地图是否超过局部匹配区域。
            # 理由：1) 因为minimap在该区域内匹配的结果包含了最终坐标，没必要和localmap做二次计算
            #      2) 用户传入的pos可能和全局匹配结果有误差！
            # 获取指定区域的特征点
            self.local_map_keypoints, self.local_map_descriptors = self.filterKeypoints(pos[0], pos[1], self.local_map_size, self.local_map_size, keypoints=self.map_2048.kep, descriptors=self.map_2048.des )
            if self.local_map_descriptors is None:
                self.logger.debug('指定区域内无特征点')
                return False
            self.local_map_pos = pos
            self.logger.info(f'缓存区域成功, 缓存的中心点像素坐标{pos}, 相对坐标{self.pix_axis_to_relative_axis(pos)}')
            return True


    def __local_match(self, small_image, keypoints_small, descriptors_small):
        """
        局部匹配：
        根据缓存的局部地图，获取匹配结果
        1. 小地图特征点与给缓存的局部特征点进行匹配
        2. 没有缓存则先创建缓存
        3. 原本的缓存中包含了像素信息,匹配成功则直接进行相对坐标转换
        4. 匹配失败则判断距离上次匹配时间是否超过一定时长，是则进行全局匹配（避免频繁全局匹配）
        :return:
        """
        # TODO BUG: 有时候会出现剧烈抖动, 将本次请求结果与上次请求结果作比较，如果差距过大则丢弃
        #   或者说不应该丢弃？让调用者自己处理？
        t0 = time.time()

        local_map_descriptors = self.local_map_descriptors
        local_map_keypoints = self.local_map_keypoints
        local_map_pos = self.local_map_pos
        pix_centerx = self.PIX_CENTER_AX
        pix_centery = self.PIX_CENTER_AY
        map_2048 = self.map_2048

        if local_map_keypoints is None or local_map_descriptors is None or map_2048 is None:
            self.logger.debug('当前尚未缓存局部地图的特征点，请稍后再进行局部匹配')
            return None

        # 虽然是局部匹配，但是坐标是算法在大地图匹配生成的，因此返回的坐标是全局坐标
        pix_pos = get_match_position(small_image, keypoints_small, descriptors_small, local_map_keypoints,
                                    local_map_descriptors, self.bf_matcher)
        if pix_pos is None or pix_pos[0] < 0 or pix_pos[1] < 0:
            self.logger.error(f'局部匹配失败, 尝试全局匹配')
            self.create_local_map_cache_thread()
            return None

        # TODO: 优化：在地图边缘可以直接筛选附近的点位作为缓存而不是全局匹配
        # 如果处于地图边缘，则开始创建全局匹配
        # 计算当前位置在局部区域的相对位置
        pix_pos_relative_to_local_map = (pix_pos[0] - local_map_pos[0] + self.local_map_size / 2,
                        pix_pos[1] - local_map_pos[1] + self.local_map_size / 2)
        if self.__position_out_of_local_map_range(pix_pos_relative_to_local_map):
            self.logger.debug(f'{pix_pos}越界了, 局部地图大小为{self.local_map_size}')
            self.create_local_map_cache_thread()
        # else: self.logger.debug(f'小地图在局部地图的匹配位置{pix_pos_relative_to_local_map}')

        pix_pos_relative_to_local_map = (pix_pos[0] - local_map_pos[0] + self.local_map_size / 2, pix_pos[1] - local_map_pos[1] + self.local_map_size / 2)
        # pix_pos_relative_to_global_map = self.pix_axis_to_relative_axis(pix_pos)
        pix_pos_relative_to_global_map = (pix_pos[0] + pix_centerx, pix_pos[1] + pix_centery)
        # self.logger.debug(f'局部匹配成功,结果为{pix_pos},转换坐标后为{pix_pos_relative_to_global_map}, 用时{time.time()-t0}')
        if threading.currentThread().name == 'MainThread' and self.debug_enable and map_2048.img is not None:
            try:
                match_result = crop_img(self.map_2048.img, pix_pos[0], pix_pos[1], capture.mini_map_width * 2).copy()
            except AttributeError as e:
                logging.error("图片裁剪失败")
                return None
            match_result = cv2.cvtColor(match_result, cv2.COLOR_GRAY2BGR)
            color = (0, 255, 0)
            if self.__position_out_of_local_map_range(pix_pos_relative_to_local_map): color = (0,0,255)

            # 小地图在局部地图的相对坐标
            text = f'{pix_pos_relative_to_local_map[0]:<3.1f},{pix_pos_relative_to_local_map[1]:<3.1f}'
            self.__putText(match_result, text, org=(0, 20), color=color)

            # 小地图在整个大地图的绝对坐标
            text = f'{pix_pos[0]:<3.1f},{pix_pos[1]:<3.1f}'
            self.__putText(match_result, text, org=(0, 40), color=color)

            # 小地图在整个大地图的相对坐标（相对于用户自定义中心点坐标)
            text = f'{pix_pos_relative_to_global_map[0]:<3.1f},{pix_pos_relative_to_global_map[1]:<3.1f}'
            self.__putText(match_result, text, org=(0, 60), color=color)
            self.__cvshow('match_result', match_result)

        return pix_pos

    def __position_out_of_local_map_range(self, pos):
        threshold = 150
        max_pos = self.local_map_size - threshold
        return pos[0] < threshold or pos[1] < threshold or pos[0] > max_pos or pos[1] > max_pos


    def get_position(self, absolute_position=False):
        """
        获取相对于中心点的位置,中心点可以在config.yaml中设置
        :param absolute_position: 是否返回绝对位置
        :return:
        """
        small_image = gs.get_mini_map()
        keypoints_small, descriptors_small = self.map_2048.sift.detectAndCompute(small_image, None)
        imgKp1 = cv2.drawKeypoints(small_image, keypoints_small, None, color=(0, 0, 255))
        self.__cvshow('imgKp1', imgKp1)

        if not capture.has_paimon():
            self.logger.error('未找到左上角小地图旁边的派蒙，无法获取位置')
            return None

        if self.local_map_descriptors is None or self.local_map_keypoints is None or len(self.local_map_descriptors) == 0 or len(self.local_map_keypoints) == 0:
            # 非阻塞
            self.create_local_map_cache_thread()
            return None
        result_pos = self.__local_match(small_image, keypoints_small, descriptors_small)

        if absolute_position: return result_pos
        # 坐标变换
        return self.pix_axis_to_relative_axis(result_pos)

    def __putText(self, img, text, org=(0,20), font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.5, color=(0,0,255), thickness=2):
        # 在图像上添加文字
        cv2.putText(img, text, org, font, font_scale, color, thickness)


    def __cvshow(self, name, img):
        if self.debug_enable:
            pass
            # name = f'{name}-{threading.currentThread().name}'
            # cv2.imshow(name, img)
            # cv2.waitKey(2)


    def update(self, width, height):
        return
        # self.PIX_CENTER_AX = 8508
        # self.PIX_CENTER_AY = 2764
        # self.logger.debug(f'坐标中心调整为{self.PIX_CENTER_AX}, {self.PIX_CENTER_AY}')


if __name__ == '__main__':
    # TODO: BUG 同一个位置，不同分辨率获取的位置有差异！
    # 解决思路：
    # 1. 不同分辨率下裁剪的小地图要一致，保持圆形在正中间
    mp = MiniMap(debug_enable=True)
    mp.logger.setLevel(logging.INFO)
    # mp.choose_map('层岩巨渊')
    mp.choose_map('渊下宫')
    capture.add_observer(mp)
    while True:
        time.sleep(0.05)
        t0 = time.time()
        pos = mp.get_position()
        # pos = mp.get_user_map_position()
        # pos = mp.get_user_map_scale()
        print(pos,time.time() - t0)


        # mp.log('相对位置:', pos)
        # if pos is not None:
        #     pix_pos = mp.relative_axis_to_pix_axis(pos)
        #     mp.log('像素位置:', pix_pos)
        #     img = mp.crop_img(mp.map_2048['img'], pix_pos[0], pix_pos[1])
        #     if img is not None:
        #         cv2.imshow('match img', img)
        #         key = cv2.waitKey(1)
        #         if key == ord('q'):
        #             cv2.destroyAllWindows()

