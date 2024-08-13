import logging
import os.path
import time
import cv2
import numpy as np
from capture.capture_factory import capture
from myutils.configutils import get_bigmap_path, cfg
from myutils.timerutils import Timer
from myutils.imgutils import crop_img
gs = capture
from mylogger.MyLogger3 import MyLogger
import threading

class MiniMap:
    def __init__(self, debug_enable=None):
        """
        :param debug_enable:
        :param gc: GenshinCapture instance
        """
        self.logger = MyLogger(__class__.__name__, logging.DEBUG, save_log=True)
        if debug_enable is None:
            debug_enable = cfg.get('debug_enable', False)
            if debug_enable: self.logger = MyLogger(__class__.__name__,level=logging.DEBUG, save_log=True)

        self.debug_enable = debug_enable
        self.sift = cv2.SIFT.create()

        # from matchmap.load_save_sift_keypoint import load
        from myutils.kp_gen import load
        t0 = time.time()
        # 地图资源加载
        bs = 2048
        self.logger.info(f'正在加载{bs}特征点')
        kp, des = load(bs)  # 特征点加载
        self.map_2048 = {
            'img': None,
            'block_size': bs, 'des': des, 'kp': kp}

        if self.debug_enable:
            tt = time.time()
            self.logger.info('开启了debug模式，正在加载大地图用于展示匹配结果, 请稍等')
            p = get_bigmap_path(self.map_2048['block_size'])
            if not os.path.exists(p):
                self.logger.error(f'您指定的路径{p}有误,请检查大地图路径')
            else:
                self.map_2048['img'] = cv2.imread(get_bigmap_path(self.map_2048['block_size']), cv2.IMREAD_GRAYSCALE)
                self.logger.info(f'地图加载完成，用时{time.time() - tt}')

        bs = 256
        self.logger.info(f'正在加载{bs}特征点')
        kp, des = load(bs)  # 特征点加载
        self.map_256 = {'block_size': bs, 'des': des, 'kp': kp }


        local_map_size = cfg.get('local_map_size', 1024)
        if local_map_size < 512: local_map_size = 512
        if local_map_size > 10240: local_map_size = 10240
        self.logger.info(f'搜索范围设置为{local_map_size}')
        self.local_map_size = local_map_size  # 缓存局部地图宽高
        self.local_map_descriptors, self.local_map_keypoints = None, None # 局部地图缓存

        # 局部地图的坐标缓存
        self.local_map_pos = None

        # 多线程缓存局部地图标志
        self.global_match_task_running = False

        # 匹配器
        self.bf_matcher = cv2.BFMatcher()
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        self.flann_matcher = cv2.FlannBasedMatcher(index_params, search_params)

        self.__last_time_global_match = 0  # 上次进行全局匹配时间
        self.__GLOBAL_MATCH_UPDATE_TIME_INTERVAL = 5  # 上次匹配时间间隔

        # 确定中心点
        self.PIX_CENTER_AX = cfg.get('center_x', 15593.298)  # 璃月天衡山右边那个十字圆环
        self.PIX_CENTER_AY = cfg.get('center_y',13528.16)
        self.update(capture.width, capture.height)

        # self.result_pos = None  # 最终坐标(像素)

        # 记录全局匹配得到的坐标与局部匹配得到的坐标产生误差
        self.local_match_global_match_diff_x = 0
        self.local_match_global_match_diff_y = 0
        self.create_local_map_cache_thread()

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

    def __match_position(self, small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                         matcher):
        if small_image is None or keypoints_small is None or descriptors_large is None or descriptors_small is None or len(keypoints_large) == 0 or len(descriptors_large) == 0:
            self.logger.error("请传入有效特征点")
            return None

        try:
            matches = matcher.knnMatch(descriptors_small, descriptors_large, k=2)
        except Exception as e:
            msg = f'进行匹配的时候出错了，报错信息{e}'
            self.logger.error(msg)
            raise e

        # 应用比例测试来过滤匹配点
        good_matches = []
        gms = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
                gms.append([m])

        if len(good_matches) < 7:
            self.logger.debug("低质量匹配")
            return None

        # 获取匹配点的坐标
        src_pts = np.float32([keypoints_small[m.queryIdx].pt for m in good_matches]).reshape(-1, 2)
        dst_pts = np.float32([keypoints_large[m.trainIdx].pt for m in good_matches]).reshape(-1, 2)

        # 使用RANSAC找到变换矩阵
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
        if M is None:
            self.logger.debug("透视变换失败！！")
            return None

        # 计算小地图的中心点
        h, w = small_image.shape[:2]
        center_point = np.array([[w / 2, h / 2]], dtype='float32')
        center_point = np.array([center_point])
        transformed_center = cv2.perspectiveTransform(center_point, M)
        # 打印小地图在大地图中的中心坐标
        # print("Center of the small map in the large map: ", transformed_center)
        return transformed_center[0][0]

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

        kp1, des1 = self.sift.detectAndCompute(screenshot, None)
        pos = self.__match_position(screenshot, kp1, des1, self.map_256['kp'], self.map_256['des'], self.flann_matcher)

        if pos is None:
            self.logger.debug("无法获取m地图所在位置")
            return None
        scale = self.map_2048['block_size'] / self.map_256['block_size']
        pos = (pos[0] * scale, pos[1] * scale)
        pos = self.pix_axis_to_relative_axis(pos)
        return pos

    def __global_match(self):
        global_match_pos = None
        small_image, keypoints_small, descriptors_small = None, None, None
        global_match_ok = False
        if self.global_match_task_running is False:
            return
        try:
            self.logger.debug('开始进行全局匹配')
            small_image = gs.get_mini_map(update_screenshot=True)
            keypoints_small, descriptors_small = self.sift.detectAndCompute(small_image, None)
            if keypoints_small is None or descriptors_small is None: self.logger.error('计算小地图特征点失败, 无法创建全局缓存')

            t0 = time.time()
            map = self.map_2048
            global_match_pos = self.__match_position(small_image, keypoints_small, descriptors_small, map['kp'], map['des'], self.flann_matcher)
            if global_match_pos is None:
                self.logger.error('2048全局匹配坐标获取失败，请重试')
                return

            scale = 2048 / map['block_size']
            self.logger.debug(f'全局匹配用时{time.time()-t0}')
            global_match_pos = (global_match_pos[0] * scale, global_match_pos[1] * scale)
            global_match_ok = self.global_match_cache(global_match_pos)
        except Exception as e:
            self.logger.error(e)
        finally:
            self.global_match_task_running = False

        if global_match_ok:
            self.logger.debug('进行一次局部匹配消除全局匹配差异')
            pos_local = self.__local_match(small_image, keypoints_small, descriptors_small)
            if pos_local is not None:
                before_pos = self.get_position()
                self.logger.debug(f'消除差异前，得到的相对坐标为{before_pos}')
                self.local_match_global_match_diff_x = global_match_pos[0] - pos_local[0]
                self.local_match_global_match_diff_y = global_match_pos[1] - pos_local[1]
                self.logger.debug(f'当前位置全局匹配得到的坐标是{global_match_pos}, 局部匹配得到的坐标是{pos_local}, 记录误差为({self.local_match_global_match_diff_x},{self.local_match_global_match_diff_y})')
                self.logger.debug(f'消除差异后，得到的相对坐标为{self.get_position()}')
        else:
            self.logger.error('全局匹配失败!无需消除局部匹配差异')
            self.local_match_global_match_diff_x = 0
            self.local_match_global_match_diff_y = 0

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
        if pos is None:
            self.logger.error('位置为空，创建局部缓存失败!')
            return False
        #  注意传入的pos不要作为最终定位的指标，仅用来筛选出局部匹配区域和判断小地图是否超过局部匹配区域。
        # 理由：1) 因为minimap在该区域内匹配的结果包含了最终坐标，没必要和localmap做二次计算
        #      2) 用户传入的pos可能和全局匹配结果有误差！
        # 获取指定区域的特征点
        self.local_map_keypoints, self.local_map_descriptors = self.filterKeypoints(pos[0], pos[1], self.local_map_size, self.local_map_size, keypoints=self.map_2048['kp'], descriptors=self.map_2048['des'] )
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
        t0 = time.time()
        if self.local_map_descriptors is None or self.local_map_keypoints is None:
            self.logger.debug('当前尚未缓存局部地图的特征点，请稍后再进行局部匹配')
            return None

        # 虽然是局部匹配，但是坐标是算法在大地图匹配生成的，因此返回的坐标是全局坐标
        pix_pos = self.__match_position(small_image, keypoints_small, descriptors_small, self.local_map_keypoints,
                                    self.local_map_descriptors, self.bf_matcher)
        if pix_pos is None:
            time_cost = time.time() - self.__last_time_global_match
            self.logger.error(f'局部匹配失败, 距离上次进行全局匹配已经过去{time_cost}秒')
            if time_cost > self.__GLOBAL_MATCH_UPDATE_TIME_INTERVAL:
                self.logger.debug('准备创建全局匹配线程')
                self.create_local_map_cache_thread()
                self.__last_time_global_match = time.time()
                return None
            return None

        # TODO: 优化：在地图边缘可以直接筛选附近的点位作为缓存而不是全局匹配
        # 如果处于地图边缘，则开始创建全局匹配
        # 计算当前位置在局部区域的相对位置
        pix_pos_relative_to_local_map = (pix_pos[0] - self.local_map_pos[0] + self.local_map_size / 2,
                        pix_pos[1] - self.local_map_pos[1] + self.local_map_size / 2)
        if self.__position_out_of_local_map_range(pix_pos_relative_to_local_map):
            self.logger.debug(f'{pix_pos}越界了, 局部地图大小为{self.local_map_size}')
            self.create_local_map_cache_thread()
        else:
            pass
            # self.logger.debug(f'小地图在局部地图的匹配位置{pix_pos_relative_to_local_map}')

        pix_pos_relative_to_local_map = (pix_pos[0] - self.local_map_pos[0] + self.local_map_size / 2, pix_pos[1] - self.local_map_pos[1] + self.local_map_size / 2)
        pix_pos_relative_to_global_map = self.pix_axis_to_relative_axis(pix_pos)
        # self.logger.debug(f'局部匹配成功,结果为{pix_pos},转换坐标后为{pix_pos_relative_to_global_map}, 用时{time.time()-t0}')
        if threading.currentThread().name == 'MainThread' and self.debug_enable and self.map_2048['img'] is not None:
            match_result = crop_img(self.map_2048['img'], pix_pos[0], pix_pos[1], capture.mini_map_width * 2).copy()
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

    def create_local_map_cache_thread(self):
        self.logger.debug(f'检测是否有全局匹配线程正在执行，检测结果为：{self.global_match_task_running}')
        if not self.global_match_task_running:
            self.global_match_task_running = True
            self.logger.info("正在创建线用于执行全局匹配, 请稍后...")
            threading.Thread(target=self.__global_match).start()
            self.logger.debug("成功创建线程执行全局匹配")
            return True
        else:
            self.logger.debug("线程正在执行缓存中，请稍后再获取")
            return False
    def __position_out_of_local_map_range(self, pos):
        threshold = 50
        max_pos = self.local_map_size - threshold
        return pos[0] < threshold or pos[1] < threshold or pos[0] > max_pos or pos[1] > max_pos


    def get_position(self, absolute_position=False):
        """
        获取相对于中心点的位置,中心点可以在config.yaml中设置
        :param absolute_position: 是否返回绝对位置
        :return:
        """
        small_image = gs.get_mini_map()
        keypoints_small, descriptors_small = self.sift.detectAndCompute(small_image, None)

        if not capture.has_paimon():
            self.logger.debug('未找到派蒙，无法获取位置')
            return None

        if self.local_map_descriptors is None or self.local_map_keypoints is None or len(self.local_map_descriptors) == 0 or len(self.local_map_keypoints) == 0:
            # 非阻塞
            self.create_local_map_cache_thread()
            return None
        result_pos = self.__local_match(small_image, keypoints_small, descriptors_small)

        # 消除局部匹配与全局匹配产生的误差
        if result_pos is not None:
            result_pos = (result_pos[0] + self.local_match_global_match_diff_x, result_pos[1] + self.local_match_global_match_diff_y)

        if absolute_position: return result_pos
        # 坐标变换
        return self.pix_axis_to_relative_axis(result_pos)

    def __putText(self, img, text, org=(0,20), font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.5, color=(0,0,255), thickness=2):
        # 在图像上添加文字
        cv2.putText(img, text, org, font, font_scale, color, thickness)


    def __cvshow(self, name, img):
        if self.debug_enable:
            cv2.imshow(name, img)
            cv2.waitKey(10)


    def update(self, width, height):
        offset_x, offset_y = 0, 0
        if width == 1280:
            offset_x, offset_y = 0, 0
            # cfgg = cfg['r_1280x720']
        elif width == 1600:
            offset_x, offset_y = 0, 0
            # cfgg = cfg['r_1600x900']
        elif width == 1920:
            # offset_x, offset_y = 0.9364013671875, 3.619384765625
            offset_x, offset_y = 0, 0
            # offset_x, offset_y = 0.9, 3.4
            # cfgg = cfg['r_1920x1080']
        elif width == 2560:
            offset_x, offset_y = 0, 0
            # cfgg = cfg['r_2560x1440']
        else:
            self.logger.debug(f'不受支持的分辨率{width}x{height}')
            return

        self.PIX_CENTER_AX = cfg['center_x'] + offset_x
        self.PIX_CENTER_AY = cfg['center_y'] + offset_y
        self.logger.debug(f'坐标中心调整为{self.PIX_CENTER_AX}, {self.PIX_CENTER_AY}')


if __name__ == '__main__':
    # TODO: BUG 同一个位置，不同分辨率获取的位置有差异！
    # 解决思路：
    # 1. 不同分辨率下裁剪的小地图要一致，保持圆形在正中间
    from myutils.configutils import cfg
    mp = MiniMap()
    mp.logger.setLevel(logging.INFO)
    capture.add_observer(mp)
    while True:
        time.sleep(0.05)
        t0 = time.time()
        pos = mp.get_position()
        # pos = mp.get_user_map_position()
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

