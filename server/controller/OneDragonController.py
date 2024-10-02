import cv2
from flask import Blueprint, request, jsonify, send_file, current_app
from capture.capture_factory import capture
from server.controller.ServerBaseController import ServerBaseController
from mylogger.MyLogger3 import MyLogger
from server.service.OneDragonService import OneDragonException

logger = MyLogger('one_dragon_controller')

one_dragon_bp = Blueprint('one_dragon', __name__)


ONE_DRAGON_START = 'socket_event_one_dragon_start'
ONE_DRAGON_UPDATE = 'socket_event_one_dragon_update'
ONE_DRAGON_END = 'socket_event_one_dragon_end'
ONE_DRAGON_EXCEPTION = 'socket_event_one_dragon_exception'


class OneDragonController(ServerBaseController):
    @staticmethod
    @one_dragon_bp.route('/one_dragon/run', methods=['POST'])
    def one_dragon_start():
        one_dragon_list = request.get_json()
        logger.debug(one_dragon_list)
        from server.service.OneDragonService import OneDragonService
        socketio_instance = current_app.extensions['socketio']
        try:
            OneDragonService.start_one_dragon(one_dragon_list, socketio_instance=socketio_instance)
        except OneDragonException as e:
            return OneDragonController.error(e.args)
        return OneDragonController.success('开始运行一条龙')

    @staticmethod
    @one_dragon_bp.route('/one_dragon/stop', methods=['GET'])
    def one_dragon_stop():
        from server.service.OneDragonService import OneDragonService
        socketio_instance = current_app.extensions['socketio']
        OneDragonService.stop_one_dragon(socketio_instance=socketio_instance)
        return OneDragonController.success('已发送停止一条龙信号')

