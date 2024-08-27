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
from myutils.configutils import get_config
from myutils.imgutils import crop_img
import logging

logging.getLogger('werkzeug').setLevel(logging.WARNING)
from flask_cors import CORS
from flask_socketio import SocketIO
from pynput.keyboard import Listener
from mylogger.MyLogger3 import MyLogger
from myutils.configutils import resource_path, get_user_folder
from myutils.jsonutils import getjson_path_byname
import threading as th
from controller.BaseController import BaseController

from engineio.async_drivers import threading  # pyinstaller打包flask的时候要导入

host = get_config('minimap')['host']
port = get_config('minimap')['port']

logger = MyLogger('minimap server')

if get_config('debug_enable') == 1:
    debug_enable = True
else:
    debug_enable = False

from myexecutor.BasePathExecutor2 import BasePathExecutor
from myexecutor.CollectPathExecutor import CollectPathExecutor
from myexecutor.FightPathExecutor import FightPathExecutor
from myexecutor.DailyMissionPathExecutor import DailyMissionPathExecutor
from myexecutor.GouliangPathExecutor import GouLiangPathExecutor

executor_map = {
    "BasePathExecutor": BasePathExecutor,
    "CollectPathExecutor": CollectPathExecutor,
    "FightPathExecutor": FightPathExecutor,
    "DailyMissionPathExecutor": DailyMissionPathExecutor,
    "GouLiangPathExecutor": GouLiangPathExecutor,
    None: BasePathExecutor,
    "": BasePathExecutor
}
SOCKET_EVENT_PLAYBACK = 'playback_event'
SOCKET_EVENT_KEYBOARD = 'key_event'

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
    try: c = key.char
    except AttributeError: c = key.name
    socketio.emit(SOCKET_EVENT_KEYBOARD, {'key': c})

def _on_release(key):
    socketio.emit(SOCKET_EVENT_KEYBOARD, {'key': key})


allow_urls = [f'http://{host}:{port}', 'http://localhost:63343']
app = FlaskApp(__name__)
CORS(app, resources={r"/*": {"origins": allow_urls}})
app.config['SECRET_KEY'] = 'mysecret'

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=allow_urls)
# socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="http://localhost:63343")
playing_thread_running = False

kb_listener = Listener(on_press=_on_press)
kb_listener.start()


# ########################  界面
@app.route('/')
def index():
    return render_template('scriptmanager.html')


@app.route('/new')
def new_pathlist():
    return render_template('new.html')

@app.route('/config/edit')
def config_editor():
    from myutils.configutils import application_path, config_name
    config_path = os.path.join(application_path, config_name)
    with open(config_path, "r", encoding="utf8") as f:
        txt = f.read()
    return render_template('config_editor.html', config_text=txt)

# ##############################################

@app.post('/config/save')
def config_save():
    from myutils.configutils import application_path, config_name, reload_config
    config_path = os.path.join(application_path, config_name)
    with open(config_path, "w", encoding="utf8") as f:
        f.write(request.get_data(as_text=True))
    reload_config()
    return jsonify({'success': True, 'msg':'保存配置成功'})


@app.route('/pathlist/edit/<filename>')
def edit(filename):
    return render_template('edit.html', filename=filename)


@app.route('/pathlist/get/<filename>')
def getfile(filename: str):
    p = getjson_path_byname(filename.strip())
    if os.path.exists(p):
        with open(p, 'r', encoding='utf8') as f:
            data = json.load(f)
            return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'data': '文件不存在'})


@app.post('/pathlist/save/<filename>')
def savepathlist(filename):
    p = getjson_path_byname(filename)
    data = request.get_data(as_text=True)
    if data is None:
        return jsonify({'success': False, 'data': None})
    if os.path.exists(p):
        with open(p, 'w', encoding='utf8') as f:
            f.write(data)
            return jsonify({'success': True})

    return jsonify({'success': False, 'data': None})


@app.route('/pathlist/list')
def pathlist():
    p = get_config('points_path', os.path.join(resource_path, 'pathlist'))
    filemap = {}
    try:
        dirs = os.listdir(p)
        for d in dirs:
            subdir = os.path.join(p, d)
            files = os.listdir(subdir)
            filemap[d] = files
        return jsonify({'success': True, 'data': filemap})
    except FileNotFoundError as e:
        return jsonify({'success': False, 'data': '目录不存在'})



@app.get('/todo/get')
def todo_get():
    todo_path = os.path.join(get_user_folder(), 'todo.json')
    if not os.path.exists(todo_path):
        with open(todo_path, 'w', encoding='utf8') as f:
            todo_dict = {'采集清单': {"enable":True, "files":[]}}
            f.write(json.dumps(todo_dict))
        return jsonify({'success': True, 'data': todo_dict})

    with open(todo_path, 'r', encoding='utf8') as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError as e:
            return jsonify({'success': False, 'data':'json解析错误！'})

    return jsonify({'success': True, 'data': data})


@app.post('/todo/save')
def todo_save():
    todo_path = os.path.join(get_user_folder(), 'todo.json')
    with open(todo_path, 'w', encoding='utf8') as f:
        f.write(request.get_data(as_text=True))
    return jsonify({'success': True, 'data': '保存成功'})


_is_thread_todo_running = False

def get_unrepeated_file(todo_json):
    # 提取非重复文件
    json_file_set = set()
    values = todo_json.values()
    for item in values:
        enable = item.get('enable', False)
        # 只保留启用的清单
        if not enable: continue
        files = item.get('files', [])
        for file in files:
            if file not in json_file_set:
                json_file_set.add(file)
    return json_file_set

def socket_emit(event, msg, success=True):
    socketio.emit(event, {'result': success, 'msg': msg})


todo_runner_lock = Lock()
def _thread_todo_runner(todo_json=None):
    with todo_runner_lock:  # 子线程嵌套时，不要用同一个锁！
        global playing_thread_running
        global _is_thread_todo_running

        if _is_thread_todo_running or playing_thread_running:
            logger.error("已经有清单线程正在执行中，不要重复创建线程！")
            return

        _is_thread_todo_running = True
        try:
            if todo_json:
                json_file_set = get_unrepeated_file(todo_json)
            else:
                todo_path = os.path.join(get_user_folder(), 'todo.json')
                with open(todo_path, 'r', encoding='utf8') as f:
                    todo_dict = json.load(f)
                    json_file_set = get_unrepeated_file(todo_dict)

            # 加载json并执行
            for json_file_name in json_file_set:
                json_file_path = getjson_path_byname(json_file_name)
                socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'正在执行{json_file_name}')
                if not os.path.exists(json_file_path): continue

                while playing_thread_running:
                    logger.debug(f'回放线程正在执行中，请等待')
                    time.sleep(1)
                    if not _is_thread_todo_running:
                        logger.debug("停止执行清单")
                        BaseController.stop_listen = True
                        return

                with open(json_file_path, 'r', encoding='utf8') as f:
                    json_dict = json.load(f)
                _thread_playback(json_dict)
        finally:
            _is_thread_todo_running = False
            logger.debug('结束执行清单了')
            socket_emit(SOCKET_EVENT_PLAYBACK, msg='结束执行清单了')

@app.post('/todo/run')
def todo_run():
    # 每次请求是不同的线程，意味着可能存在资源共享问题
    if not _is_thread_todo_running:
        todo_json = request.get_json()
        files = get_unrepeated_file(todo_json)
        if len(files) == 0:
            return jsonify({'success': False, 'data': '空清单，无法执行'})

        BaseController.stop_listen = False

        Thread(target=_thread_todo_runner, args=(todo_json,)).start()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'data': '已经有线程执行清单中'})

@app.get('/todo/stop')
def todo_stop():
    BaseController.stop_listen = True

    global _is_thread_todo_running
    if not _is_thread_todo_running:
        return jsonify({'success': False, 'data': '未执行清单，无需停止'})
    else:
        _is_thread_todo_running = False
        return jsonify({'success': True, 'data': '停止执行清单'})



playback_lock = Lock()

def _thread_playback(jsondict: dict):
    global playing_thread_running
    with playback_lock:
        playing_thread_running = True
        playback_ok = False
        try:
            json_object = json.dumps(jsondict, indent=4, ensure_ascii=False)
            from myutils.configutils import resource_path
            temp_json_path = os.path.join(resource_path, 'temp.json')
            from_index = jsondict.get('from_index', None)
            with open(temp_json_path, mode="w", encoding="utf-8") as outfile:
                outfile.write(json_object)

            socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'正在执行{jsondict.get("name")}')
            executor_text = jsondict.get('executor')
            executor = executor_map.get(executor_text)
            bp = executor(json_file_path=temp_json_path)
            bp.execute(from_index=from_index)
            playback_ok = True
        except Exception as e:
            logger.error(e)
            playback_ok = False
        finally:
            playing_thread_running = False
            socket_emit(SOCKET_EVENT_PLAYBACK, success=playback_ok, msg="执行结束")


@app.route('/playback', methods=['POST'])
def playback():
    BaseController.stop_listen = False

    global playing_thread_running
    if playing_thread_running: return jsonify({'result': False, 'msg': '已经有脚本正在运行中，请退出该脚本后再重试!'})

    jsondict = request.json
    if jsondict is None: return jsonify({'result': False, 'msg': '空json对象，无法回放'})
    Thread(target=_thread_playback, args=(jsondict,)).start()
    return jsonify({'result': True, 'msg': '已运行回放脚本'})

@app.route('/playback/stop')
def playback_stop():
    BaseController.stop_listen = True
    return jsonify({'result': True, 'msg': '已停止回放脚本'})


@app.route('/usermap/get_position', methods=['GET'])
def get_user_map_position():
    return jsonify(app.minimap.get_user_map_position())


@app.route('/usermap/get_scale', methods=['GET'])
def get_user_map_scale():
    return jsonify(app.minimap.get_user_map_scale())


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
    absolute_position = request.args.get('absolute_position', 0) == '1'
    pos = app.minimap.get_position(absolute_position=absolute_position)
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
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
    # app.run(port=5000,debug=False)
