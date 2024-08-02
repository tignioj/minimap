from flask import Flask, request, jsonify
from paddleocr import PaddleOCR
from capture.genshin_capture import GenShinCapture
import cv2
from mylogger.MyLogger3 import MyLogger
from myutils.configutils import cfg
import logging

host = cfg['ocr']['host']
port = cfg['ocr']['port']

logging.getLogger('ppocr').setLevel(logging.INFO)

logger = MyLogger('OCRServer')
ocr = PaddleOCR(use_angle_cls=False, lang="ch",
                use_gpu=False)  # need to run only once to download and load model into memory
class FlaskApp(Flask):
    pass

app = FlaskApp(__name__)

@app.route('/ocr', methods=['POST', 'GET'])
def ocrimg():  # TODO bug: 不止为何有时候会找不到（‘探索度’）
    if request.method == 'GET':
        sc = GenShinCapture.get_screenshot()
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
