import logging
import time

import cv2
import numpy as np
from capture.genshin_capture import GenShinCapture
from myutils.configutils import get_bigmap_path, get_paimon_icon_path, cfg

gs = GenShinCapture
from mylogger.MyLogger3 import MyLogger
import threading

class MiniMap:
    @staticmethod
    def crop_img(large_image, center_x, center_y, crop_size=500):
        # 假设已经获取到了center_x 和 center_y

        # 1. 计算裁剪区域的左上角坐标
        left = int(center_x - crop_size / 2)
        top = int(center_y - crop_size / 2)

        # 3. 裁剪图片
        # 确保裁剪区域在大图范围内
        cropped_image = large_image[top:top + crop_size, left:left + crop_size]
        if cropped_image.shape[0] < 1 or cropped_image.shape[1] < 1:
            print('Cropped image too small')
            return None

        # 4. 保存裁剪后的图片（可选）
        # cv2.imwrite('cropped_image.jpg', cropped_image)

        # 可选：显示裁剪后的图片
        # cv2.imshow('Cropped Image', cropped_image)
        # key = cv2.waitKey(1)
        # if key == ord('q'):
        #     cv2.destroyAllWindows()
        return cropped_image

    def __init__(self, debug_enable=False):
        """
        :param debug_enable:
        :param gc: GenshinCapture instance
        """
        self.debug_enable = debug_enable
        self.logger = MyLogger(self.__class__.__name__, save_log=True)
        self.sift = cv2.SIFT.create()

        from matchmap.load_save_sift_keypoint import load
        # 地图资源加载
        kp, des = load(2048)  # 特征点加载
        self.map_2048 = {
            'block_size': 2048,
            'img': cv2.imread(get_bigmap_path(2048), cv2.IMREAD_GRAYSCALE),
            'des': des, 'kp': kp
        }

        kp, des = load(600)  # 特征点加载
        self.map_600 = {
            'block_size': 600,
            'img': cv2.imread(get_bigmap_path(600), cv2.IMREAD_GRAYSCALE),
            'des': des, 'kp': kp
        }

        kp, des = load(256)  # 特征点加载
        self.map_256 = {
            'block_size': 256,
            'img': cv2.imread(get_bigmap_path(256), cv2.IMREAD_GRAYSCALE),
            'des': des, 'kp': kp
        }

        paimon_png = cv2.imread(get_paimon_icon_path(), cv2.IMREAD_GRAYSCALE)
        kp, des = self.sift.detectAndCompute(paimon_png, None)  # 判断是否在大世界
        self.map_paimon = {
            'img': paimon_png,
            'des': des,
            'kp': kp
        }

        self.local_map_size = 2048  # 缓存局部地图宽高
        self.local_map, self.local_map_descriptors, self.local_map_keypoints = None, None, None  # 局部地图缓存

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
        self.PIX_CENTER_AX = cfg['center_x']  # 15593.268  # 璃月天衡山右边那个十字圆环
        self.PIX_CENTER_AY = cfg['center_y']  # 13526.913

        self.result_pos = None  # 最终坐标(像素)

    def log(self, *args):
        self.logger.info(args)

    def error(self, *args):
        self.logger.error(args)

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
        return [res_x, res_y]

    def relative_axis_to_pix_axis(self, pos):
        """
        指定点位的坐标转换为原图像素点的坐标
        :param pos:
        :return:
        """
        if pos is None: return None
        return [self.PIX_CENTER_AX + pos[0], self.PIX_CENTER_AY + pos[1]]

    def __match_position(self, small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                         matcher):
        if descriptors_large is None or descriptors_small is None:
            self.error("请传入有效特征点")
            return None

        matches = matcher.knnMatch(descriptors_small, descriptors_large, k=2)

        # 应用比例测试来过滤匹配点
        good_matches = []
        gms = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
                gms.append([m])

        if len(good_matches) < 7:
            self.log("低质量匹配")
            return None

        # 获取匹配点的坐标
        src_pts = np.float32([keypoints_small[m.queryIdx].pt for m in good_matches]).reshape(-1, 2)
        dst_pts = np.float32([keypoints_large[m.trainIdx].pt for m in good_matches]).reshape(-1, 2)

        # 使用RANSAC找到变换矩阵
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
        if M is None:
            self.log("透视变换失败！！")
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
            self.log('左上角发现派蒙，表示不在打开的地图界面，获取位置失败')
            return None
        screenshot = gs.get_screenshot()
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        screenshot = cv2.resize(screenshot, None, fx=0.5, fy=0.5)
        # cv2.imshow('screenshot', screenshot)

        kp1, des1 = self.sift.detectAndCompute(screenshot, None)
        pos = self.__match_position(screenshot, kp1, des1, self.map_256['kp'], self.map_256['des'], self.flann_matcher)

        if pos is None:
            self.log("无法获取m地图所在位置")
            return None
        scale = self.map_2048['block_size'] / self.map_256['block_size']
        pos = (pos[0] * scale, pos[1] * scale)
        pos = self.pix_axis_to_relative_axis(pos)
        return pos

    def __global_match(self):
        if self.global_match_task_running is False:
            return
        try:
            self.log('开始进行全局匹配')
            small_image = gs.get_mini_map(update_screenshot=True)
            keypoints_small, descriptors_small = self.sift.detectAndCompute(small_image, None)
            if keypoints_small is None or descriptors_small is None:
                self.error('计算小地图特征点失败, 无法创建全局缓存')
            t0 = time.time()
            map = self.map_600
            pos = self.__match_position(small_image, keypoints_small, descriptors_small, map['kp'], map['des'], self.flann_matcher)
            if pos is None:
                self.log('600px全局匹配坐标获取失败, 正尝试2048')
                map = self.map_2048
                pos = self.__match_position(small_image, keypoints_small, descriptors_small, map['kp'], map['des'], self.flann_matcher)
                if pos is None:
                    self.log('2048px全局匹配坐标获取失败，请重试')
                    return None

            scale = 2048 / map['block_size']
            self.log('全局匹配用时', time.time() - t0)
            pos = (pos[0] * scale, pos[1] * scale)
            self.global_match_cache(pos)
        except Exception as e:
            self.error(e)
        finally:
            self.global_match_task_running = False

    def global_match_cache(self, pos):
        """
        指定坐标缓存地图
        :param pos:
        :return:
        """
        # 裁剪局部地图
        self.log('正在裁剪局部地图用于缓存...')
        self.local_map = self.crop_img(self.map_2048['img'], pos[0], pos[1], self.local_map_size)
        if self.local_map is None:
            self.log('全局匹配裁剪图片失败，请重试')
            return False
        self.local_map_keypoints, self.local_map_descriptors = self.sift.detectAndCompute(self.local_map, None)
        if self.local_map_descriptors is None:
            self.log('无特征点生成，请检查局部地图')
            self.local_map = None
            return False
        # cv2.namedWindow('local map', cv2.WINDOW_GUI_EXPANDED)
        # cv2.imshow('local map', self.local_map)
        self.local_map_pos = pos
        self.result_pos = pos
        self.log(f'全局匹配成功, 像素坐标{self.result_pos}, 相对坐标{self.pix_axis_to_relative_axis(pos)}')
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
        return len(good_matches) > 7

    def __local_match(self, small_image, keypoints_small, descriptors_small):
        """
        局部匹配：
        根据缓存的局部地图，获取匹配结果
        1. 计算出小地图在局部地图中的坐标位置pos
        2. 根据得到的坐标，局部地图的坐标缓存以及局部地图的宽高，可以得到最终坐标
        :return:
        """
        t0 = time.time()
        if self.global_match_task_running:
            self.log('全局匹配线程尚未结束，请稍后再进行局部匹配')
            return

        pos = self.__match_position(small_image, keypoints_small, descriptors_small, self.local_map_keypoints,
                                    self.local_map_descriptors, self.bf_matcher)
        if pos is None:
            time_cost = time.time() - self.__last_time_global_match
            self.log(f'局部匹配失败, 距离上次进行全局匹配已经过去{time_cost}秒')
            self.result_pos = None
            if time_cost > self.__GLOBAL_MATCH_UPDATE_TIME_INTERVAL:
                self.log('准备创建全局匹配线程')
                self.__create_local_map_cache_thread()
                self.__last_time_global_match = time.time()
                return None
            return

        x = pos[0] + self.local_map_pos[0] - self.local_map_size / 2
        y = pos[1] + self.local_map_pos[1] - self.local_map_size / 2
        self.result_pos = [x, y]
        self.__last_time_global_match = time.time()
        self.log('局部匹配成功', self.result_pos, '用时', time.time() - t0)

    def __create_local_map_cache_thread(self):
        self.log(f'检测是否有全局匹配线程正在执行，检测结果为：{self.global_match_task_running}')
        if not self.global_match_task_running:
            self.global_match_task_running = True
            self.log("正在创建线用于执行全局匹配")
            threading.Thread(target=self.__global_match).start()
            self.log("成功创建线程执行全局匹配")
        else:
            self.log("线程正在执行缓存中，青稍后再获取")
        return None

    def get_position(self):
        gs.update_screenshot()
        small_image = gs.get_mini_map(update_screenshot=False)
        keypoints_small, descriptors_small = self.sift.detectAndCompute(small_image, None)

        if not self.__has_paimon(update_screenshot=False):
            self.log('未找到派蒙，无法获取位置')
            return None

        if self.local_map is None:
            # 非阻塞
            self.__create_local_map_cache_thread()
            return None
            # self.__global_match(small_image, keypoints_small, descriptors_small)
        else:
            self.__local_match(small_image, keypoints_small, descriptors_small)
        # 坐标变换
        return self.pix_axis_to_relative_axis(self.result_pos)


if __name__ == '__main__':
    mp = MiniMap(debug_enable=True)
    while True:
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

