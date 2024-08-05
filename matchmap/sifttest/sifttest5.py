import logging
import os.path
import time
import cv2
import numpy as np
from capture.genshin_capture import GenShinCapture
from myutils.configutils import get_bigmap_path, get_paimon_icon_path, cfg
from myutils.timerutils import Timer
from myutils.imgutils import crop_img

gs = GenShinCapture
from mylogger.MyLogger3 import MyLogger
import threading

class MiniMap:
    def __init__(self, debug_enable=False):
        """
        :param debug_enable:
        :param gc: GenshinCapture instance
        """
        self.debug_enable = debug_enable
        self.logger = MyLogger(__class__.__name__, save_log=True)
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

        paimon_png = cv2.imread(get_paimon_icon_path(), cv2.IMREAD_GRAYSCALE)
        kp, des = self.sift.detectAndCompute(paimon_png, None)  # 判断是否在大世界
        self.map_paimon = { 'img': paimon_png, 'des': des, 'kp': kp }
        self.logger.info(f'地图和特征点加载完成，用时{time.time() - t0}')

        self.__paimon_appear_delay = 0.2  # 派蒙出现后，多少秒才可以进行匹配
        # 如果要求首次不进行计时器检查，则需要设置一个0的计时器
        self.__paimon_appear_delay_timer = Timer(0)  # 派蒙延迟计时器
        self.__paimon_appear_delay_timer.start()

        self.local_map_size = 500 # 缓存局部地图宽高
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
        self.PIX_CENTER_AX = None  # cfg['center_x']  # 15593.268  # 璃月天衡山右边那个十字圆环
        self.PIX_CENTER_AY = None  # cfg['center_y']  # 13526.913
        self.update(GenShinCapture.width, GenShinCapture.height)

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
        if self.__has_paimon():
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
        # 获取指定区域的特征点
        self.local_map_keypoints, self.local_map_descriptors = self.filterKeypoints(pos[0], pos[1], self.local_map_size, self.local_map_size, keypoints=self.map_2048['kp'], descriptors=self.map_2048['des'] )
        if self.local_map_descriptors is None:
            self.logger.debug('指定区域内无特征点')
            return False
        self.local_map_pos = pos
        self.logger.debug(f'全局匹配成功, 像素坐标{pos}, 相对坐标{self.pix_axis_to_relative_axis(pos)}')
        return True

    def __has_paimon(self, update_screenshot=True):
        """
        判断小地图左上角区域是否有小派蒙图标,如果没有说明不在大世界界面（可能切地图或者菜单界面了)
        :return:
        """
        # 将图像转换为灰度
        img = gs.get_paimon_ariea(update_screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

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
            return self.__paimon_appear_delay_timer.check()
        else:
            self.__paimon_appear_delay_timer = None
        return False


    def __local_match(self, small_image, keypoints_small, descriptors_small):
        """
        局部匹配：
        根据缓存的局部地图，获取匹配结果
        1. 计算出小地图在局部地图中的坐标位置pos
        2. 根据得到的坐标，局部地图的坐标缓存以及局部地图的宽高，可以得到最终坐标
        :return:
        """
        # TODO BUG: 有时候会出现剧烈抖动, 将本次请求结果与上次请求结果作比较，如果差距过大则丢弃
        t0 = time.time()
        if self.local_map_descriptors is None or self.local_map_keypoints is None:
            self.logger.debug('当前尚未缓存局部地图的特征点，请稍后再进行局部匹配')
            return None

        # 虽然是局部匹配，但是坐标是全局匹配生成的，因此返回的坐标是全局坐标
        pix_pos = self.__match_position(small_image, keypoints_small, descriptors_small, self.local_map_keypoints,
                                    self.local_map_descriptors, self.bf_matcher)
        if pix_pos is None:
            # cv2.imwrite('bad.jpg', small_image)
            # pai = GenShinCapture.get_paimon_ariea(update_screenshot=False)
            # cv2.imwrite('pai.jpg', pai)
            time_cost = time.time() - self.__last_time_global_match
            self.logger.error(f'局部匹配失败, 距离上次进行全局匹配已经过去{time_cost}秒')
            if time_cost > self.__GLOBAL_MATCH_UPDATE_TIME_INTERVAL:
                self.logger.debug('准备创建全局匹配线程')
                self.create_local_map_cache_thread()
                self.__last_time_global_match = time.time()
                return None
            return None

        # 如果处于地图边缘，则开始创建全局匹配
        # 计算当前位置在局部区域的相对位置
        pix_pos_relative_to_local_map = (pix_pos[0] - self.local_map_pos[0] + self.local_map_size / 2,
                        pix_pos[1] - self.local_map_pos[1] + self.local_map_size / 2)
        if self.__position_out_of_local_map_range(pix_pos_relative_to_local_map):
            self.logger.debug(f'{pix_pos}越界了, 局部地图大小为{self.local_map_size}')
            self.create_local_map_cache_thread()
        else:
            self.logger.debug(f'小地图在局部地图的匹配位置{pix_pos_relative_to_local_map}')

        pix_pos_relative_to_local_map = (pix_pos[0] - self.local_map_pos[0] + self.local_map_size / 2, pix_pos[1] - self.local_map_pos[1] + self.local_map_size / 2)
        pix_pos_relative_to_global_map = self.pix_axis_to_relative_axis(pix_pos)
        self.logger.debug(f'局部匹配成功,结果为{pix_pos},转换坐标后为{pix_pos_relative_to_global_map}, 用时{time.time()-t0}')
        if threading.currentThread().name == 'MainThread' and self.debug_enable and self.map_2048['img'] is not None:
            match_result = crop_img(self.map_2048['img'], pix_pos[0], pix_pos[1], GenShinCapture.mini_map_width * 2).copy()
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
            self.logger.debug("正在创建线用于执行全局匹配")
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
        gs.update_screenshot()
        small_image = gs.get_mini_map(update_screenshot=False)
        keypoints_small, descriptors_small = self.sift.detectAndCompute(small_image, None)

        if not self.__has_paimon(update_screenshot=False):
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
    from myutils.configutils import cfg
    dn = cfg.get('debug_enable', False)
    if dn == 1:
        mp = MiniMap(debug_enable=True)
    else:
        mp = MiniMap(debug_enable=False)
    mp.logger.setLevel(logging.INFO)
    GenShinCapture.add_observer(mp)
    while True:
        time.sleep(0.05)
        t0 = time.time()
        pos = mp.get_position()
    #     pos = mp.get_user_map_position()
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

