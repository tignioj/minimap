from flask import Flask, request, jsonify, send_file, render_template
from myutils.configutils import get_config
import logging


logging.getLogger('werkzeug').setLevel(logging.WARNING)
from flask_cors import CORS
from flask_socketio import SocketIO
from pynput.keyboard import Listener
from mylogger.MyLogger3 import MyLogger

from engineio.async_drivers import threading  # pyinstaller打包flask的时候要导入

host = get_config('minimap')['host']
port = get_config('minimap')['port']

logger = MyLogger('minimap server')

if get_config('debug_enable') == 1:
    debug_enable = True
else:
    debug_enable = False

SOCKET_EVENT_PLAYBACK = 'playback_event'
SOCKET_EVENT_KEYBOARD = 'key_event'

class FlaskApp(Flask):pass

def _on_press(key):
    try: c = key.char
    except AttributeError: c = key.name
    socketio.emit(SOCKET_EVENT_KEYBOARD, {'key': c})

def _on_release(key):
    socketio.emit(SOCKET_EVENT_KEYBOARD, {'key': key})


allow_urls = [f'http://{host}:{port}',
              'http://localhost:63343',  # webstrom default
              'http://localhost:5173'  # vuejs
              ]
app = FlaskApp(__name__)
CORS(app, resources={r"/*": {"origins": allow_urls}})
app.config['SECRET_KEY'] = 'mysecret'
from server.controller.TodoController import todo_bp
from server.controller.PlayBackController import playback_bp
from server.controller.FileManagerController import filemanager_bp
from server.controller.ConfigController import config_bp
from server.controller.MiniMapController import minimap_bp
app.register_blueprint(todo_bp)
app.register_blueprint(playback_bp)
app.register_blueprint(filemanager_bp)
app.register_blueprint(config_bp)
app.register_blueprint(minimap_bp)

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
def socket_emit(event, msg, success=True):
    socketio.emit(event, {'result': success, 'msg': msg})


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
