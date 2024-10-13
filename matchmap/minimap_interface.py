import logging
import os
import time
class MiniMapInter:

    # 获取当前选择的地图
    def get_chosen_country(self)->str: pass
    def choose_map(self, map_name): pass

    def get_position(self): pass

    def get_position_and_rotation(self): pass

    def get_user_map_scale(self): pass

    def get_insert_node(self, absolute_position): pass

    def get_local_map(self): pass
    def get_region_map(self,x, y, width): pass
    def get_rotation(self,use_alpha=False): pass
    def get_user_map_position(self): pass
    def create_cached_local_map(self,xy=None,use_middle_map=False): pass

    def get_ocr_result(self): pass
    def get_ocr_fight_team(self): pass


from server.service.MinimapService import MinimapService
from server.service.OCRService import OCRService
class MinimapNative(MiniMapInter):

    def get_position(self):
        """
        获取当前小地图的位置
        :return:
        """
        return MinimapService.get_position()

    def get_position_and_rotation(self):
        return MinimapService.get_position_and_rotation()

    def get_region_map(self, x, y, width,region=None):
        return MinimapService.get_region_map(x, y, width, scale=1, country=region)

    def get_insert_node(self, absolute_position):
        return MinimapService.get_insert_node(absolute_position=absolute_position)

    def choose_map(self, map_name):
        return MinimapService.choose_map(map_name)

    def get_rotation(self, use_alpha=False):
        return MinimapService.get_rotation()

    def get_user_map_position(self): return MinimapService.get_user_map_position()
    def get_user_map_scale(self): return MinimapService.get_user_map_scale()

    def create_cached_local_map(self, center=None,use_middle_map=False):
        return MinimapService.create_cached_local_map(center=center, use_middle_map=use_middle_map)

    def get_ocr_result(self, mss_mode=False):
        if mss_mode:
            return OCRService.ocr_result_mss()
        else:
            return OCRService.ocr_result()

    def get_ocr_fight_team(self):
        return OCRService.ocr_fight_team()


MinimapInterface = MinimapNative()

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

