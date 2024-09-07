from threading import Thread

from flask import Blueprint, jsonify, request, current_app
from server.controller.ServerBaseController import ServerBaseController
from server.service.PlayBackService import PlayBackService, PlayBackException
daily_mission_bp = Blueprint('daily_mission', __name__)

class DailyMissionException(Exception): pass
from server.service.DailyMissionService import DailyMissionService, DailyMissionException

class DailyMissionController(ServerBaseController):
    @staticmethod
    @daily_mission_bp.route('/daily_mission/run')
    def playback():
        # jsondict = request.json
        socketio_instance = current_app.extensions['socketio']
        try:
            DailyMissionService.run(socketio_instance=socketio_instance)
            return DailyMissionController.success('已运行回放脚本')
        except DailyMissionException as e:
            return DailyMissionController.error(message=e.args)


    @staticmethod
    @daily_mission_bp.route('/daily_mission/stop')
    def playback_stop():
        socketio_instance = current_app.extensions['socketio']
        DailyMissionService.stop(socketio_instance=socketio_instance)
        return DailyMissionController.success('已发送停止信号')
