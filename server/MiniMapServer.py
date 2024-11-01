import logging
logging.getLogger("matplotlib").setLevel(logging.INFO)
from flask import Flask, request, jsonify, send_file, render_template
from myutils.configutils import ServerConfig, DebugConfig
import logging
from flask_cors import CORS
from flask_socketio import SocketIO
from pynput.keyboard import Listener
from mylogger.MyLogger3 import MyLogger

from server.controller.ServerDomainController import domain_bp
from server.controller.TodoController import todo_bp
from server.controller.PlayBackController import playback_bp
from server.controller.FileManagerController import filemanager_bp
from server.controller.ConfigController import config_bp
from server.controller.MiniMapController import minimap_bp
from server.controller.FightTeamController import fight_team_bp
from server.controller.ServerOCRController import ocr_bp
from server.controller.DailyMissionController import daily_mission_bp
from server.controller.LeyLineOutCropController import leyline_outcrop_bp
from server.controller.OneDragonController import one_dragon_bp

from engineio.async_drivers import threading  # pyinstaller打包flask的时候要导入

# 尝试修复 Error: Failed to load module script:
# Expected a JavaScript module script but the server responded with a MIME type of "text/plain".
import mimetypes
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')

host = ServerConfig.get(ServerConfig.KEY_HOST)
port = ServerConfig.get(ServerConfig.KEY_PORT)
debug_enable = DebugConfig.get(DebugConfig.KEY_DEBUG_ENABLE)
logger = MyLogger('minimap server')

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

    try:
        if socketio_instance: socketio_instance.emit(SOCKET_EVENT_KEYBOARD, {'key': c})
    except AttributeError:
        logger.error('服务器还在启动中，请稍后再发送键盘事件')
def _on_release(key):
    try: c = key.char
    except AttributeError: c = key.name
    try:
        if socketio_instance: socketio_instance.emit(SOCKET_EVENT_KEYBOARD, {'key': c})
    except AttributeError:
        logger.error('服务器还在启动中，请稍后再发送键盘事件')


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
    app = Flask(__name__,
                static_folder='web/static',
                template_folder='web/templates')
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
    app.register_blueprint(one_dragon_bp)
    app.register_blueprint(domain_bp)


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

