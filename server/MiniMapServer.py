import base64
import threading
import time

import numpy as np
from flask import Flask, request, jsonify, send_file
from capture.genshin_capture import GenShinCapture
from matchmap.sifttest.sifttest5 import MiniMap
from matchmap.gia_rotation import RotationGIA
import cv2
from myutils.configutils import cfg
from myutils.imgutils import crop_img
import logging
logging.getLogger('werkzeug').setLevel(logging.WARNING)

if cfg.get('debug_enable') == 1:
    debug_enable = True
else:
    debug_enable = False


class FlaskApp(Flask):
    minimap = MiniMap(debug_enable=debug_enable)
    large_map = minimap.map_2048['img']
    minimap.get_position()
    rotate = RotationGIA(True)
    GenShinCapture.add_observer(rotate)
    GenShinCapture.add_observer(minimap)

def cvimg_to_base64(cvimg):
    _, img_encoded = cv2.imencode('.jpg', cvimg)
    return base64.b64encode(img_encoded).decode("utf-8")


app = FlaskApp(__name__)

@app.route('/usermap/get_position', methods=['GET'])
def get_user_map_position():
    return jsonify(app.minimap.get_user_map_position())


@app.route('/usermap/create_cache', methods=['POST'])
def create_cached_local_map():
    data = request.json  # 获取JSON数据
    center_pos = data.get('center_pos')
    use_middle_map = data.get('use_middle_map')
    result = False
    if center_pos:
        # 用户传过来的是相对位置，要转换成绝对位置
        pix_pos = app.minimap.relative_axis_to_pix_axis(center_pos)
        result = app.minimap.global_match_cache(pix_pos)
    elif use_middle_map:
        # 现在传送移动地图不是移动到中心点，传送的时候禁止用此方法创建缓存
        pos = app.minimap.get_user_map_position()
        if pos:
            pos = app.minimap.relative_axis_to_pix_axis(pos)
            result = app.minimap.global_match_cache(pos)
    else:
        result = app.minimap.create_local_map_cache_thread()

    return jsonify({"result": result})


@app.route('/minimap/get_position', methods=['GET'])
def get_position():
    t = time.time()
    pos = app.minimap.get_position()
    print('g cost:', time.time() - t)
    return jsonify(pos)


@app.route('/minimap/get_rotation', methods=['GET'])
def get_rotation():
    img = GenShinCapture.get_mini_map()
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return jsonify(app.rotate.predict_rotation(img))


from io import BytesIO

@app.route('/minimap/get_region_map', methods=['GET'])
def get_region_map():
    x = request.args.get('x')
    y = request.args.get('y')
    radius = request.args.get('radius')
    if x is not None and y is not None and radius is not None:
        radius = int(float(radius))
        x = int(float(x))
        y = int(float(y))

        pix_pos = app.minimap.relative_axis_to_pix_axis((x,y))

        tem_local_map = crop_img(app.minimap.map_2048['img'], pix_pos[0], pix_pos[1], radius)

        _, img_encoded = cv2.imencode('.jpg', tem_local_map)
        return send_file(BytesIO(img_encoded), mimetype='image/jpeg')

@app.route('/minimap/get_local_map', methods=['GET'])
def get_local_map():
    local_map_pos = app.minimap.local_map_pos
    if local_map_pos is None:
        return jsonify({'result': False})

    pix_pos = app.minimap.local_map_pos
    width = app.minimap.local_map_size
    tem_local_map = crop_img(app.large_map, pix_pos[0], pix_pos[1], width)
    img_base64 = cvimg_to_base64(tem_local_map)
    data = {
        'result': True,
        'data': {
            'position': pix_pos,
            'xywh': None,
            'img_base64': img_base64
        }
    }
    return jsonify(data)

# threading.Thread(target=app.cvshow).start()

if __name__ == '__main__':
    host = cfg['minimap']['host']
    port = cfg['minimap']['port']
    schema = 'http'
    url = f'{schema}://{host}:{port}'
    print(f"""
    {url}/minimap/get_position', methods=['GET']
    {url}/minimap/get_rotation', methods=['GET']
    {url}/minimap/get_region_map', methods=['GET']
    {url}/minimap/get_local_map', methods=['GET']
    {url}/usermap/get_position', methods=['GET']
    {url}/usermap/create_cache', methods=['POST']
    """)
    app.run(host=host, port=port, debug=False)
    # app.run(port=5000,debug=False)
