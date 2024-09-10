from threading import Thread

from flask import Blueprint, jsonify, request, current_app
from server.controller.ServerBaseController import ServerBaseController
from server.service.PlayBackService import PlayBackService, PlayBackException
leyline_outcrop_bp = Blueprint('leyline_outcrop', __name__)

class LeyLineOutcropException(Exception): pass
from server.service.LeyLineOutcropService import LeyLineOutcropService, LeyLineOutcropException

class LeyLineOutcropController(ServerBaseController):
    @staticmethod
    @leyline_outcrop_bp.route('/leyline_outcrop/run/<leyline_type>')
    def playback(leyline_type):
        # jsondict = request.json
        socketio_instance = current_app.extensions['socketio']
        try:
            LeyLineOutcropService.run(leyline_type=leyline_type,socketio_instance=socketio_instance)
            return LeyLineOutcropController.success('准备执行地脉任务')
        except LeyLineOutcropException as e:
            return LeyLineOutcropController.error(message=e.args)

    @staticmethod
    @leyline_outcrop_bp.route('/leyline_outcrop/stop')
    def playback_stop():
        socketio_instance = current_app.extensions['socketio']
        LeyLineOutcropService.stop(socketio_instance=socketio_instance)
        return LeyLineOutcropController.success('已发送停止信号')
