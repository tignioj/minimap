import time
import os
from paddleocr import PaddleOCR
from capture.capture_factory import capture
import cv2
from mylogger.MyLogger3 import MyLogger
from myutils.configutils import resource_path, ServerConfig
import logging

# 把OCR首次运行需要的文件下载到本地
# https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_ch/whl.md#31-%E4%BB%A3%E7%A0%81%E4%BD%BF%E7%94%A8

logging.getLogger('ppocr').setLevel(logging.WARNING)
logger = MyLogger('ocr_service')
your_det_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_det_infer')
your_rec_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_rec_infer')
# your_rec_char_dict_path=None
your_cls_model_dir = os.path.join(resource_path, 'ocr', 'ch_ppocr_mobile_v2.0_cls_infer')
ocr = PaddleOCR(det_model_dir=f'{your_det_model_dir}',
                lang="ch", rec_model_dir=f'{your_rec_model_dir}',
                cls_model_dir=f'{your_cls_model_dir}',
               use_angle_cls=False, use_gpu=False, show_log=False )

# 报错RuntimeError('could not execute a primitive'), 后续考虑尝试换成 https://gitee.com/raoyutian/paddleocrsharp/blob/master/Demo/python/PaddleOCRCppPython.py

class OCRService:
    @classmethod
    def ocr_result_mss(cls):

        sc = capture.get_screenshot(mss_mode=True)
        result = ocr.ocr(sc, cls=False)
        return result

    @classmethod
    def ocr_result(cls):
        sc = capture.get_screenshot()
        b,g,r,alpha = cv2.split(sc)
        # RuntimeError: (PreconditionNotMet) Tensor holds no memory. Call Tensor::mutable_data firstly.
        result = ocr.ocr(sc, cls=False)
        # logger.info(result)
        return result

    @classmethod
    def ocr_fight_team(cls):
        # sc = capture.get_screenshot()
        sc = capture.get_team_area()
        b,g,r,alpha = cv2.split(sc)
        result = ocr.ocr(alpha, cls=False)
        return result
