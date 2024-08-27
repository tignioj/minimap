from flask import Flask, request, jsonify
import os
from paddleocr import PaddleOCR
from capture.capture_factory import capture
import cv2
from mylogger.MyLogger3 import MyLogger
from myutils.configutils import resource_path, get_config
import logging

# 把OCR首次运行需要的文件下载到本地
# https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.6/doc/doc_ch/whl.md#31-%E4%BB%A3%E7%A0%81%E4%BD%BF%E7%94%A8

host = get_config('ocr')['host']
port = get_config('ocr')['port']
logging.getLogger('ppocr').setLevel(logging.INFO)

logger = MyLogger('OCRServer')
your_det_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_det_infer')
your_rec_model_dir = os.path.join(resource_path, 'ocr', 'ch_PP-OCRv4_rec_infer')
# your_rec_char_dict_path=None
your_cls_model_dir = os.path.join(resource_path, 'ocr', 'ch_ppocr_mobile_v2.0_cls_infer')
ocr = PaddleOCR(det_model_dir=f'{your_det_model_dir}', lang="ch", rec_model_dir=f'{your_rec_model_dir}',
                     cls_model_dir=f'{your_cls_model_dir}',
                     use_angle_cls=False, use_gpu=False, show_log=False)
class FlaskApp(Flask):
    pass

app = FlaskApp(__name__)

@app.route('/ocr', methods=['POST', 'GET'])
def ocr_result():  # TODO bug: 不止为何有时候会找不到（‘探索度’）
    if request.method == 'GET':
        sc = capture.get_screenshot()
        # sc = cv2.cvtColor(sc, cv2.COLOR_BGR2GRAY)
        # sc = cv2.resize(sc, None, fx=1.5, fy=1.5)
        # 由于做了缩放，客户端得到坐标后要x2
        # 缩放后速度并没有变快，似乎快慢和图片上的文本数量有比较大的关系
        try:
            # RuntimeError: (PreconditionNotMet) Tensor holds no memory. Call Tensor::mutable_data firstly.
            result = ocr.ocr(sc, cls=False)
            logger.info(result)
            return jsonify(result)
        except Exception as e:
            logger.error(e)
            return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    url = f'http://{host}:{port}/ocr'
    print(f"""
    请访问 {url}
    """)
    app.run(host=host, port=port,debug=False)
