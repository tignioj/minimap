import logging
import os
import time
from server import ServerAPI
from myutils.configutils import cfg, resource_path
from myutils.imgutils import crop_img
class MiniMapInter:
    def get_position(self): pass
    def get_local_map(self): pass
    def get_region_map(self,x, y, width): pass
    def get_rotation(self,use_alpha=False): pass
    def get_user_map_position(self): pass
    def create_cached_local_map(self,xy=None,use_middle_map=False): pass

    def get_ocr_result(self): pass
class MinimapServer(MiniMapInter):

    def get_position(self):
        """
        获取当前小地图的位置
        :return:
        """
        return ServerAPI.position()

    def get_region_map(self, x, y, width):
        return ServerAPI.get_region_map(x, y, width)

    def get_rotation(self, use_alpha=False):
        return ServerAPI.rotation(use_alpha=use_alpha)

    def get_user_map_position(self): return ServerAPI.user_map_position()
    def get_user_map_scale(self): return ServerAPI.user_map_scale()

    def create_cached_local_map(self, center=None,use_middle_map=False): return ServerAPI.create_cached_local_map(center_pos=center, use_middle_map=use_middle_map)

    def get_ocr_result(self):
        return ServerAPI.get_ocr_result()


import cv2
from capture.capture_factory import capture
class MinimapNative(MiniMapInter):
    def __init__(self):
        from matchmap.sifttest.sifttest5 import MiniMap
        from matchmap.gia_rotation import RotationGIA
        self.minimap = MiniMap()
        self.rotation = RotationGIA()
        self.large_map = self.minimap.map_2048['img']
        self.gc = capture
        capture.add_observer(self.minimap)
        capture.add_observer(self.rotation)
        from paddleocr import PaddleOCR
        your_det_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_det_infer')
        your_rec_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_rec_infer')
        # your_rec_char_dict_path=None
        your_cls_model_dir = os.path.join(resource_path, 'ocr', 'ch_ppocr_mobile_v2.0_cls_infer')
        self.ocr = PaddleOCR(det_model_dir=f'{your_det_model_dir}', lang="ch", rec_model_dir=f'{your_rec_model_dir}',
                        cls_model_dir=f'{your_cls_model_dir}',
                        use_angle_cls=False, use_gpu=False, show_log=False)
        # self.ocr = PaddleOCR(use_angle_cls=False, lang="ch", use_gpu=False, show_log=False)


    def get_position(self):
        """
        获取当前小地图的位置
        :return:
        """
        return self.minimap.get_position()

    def get_local_map(self):
        local_map_pos = self.minimap.local_map_pos
        if local_map_pos is None:
            return None

        pix_pos = self.minimap.local_map_pos
        width = self.minimap.local_map_size
        tem_local_map = crop_img(self.large_map, pix_pos[0], pix_pos[1], width)
        return tem_local_map

    def get_region_map(self, x, y, width):
        if x is not None and y is not None and width is not None:
            width = int(float(width))
            x = int(float(x))
            y = int(float(y))

            pix_pos = self.minimap.relative_axis_to_pix_axis((x, y))

            if self.large_map is None:
                from myutils.configutils import get_bigmap_path
                self.large_map = cv2.imread(get_bigmap_path(2048), cv2.IMREAD_GRAYSCALE)
                if self.large_map is None:
                    raise Exception("无法加载大地图")

            # tem_local_map = crop_img(app.large_map, pix_pos[0], pix_pos[1], crop_size=width, scale=scale)
            tem_local_map = crop_img(self.large_map, pix_pos[0], pix_pos[1], crop_size=width)
            if tem_local_map is None:
                raise Exception("无法裁剪大地图")
            return tem_local_map

    def get_rotation(self, use_alpha=False):
        img = self.gc.get_mini_map()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return self.rotation.predict_rotation(img)

    def get_user_map_position(self):
        return self.minimap.get_user_map_position()

    def get_user_map_scale(self): return self.minimap.get_user_map_scale()
    def create_cached_local_map(self,center=None,use_middle_map=False):
        result = False
        if center:
            # 用户传过来的是相对位置，要转换成绝对位置
            pix_pos = self.minimap.relative_axis_to_pix_axis(center)
            result = self.minimap.global_match_cache(pix_pos)
        elif use_middle_map:
            # 现在传送移动地图不是移动到中心点，传送的时候禁止用此方法创建缓存
            pos = self.minimap.get_user_map_position()
            if pos:
                pos = self.minimap.relative_axis_to_pix_axis(pos)
                result = self.minimap.global_match_cache(pos)
        else:
            result = self.minimap.create_local_map_cache_thread()

        return result
    def get_ocr_result(self):
        return self.ocr.ocr(capture.get_screenshot(), cls=False)

if cfg.get('enable_serve_less_mode', 0):
    MinimapInterface = MinimapNative()
else:
    MinimapInterface = MinimapServer()

if __name__ == '__main__':
    mp = MinimapInterface
    while True:
        start = time.time()
        # pos = mp.get_position()
        mpos = mp.get_user_map_position()
        # rotation = mp.get_rotation(use_alpha=False)
        # print(pos, rotation)
        print(mpos,"cost time:", time.time() - start)
