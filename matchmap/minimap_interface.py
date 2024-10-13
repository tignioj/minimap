import logging
import os
import time
from server import ServerAPI
from myutils.configutils import resource_path
from myutils.imgutils import crop_img
class MiniMapInter:

    # 获取当前选择的地图
    def get_chosen_country(self)->str: pass
    def choose_map(self, map_name): pass

    def get_position(self): pass

    def get_position_and_rotation(self): pass

    def get_user_map_scale(self): pass

    def get_local_map(self): pass
    def get_region_map(self,x, y, width): pass
    def get_rotation(self,use_alpha=False): pass
    def get_user_map_position(self): pass
    def create_cached_local_map(self,xy=None,use_middle_map=False): pass

    def get_ocr_result(self): pass
    def get_ocr_fight_team(self): pass


class MinimapServer(MiniMapInter):

    def get_position(self):
        """
        获取当前小地图的位置
        :return:
        """
        return ServerAPI.position()

    def get_position_and_rotation(self):
        return ServerAPI.get_position_and_rotation()

    def get_region_map(self, x, y, width, region=None):
        return ServerAPI.get_region_map(x, y, width, region=region)

    def get_insert_node(self):
        return ServerAPI.get_insert_node()
    def choose_map(self, map_name):
        return ServerAPI.choose_map(map_name)

    def get_rotation(self, use_alpha=False):
        return ServerAPI.rotation(use_alpha=use_alpha)

    def get_user_map_position(self): return ServerAPI.user_map_position()
    def get_user_map_scale(self): return ServerAPI.user_map_scale()

    def create_cached_local_map(self, center=None,use_middle_map=False): return ServerAPI.create_cached_local_map(center_pos=center, use_middle_map=use_middle_map)

    def get_ocr_result(self, mss_mode=False):
        return ServerAPI.get_ocr_result(mss_mode=mss_mode)

    def get_ocr_fight_team(self):
        return ServerAPI.get_ocr_fight_team()


MinimapInterface = MinimapServer()

if __name__ == '__main__':
    mp = MinimapInterface
    while True:
        start = time.time()
        # pos = mp.get_position()
        # mpos = mp.get_user_map_position()
        # rotation = mp.get_rotation(use_alpha=False)
        # print(pos, rotation)
        # print(mpos,"cost time:", time.time() - start)
        mp.get_ocr_result()
        print(time.time() - start)

