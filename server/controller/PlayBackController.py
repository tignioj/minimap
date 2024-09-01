from threading import Thread

from flask import Blueprint, jsonify, request, current_app
from server.controller.ServerBaseController import ServerBaseController
from server.service.PlayBackService import PlayBackService, PlayBackException
playback_bp = Blueprint('playback', __name__)

class PlayBackController(ServerBaseController):
    @staticmethod
    @playback_bp.route('/playback', methods=['POST'])
    def playback():
        jsondict = request.json
        socketio_instance = current_app.extensions['socketio']
        if jsondict is None:
            return PlayBackController.error(message='空json对象，无法回放')
        try:
            PlayBackService.playBack(jsondict=jsondict, socketio_instance=socketio_instance)
            return PlayBackController.success('已运行回放脚本')
        except PlayBackException as e:
            return PlayBackController.error(status=e.status, message=e.message)


    @staticmethod
    @playback_bp.route('/playback/stop')
    def playback_stop():
        socketio_instance = current_app.extensions['socketio']
        PlayBackService.playback_stop(socketio_instance=socketio_instance)
        return PlayBackController.success('已停止回放脚本')
