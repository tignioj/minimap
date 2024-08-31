from threading import Thread

from flask import Blueprint, jsonify, request

from controller.BaseController import BaseController
from server.service.PlayBackService import PlayBackService, PlayBackException

playback_bp = Blueprint('playback', __name__)
class PlayBackController:

    @staticmethod
    def success(status=None, message=None):
        return jsonify({'success': True, status: status, message: message})

    @staticmethod
    def error(status=0, message=None):
        return jsonify({'success': False, status: status, message: message})
    @staticmethod
    @playback_bp.route('/playback', methods=['POST'])
    def playback():
        jsondict = request.json
        if jsondict is None:
            return PlayBackController.error(message='空json对象，无法回放')
        try:
            PlayBackService.playBack(jsondict=jsondict)
            return PlayBackController.success( '已运行回放脚本')
        except PlayBackException as e:
            return PlayBackController.error( status=e.status, message=e.message)


    @staticmethod
    @playback_bp.route('/playback/stop')
    def playback_stop():
        PlayBackService.playback_stop()
        return PlayBackController.success('已停止回放脚本')