import sys
import time

import cv2
import requests
import numpy as np
from mylogger.MyLogger3 import MyLogger
from io import BytesIO
import logging
from myutils.configutils import ServerConfig
logger = MyLogger('server_api', logging.INFO)
logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)

host = ServerConfig.get(ServerConfig.KEY_HOST)
port = ServerConfig.get(ServerConfig.KEY_PORT)
url = f'http://{host}:{port}/'
ocr_url = f'http://{host}:{port}/'

def __log(*args):
    logger.debug(args)

def __err(*args):
    logger.error(args)

from capture.capture_factory import capture
gs = capture

def get_ocr_result(mss_mode=False):
    if mss_mode:
        response = requests.get(f"{ocr_url}/ocr/screen_mss")
    else: response = requests.get(f"{ocr_url}/ocr/screen")
    if response.status_code == 200:
        result = response.json()
        if result.get('success') is True:
            return result.get('data')
        else:
            logger.error(result.get('message'))
            return None
    else:
        return None

def get_ocr_fight_team():
    response = requests.get(f"{ocr_url}/ocr/fight_team")
    if response.status_code == 200:
        result = response.json()
        if result.get('success') is True:
            return result.get('data')
        else:
            logger.error(result.get('message'))
            return None
    return None

def position():
    resp = requests.get(f"{url}/minimap/get_position")
    if resp.status_code == 200:
        result = resp.json()
        if result.get('success') is True:
            return result.get('data')
    return None

def user_map_position():
    resp = requests.get(f"{url}/usermap/get_position")
    if resp.status_code == 200:
        result = resp.json()
        if result.get('success') is True:
            return result.get('data')
    return None

def user_map_scale():
    resp = requests.get(f"{url}/usermap/get_scale")
    if resp.status_code == 200:
        result = resp.json()
        if result.get('success') is True:
            return result.get('data')
    return None

def create_cached_local_map(center_pos=None, use_middle_map=False):
    jsondata = {'center_pos': center_pos, 'use_middle_map': use_middle_map}
    result = requests.post(f"{url}/usermap/create_cache", json=jsondata).json()
    __log(f"创建缓存结果{result}")

def rotation(use_alpha=False):
    req = requests.get(f"{url}/minimap/get_rotation")
    if req.status_code == 200:
        result = req.json()
        if result.get('success') is True:
            return result.get('data')
    return None
def get_position_and_rotation():
    req = requests.get(f"{url}/minimap/get_position_rotation")
    if req.status_code == 200:
        result = req.json()
        if result.get('success') is True:
            return result.get('data')
    return None
def get_insert_node():
    req = requests.get(f"{url}/minimap/get_insert_node")
    if req.status_code == 200 and req.json().get('success') is True:
        return req.json().get('data')
    return None
def choose_map(map_name):
    req = requests.get(f"{url}/minimap/choose_map?map_name={map_name}")
    if req.status_code == 200 and req.json().get('success') is True:
        return True
    return False


def __cv_show(name, img):
    w = max(img.shape)
    if w > 500:
        img = cv2.resize(img, None, fx=500 / w, fy=500 / w)
    cv2.imshow(name, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def get_region_map(x, y, width, region=None):
    resp = requests.get(f"{url}/minimap/get_region_map?region={region}&x={x}&y={y}&width={width}")
    if resp.status_code == 200:
        # 处理图片
        img_bytes = BytesIO(resp.content)
        img_np = np.frombuffer(img_bytes.getvalue(), dtype=np.uint8)
        img = cv2.imdecode(img_np, cv2.IMREAD_GRAYSCALE)
        # __cv_show('rm', img)
        return img
    else:
        return None

def get_local_map():
    resp = requests.get(f"{url}/minimap/get_local_map")
    if resp.status_code != 200: return None
    # 解析图片数据
    data = resp.json()
    success = data.get('success')
    if not success:
        __log("获取localmap失败")
        return None
    data = data.get('data')
    img_base64 = data.get('img_base64')
    if img_base64 is None:
        __log("空map")
        return None
    import base64
    # 将 base64 字符串解码为字节流
    img_bytes = base64.b64decode(img_base64)

    # 将字节流转换为 numpy 数组
    img_arr = np.frombuffer(img_bytes, np.uint8)

    # 将 numpy 数组解码为 OpenCV 图像
    img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    data['map'] = img
    # cv2.imshow('img local', img)
    # __log(data.get('xywh'))
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    return data


if __name__ == '__main__':
    # 发送POST请求
    gc = capture
    # create_cached_local_map(use_middle_map=False)
    # create_cached_local_map((-7211.3272, -10996.9493))
    # create_cached_local_map((1114,-3508.5))
    # create_cached_local_map((-3786, 1154))
    while True:
    #     time.sleep(0.05)
        start = time.time()
        data = get_position_and_rotation()
        if data is None:
            print("None")
            continue
        pos = data.get('position')
        rot = data.get('rotation')
    #     # get_ocr_result()
        cost = time.time() - start
        print(f'pos {pos},rotation {rot}, time cost{cost}')
        # print(f'rotation is {rot},  cost: {cost}')

    # import threading
    # for i in range(10):
    #     threading.Thread(target=threaddemo).start()
    # img = gc.get_screenshot()
    # result = ocr(img)
    # result = get_ocr_result()[0]
    # txts = [line[1][0] for line in result]
    # print(txts)
    # print("position", position())
    # print("rotation:", rotation(True))
    # print(f"cost: {time.time() - start}s")


