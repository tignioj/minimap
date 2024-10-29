import time

import cv2
from capture.capture_factory import capture
from matchmap.gia_rotation import RotationGIA
from matchmap.sifttest.sifttest6 import MiniMap
from mylogger.MyLogger3 import MyLogger

minimap = MiniMap()
from myutils.imgutils import crop_img
logger = MyLogger('minimap_service')
rotate = RotationGIA(False)
capture.add_observer(rotate)
capture.add_observer(minimap)

class MinimapService:
    @classmethod
    def get_user_map_position(cls):
        return minimap.get_user_map_position()

    @classmethod
    def get_user_map_scale(cls):
        return minimap.get_user_map_scale()


    @classmethod
    def create_cached_local_map(cls, center=None, use_middle_map=False)->bool:
        result = False
        if center:
            # 用户传过来的是相对位置，要转换成绝对位置
            pix_pos = minimap.relative_axis_to_pix_axis(center)
            result = minimap.global_match_cache(pix_pos)
        elif use_middle_map:
            # 现在传送移动地图不是移动到中心点，传送的时候禁止用此方法创建缓存
            pos = minimap.get_user_map_position()
            if pos:
                pos = minimap.relative_axis_to_pix_axis(pos)
                result = minimap.global_match_cache(pos)
        else:
            result = minimap.create_local_map_cache_thread()
        return result

    @classmethod
    def get_position(cls, absolute_position=False):
        return minimap.get_position(absolute_position=absolute_position)

    @classmethod
    def get_position_and_rotation(cls, absolute_position=False):
        return minimap.get_position_and_rotation(absolute_position=absolute_position)

    @classmethod
    def get_insert_node(cls, absolute_position=False):
        pos, rot = minimap.get_position_and_rotation(absolute_position=absolute_position)
        if pos is None or minimap.map_2048 is None:
            return None

        from myexecutor.BasePathExecutor2 import Point
        if capture.is_flying():
            move_mode = Point.MOVE_MODE_FLY
        elif capture.is_swimming():
            move_mode = Point.MOVE_MODE_SWIM
        else:
            move_mode = Point.MOVE_MODE_NORMAL
        map_name = minimap.map_2048.map_name

        data = {
            'position': pos,
            'move_mode': move_mode,
            'rotation': rot,
            'map_name': map_name
        }

        return data

    @classmethod
    def get_rotation(cls, use_alpha=True, confidence=0.6):
        """
        获取角度
        :param use_alpha: 是否只使用alpha计算角度（不要在秘境开启alpha，不同电脑不一样）
        :param confidence: GIA计算角度结果的置信度
        :return:
        """
        img = capture.get_mini_map(use_alpha=True)

        if use_alpha:
            b,g,r,a = cv2.split(img)
            inv_a = cv2.bitwise_not(a)
            result = rotate.predict_rotation(inv_a, confidence)
        else:
            result = rotate.predict_rotation(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), confidence)
        if result is None:
            result = minimap.get_rotation()
            logger.debug(f'采取减背景法计算转向:结果为:{result}')

        return result

    @classmethod
    def choose_map(cls, map_name):
        minimap.choose_map(map_name=map_name)


    @classmethod
    def get_region_map(cls, x,y,width, scale,country):
        # from myutils.load_save_sift_keypoint import get_sift_map, SiftMap, cn_text_map

        # if cn_text_map.get(country) is None:
        #     return ServerBaseController.error(f'{country}区域信息无法识别'), 400

        sift_map = MiniMap.get_sift_map(block_size=2048, map_name=country)
        try:
            x = int(float(x))
            y = int(float(y))
            width = int(width)
            if scale: scale = float(scale)
            else: scale = 1
        except ValueError as e:
            logger.error(e)
            return

        pix_pos = (sift_map.center[0] + x, sift_map.center[1] + y)
        tem_local_map = crop_img(sift_map.img, pix_pos[0], pix_pos[1], crop_size=width, scale=scale)
        if tem_local_map is None:
            raise Exception('无法裁剪地图')
        return tem_local_map

if __name__ == '__main__':
    while True:
        t = time.time()
        rot = MinimapService.get_rotation()
        print(rot, time.time() - t)