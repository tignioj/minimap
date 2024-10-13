import time

from flask import Flask, request, jsonify, Blueprint
from capture.capture_factory import capture
import cv2
from myutils.configutils import ServerConfig
from server.controller.ServerBaseController import ServerBaseController

# 把OCR首次运行需要的文件下载到本地
# https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_ch/whl.md#31-%E4%BB%A3%E7%A0%81%E4%BD%BF%E7%94%A8

host = ServerConfig.get(ServerConfig.KEY_HOST, '127.0.0.1')
port = ServerConfig.get(ServerConfig.KEY_PORT, 5000)
# 报错RuntimeError('could not execute a primitive'), 后续考虑尝试换成 https://gitee.com/raoyutian/paddleocrsharp/blob/master/Demo/python/PaddleOCRCppPython.py
ocr_bp = Blueprint('ocrbp', __name__)
from server.service.OCRService import OCRService
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('ocr_controller')
class ServerOCRController(ServerBaseController):
    @staticmethod
    @ocr_bp.get('/ocr/screen_mss')
    def ocr_result_mss():
        try:
            result = OCRService.ocr_result_mss()
            return ServerOCRController.success(data=result)
        except Exception as e:
            logger.error(e)
            return ServerOCRController.error(e), 500
    @staticmethod
    @ocr_bp.get('/ocr/screen')
    def ocr_result():
        try:
            result = OCRService.ocr_result()
            return ServerOCRController.success(data=result)
        except Exception as e:
            logger.error(e)
            return ServerOCRController.error(e), 500

    @staticmethod
    @ocr_bp.get('/ocr/fight_team')
    def ocr_fight_team():
        try:
            result = OCRService.ocr_fight_team()
            logger.info(result)
            return ServerOCRController.success(data=result)
        except Exception as e:
            logger.error(e)
            return ServerOCRController.error(e), 500
