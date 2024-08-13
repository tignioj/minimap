import base64
import json
import os.path
from threading import Thread, Lock
import time
import numpy as np
from flask import Flask, request, jsonify, send_file, render_template
from capture.capture_factory import capture
from matchmap.sifttest.sifttest5 import MiniMap
from matchmap.gia_rotation import RotationGIA
import cv2
from myutils.configutils import cfg
from myutils.imgutils import crop_img
import logging

logging.getLogger('werkzeug').setLevel(logging.WARNING)
from flask_cors import CORS
from flask_socketio import SocketIO
from pynput.keyboard import Listener
from mylogger.MyLogger3 import MyLogger
from engineio.async_drivers import threading  # pyinstaller打包flask的时候要导入

logger = MyLogger('minimap server')

if cfg.get('debug_enable') == 1:
    debug_enable = True
else:
    debug_enable = False


class FlaskApp(Flask):
    minimap = MiniMap()
    large_map = minimap.map_2048['img']
    minimap.get_position()
    rotate = RotationGIA(True)
    capture.add_observer(rotate)
    capture.add_observer(minimap)


def cvimg_to_base64(cvimg):
    _, img_encoded = cv2.imencode('.jpg', cvimg)
    return base64.b64encode(img_encoded).decode("utf-8")


def _on_press(key):
    # print(f'key {key} pressed')
    try:
        c = key.char
    except AttributeError:
        c = key.name
    socketio.emit('key_event', {'key': c})


def _on_release(key):
    # print(f'key {key} released')
    socketio.emit('key_event', {'key': key})


app = FlaskApp(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app, async_mode='threading')
playing_thread_running = False

kb_listener = Listener(on_press=_on_press)
kb_listener.start()


@app.route('/')
def index():
    return render_template('index.html')


lock = Lock()


def _thread_playback(jsondict):
    global playing_thread_running
    with lock:
        playing_thread_running = True
        playback_ok = False
        try:
            json_object = json.dumps(jsondict, indent=4, ensure_ascii=False)
            from myutils.configutils import resource_path
            with open(os.path.join(resource_path, 'temp.json'), mode="w", encoding="utf-8") as outfile:
                outfile.write(json_object)
            from myexecutor.BasePathExecutor2 import BasePathExecutor
            bp = BasePathExecutor(json_dict=jsondict)
            bp.execute()
            playback_ok = True
        except Exception as e:
            logger.error(e)
            playback_ok = False
        finally:
            playing_thread_running = False
            socketio.emit('playback_event', {'result': playback_ok})


@app.route('/playback', methods=['POST'])
def playback():
    global playing_thread_running
    if playing_thread_running: return jsonify({'result': False, 'msg': '已经有脚本正在运行中，请退出该脚本后再重试!'})

    jsondict = request.json
    if jsondict is None: return jsonify({'result': False, 'msg': '空json对象，无法回放'})
    Thread(target=_thread_playback, args=(jsondict,)).start()
    return jsonify({'result': True, 'msg': '已运行回放脚本，如需停止按下ESC'})


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
    pos = app.minimap.get_position()
    return jsonify(pos)


@app.route('/minimap/get_rotation', methods=['GET'])
def get_rotation():
    img = capture.get_mini_map()
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return jsonify(app.rotate.predict_rotation(img))


from io import BytesIO


@app.route('/minimap/get_region_map', methods=['GET'])
def get_region_map():
    x = request.args.get('x')
    y = request.args.get('y')
    width = request.args.get('width')
    scale = request.args.get('scale')
    if x is not None and y is not None and width is not None:
        width = int(float(width))
        x = int(float(x))
        y = int(float(y))
        if scale is None: scale = 1
        scale = float(scale)

        pix_pos = app.minimap.relative_axis_to_pix_axis((x, y))

        if app.large_map is None:
            from myutils.configutils import get_bigmap_path
            app.large_map = cv2.imread(get_bigmap_path(2048), cv2.IMREAD_GRAYSCALE)
            if app.large_map is None:
                raise Exception("无法加载大地图")

        # tem_local_map = crop_img(app.large_map, pix_pos[0], pix_pos[1], crop_size=width, scale=scale)
        tem_local_map = crop_img(app.large_map, pix_pos[0], pix_pos[1], crop_size=width, scale=scale)
        if tem_local_map is None:
            raise Exception("无法裁剪大地图")

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


import webbrowser as w

if __name__ == '__main__':
    host = cfg['minimap']['host']
    port = cfg['minimap']['port']
    schema = 'http'
    url = f'{schema}://{host}:{port}'
    w.open(f'{url}')
    print(f"""
    {url}/minimap/get_position', methods=['GET']
    {url}/minimap/get_rotation', methods=['GET']
    {url}/minimap/get_region_map', methods=['GET']
    {url}/minimap/get_local_map', methods=['GET']
    {url}/usermap/get_position', methods=['GET']
    {url}/usermap/create_cache', methods=['POST']
    {url}/playback', methods=['POST']
    """)
    # app.run(host=host, port=port, debug=False)
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True, debug=False)
    # app.run(port=5000,debug=False)
