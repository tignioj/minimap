import time

from flask import Flask, request, jsonify, Blueprint
import os
from paddleocr import PaddleOCR
from capture.capture_factory import capture
import cv2
from mylogger.MyLogger3 import MyLogger
from myutils.configutils import resource_path, ServerConfig
import logging

from server.controller.ServerBaseController import ServerBaseController

# 把OCR首次运行需要的文件下载到本地
# https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_ch/whl.md#31-%E4%BB%A3%E7%A0%81%E4%BD%BF%E7%94%A8

host = ServerConfig.get(ServerConfig.KEY_HOST, '127.0.0.1')
port = ServerConfig.get(ServerConfig.KEY_PORT, 5000)
logging.getLogger('ppocr').setLevel(logging.WARNING)

logger = MyLogger('OCRServer')
your_det_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_det_infer')
your_rec_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_rec_infer')
# your_rec_char_dict_path=None
your_cls_model_dir = os.path.join(resource_path, 'ocr', 'ch_ppocr_mobile_v2.0_cls_infer')
ocr = PaddleOCR(det_model_dir=f'{your_det_model_dir}',
                lang="ch", rec_model_dir=f'{your_rec_model_dir}',
                cls_model_dir=f'{your_cls_model_dir}',
               use_angle_cls=False, use_gpu=False, show_log=False )

# 报错RuntimeError('could not execute a primitive'), 后续考虑尝试换成 https://gitee.com/raoyutian/paddleocrsharp/blob/master/Demo/python/PaddleOCRCppPython.py
ocr_bp = Blueprint('ocrbp', __name__)

class ServerOCRController(ServerBaseController):
    @staticmethod
    @ocr_bp.get('/ocr/screen_mss')
    def ocr_result_mss():

        sc = capture.get_screenshot(mss_mode=True)
        try:
            # RuntimeError: (PreconditionNotMet) Tensor holds no memory. Call Tensor::mutable_data firstly.
            result = ocr.ocr(sc, cls=False)
            # logger.info(result)
            return ServerOCRController.success(data=result)
        except Exception as e:
            logger.error(e)
            return ServerOCRController.error(e), 500
    @staticmethod
    @ocr_bp.get('/ocr/screen')
    def ocr_result():
        sc = capture.get_screenshot()
        b,g,r,alpha = cv2.split(sc)
        try:
            # RuntimeError: (PreconditionNotMet) Tensor holds no memory. Call Tensor::mutable_data firstly.
            result = ocr.ocr(sc, cls=False)
            # logger.info(result)
            return ServerOCRController.success(data=result)
        except Exception as e:
            logger.error(e)
            return ServerOCRController.error(e), 500

    @staticmethod
    @ocr_bp.get('/ocr/fight_team')
    def ocr_fight_team():
        # sc = capture.get_screenshot()
        sc = capture.get_team_area()
        b,g,r,alpha = cv2.split(sc)
        # sc = cv2.cvtColor(sc, cv2.COLOR_BGR2GRAY)
        # sc = cv2.resize(sc, None, fx=1.5, fy=1.5)
        # 由于做了缩放，客户端得到坐标后要x2
        # 缩放后速度并没有变快，似乎快慢和图片上的文本数量有比较大的关系
        try:
            # RuntimeError: (PreconditionNotMet) Tensor holds no memory. Call Tensor::mutable_data firstly.
            result = ocr.ocr(alpha, cls=False)
            logger.info(result)
            # return jsonify(result)
            return ServerOCRController.success(data=result)
        except Exception as e:
            logger.error(e)
            return ServerOCRController.error(e), 500
