from flask import Flask, request, jsonify, send_file, render_template
from myutils.configutils import get_config
import logging
from flask_cors import CORS
from flask_socketio import SocketIO
from pynput.keyboard import Listener
from mylogger.MyLogger3 import MyLogger

from server.controller.TodoController import todo_bp
from server.controller.PlayBackController import playback_bp
from server.controller.FileManagerController import filemanager_bp
from server.controller.ConfigController import config_bp
from server.controller.MiniMapController import minimap_bp
from server.controller.FightTeamController import fight_team_bp
from server.controller.ServerOCRController import ocr_bp
from server.controller.DailyMissionController import daily_mission_bp
from server.controller.LeyLineOutCropController import leyline_outcrop_bp

from engineio.async_drivers import threading  # pyinstaller打包flask的时候要导入

host = get_config('minimap')['host']
port = get_config('minimap')['port']
logger = MyLogger('minimap server')

if get_config('debug_enable') == 1: debug_enable = True
else: debug_enable = False

SOCKET_EVENT_PLAYBACK = 'playback_event'
SOCKET_EVENT_KEYBOARD = 'key_event'
allow_urls = [f'http://{host}:{port}',
              'http://localhost:63343',  # webstrom default
              'http://localhost:5173'  # vuejs
              ]
socketio_instance = SocketIO(async_mode='threading', cors_allowed_origins=allow_urls)

def _on_press(key):
    try: c = key.char
    except AttributeError: c = key.name
    if socketio_instance: socketio_instance.emit(SOCKET_EVENT_KEYBOARD, {'key': c})

def _on_release(key):
    try: c = key.char
    except AttributeError: c = key.name
    if socketio_instance: socketio_instance.emit(SOCKET_EVENT_KEYBOARD, {'key': c})


# socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="http://localhost:63343")
kb_listener = Listener(on_press=_on_press)
kb_listener.start()
#
# @app.route('/new')
# def new_pathlist():
#     return render_template('new.html')
# def socket_emit(event, msg, success=True):
#     socketio.emit(event, {'result': success, 'msg': msg})

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": allow_urls}})
    app.config['SECRET_KEY'] = 'mysecret'
    socketio_instance.init_app(app)
    app.register_blueprint(todo_bp)
    app.register_blueprint(playback_bp)
    app.register_blueprint(filemanager_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(minimap_bp)
    app.register_blueprint(fight_team_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(daily_mission_bp)
    app.register_blueprint(leyline_outcrop_bp)


    return app


import webbrowser as w

if __name__ == '__main__':
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    schema = 'http'
    url = f'{schema}://{host}:{port}'
    w.open(f'{url}')
    # app.run(host=host, port=port, debug=False)
    app = create_app()

    # ########################  界面
    @app.route('/')
    def index():
        return render_template('index.html')

    socketio_instance.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
    # app.run(port=5000,debug=False)
