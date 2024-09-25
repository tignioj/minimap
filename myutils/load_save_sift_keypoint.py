import sys
from typing import List

import cv2
import pickle
import os

import numpy

from myutils.configutils import resource_path

# class SiftMap:
#     def __init__(self, map_name, block_size,img, des, kep, center):
#         self.map_name = map_name
#         self.block_size = block_size
#         self.img = img
#         self.des:numpy.ndarray = des
#         self.kep: List[cv2.KeyPoint] = kep
#         self.center = center
#
__map_dict = {}

def get_bigmap_path(block_size=2048,map_name='daoqi'):
    # return os.path.join(resource_path, 'map', 'segments', map_file_name)
    return os.path.join(resource_path, 'map', 'segments', f'{map_name}_{block_size}.png')

def get_keypoints_des_path(block_size,map_name):
    kp = os.path.join(resource_path, 'features', 'sift', f'segments', f'sift_keypoints_{block_size}_{map_name}.pkl')
    des = os.path.join(resource_path, 'features', 'sift', f'segments', f'sift_descriptors_{block_size}_{map_name}.pkl')
    return kp, des


# def get_sift_map(map_name,block_size) -> SiftMap:
#     global __map_dict
#     map_pinyin = cn_text_map.get(map_name)
#     key = f'{map_pinyin}_{block_size}'
#     map_obj = __map_dict.get(key)
#     if map_obj is None:
#         print(f"加载{map_name}图片中...........")
#         map_path = get_bigmap_path(block_size, map_name=map_pinyin)
#         center = get_config('map_config').get(map_pinyin).get('center')
#         img = cv2.imread(map_path, cv2.IMREAD_GRAYSCALE)
#         # cv2.imshow(map_pinyin, cv2.resize(img, None, fx=0.1,fy=0.1))
#         # cv2.waitKey(0)
#
#         kep, des = load(block_size=block_size, map_name=map_pinyin)
#         __map_dict[key] = SiftMap(map_name=map_name,block_size=block_size,img=img, des=des, kep=kep, center=center)
#     return __map_dict[key]


# 将关键点的数据转换为可以序列化的格式
# 只能在google lab运行，需要运行内存至少100G
def __save(block_size, map_name):
    # 假设 'surf' 是已经初始化的cv2.xresources/features2d.SURF对象
    # 'bigmap' 是大图像的变量
    surf = cv2.SIFT.create()
    bigmap = cv2.imread(get_bigmap_path(block_size=block_size,map_name=map_name), 0)
    # 检测关键点和计算描述符
    keypoints_large, descriptors_large = surf.detectAndCompute(bigmap, None)
    index = []
    for point in keypoints_large:
        temp = (point.pt, point.size, point.angle, point.response, point.octave, point.class_id)
        index.append(temp)

    # 保存关键点和描述符
    kpp, desp = get_keypoints_des_path(block_size,map_name)
    with open(kpp, 'wb') as kp_file:
        pickle.dump(index, kp_file)
    with open(desp, 'wb') as des_file:
        pickle.dump(descriptors_large, des_file)

def load(block_size, map_name):
    kpp, desp = get_keypoints_des_path(block_size, map_name)
    # 读取关键点
    with open( kpp, 'rb') as kp_file:
        index = pickle.load(kp_file)
    keypoints_large = []
    for point in index:
        temp = cv2.KeyPoint(x=point[0][0], y=point[0][1], size=point[1], angle=point[2], response=point[3],
                            octave=point[4], class_id=point[5])
        keypoints_large.append(temp)
    # 读取描述符
    with open(desp, 'rb') as des_file:
        descriptors_large = pickle.load(des_file)
    return keypoints_large, descriptors_large


def sift_kp_des_generator():
    from myutils.configutils import MapConfig

if __name__ == '__main__':
    block_size = 2048
    # block_size = 256
    # map_name = 'liyue'
    # map_name = 'fengdan'
    # map_name = 'nata'
    # map_name = 'xumi'
    # map_name = 'daoqi'
    map_name = 'mengde'
    # map_name = 'shachongsuidao-shangfangtonglu'
    # __save(block_size, map_name)
    kp, des = load(block_size, map_name)
    print(des.shape)
    # mapobj = get_sift_map(map_name='枫丹', block_size=block_size)
    # print(mapobj.map_name)
