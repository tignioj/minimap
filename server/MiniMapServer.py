import base64
import threading
import time

import numpy as np
from flask import Flask, request, jsonify, send_file
from capture.genshin_capture import GenShinCapture
from matchmap.sifttest.sifttest4_1 import MiniMap
from matchmap.gia_rotation import RotationGIA
import cv2
from myutils.configutils import cfg

class FlaskApp(Flask):
    minimap = MiniMap(debug_enable=True)
    minimap.get_position()
    rotate = RotationGIA(True)

    def cvshow(self):
        while True:
            time.sleep(0.1)
            localmap = self.minimap.local_map
            if localmap is not None:
                m = np.max(localmap.shape)
                if m > 300:
                    localmap = cv2.resize(localmap, None, fx=500 / m, fy=500 / m)
                cv2.imshow('Server local map', localmap)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


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
    xywh = data.get('xywh')
    use_middle_map = data.get('use_middle_map')
    result = False

    if xywh:
        (x,y,w,h) = xywh
        result = app.minimap.global_match_cache((x,y))
    elif use_middle_map:
        pos = app.minimap.get_user_map_position()
        if pos:
            pos = app.minimap.relative_axis_to_pix_axis(pos)
            result = app.minimap.global_match_cache(pos)

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

        tem_local_map = app.minimap.crop_img(app.minimap.map_2048['img'], pix_pos[0], pix_pos[1], radius)

        _, img_encoded = cv2.imencode('.jpg', tem_local_map)
        return send_file(BytesIO(img_encoded), mimetype='image/jpeg')

@app.route('/minimap/get_local_map', methods=['GET'])
def get_local_map():
    local_map = app.minimap.local_map
    if local_map is None:
        return jsonify({'result': False})

    position = app.minimap.local_map_pos
    img_base64 = cvimg_to_base64(local_map)
    data = {
        'result': True,
        'data': {
            'position': position,
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
    # app.run(host=host, port=port, debug=False)
    app.run(port=5000,debug=False)
