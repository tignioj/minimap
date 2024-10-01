import threading
from threading import Thread

from flask import Blueprint, jsonify, request, current_app
from server.controller.ServerBaseController import ServerBaseController
from server.service.PlayBackService import PlayBackService, PlayBackException
daily_mission_bp = Blueprint('daily_mission', __name__)

SOCKET_EVENT_DAILY_MISSION_START = 'socket_event_daily_mission_start'
SOCKET_EVENT_DAILY_MISSION_UPDATE = 'socket_event_daily_mission_update'
SOCKET_EVENT_DAILY_MISSION_END = 'socket_event_daily_mission_end'
SOCKET_EVENT_DAILY_MISSION_EXCEPTION = 'socket_event_daily_mission_exception'


class DailyMissionException(Exception): pass
from server.service.DailyMissionService import DailyMissionService, DailyMissionException

class DailyMissionController(ServerBaseController):
    @staticmethod
    @daily_mission_bp.route('/daily_mission/run')
    def playback():
        socketio_instance = current_app.extensions['socketio']
        try:
            DailyMissionService.start_daily_mission(socketio_instance=socketio_instance)
            return DailyMissionController.success('正在准备执行每日战斗委托')
        except DailyMissionException as e:
            return DailyMissionController.error(message=e.args)


    @staticmethod
    @daily_mission_bp.route('/daily_mission/claim_reward')
    def claim_reward():
        socketio_instance = current_app.extensions['socketio']
        try:
            DailyMissionService.start_claim_reward(socketio_instance=socketio_instance)
            return DailyMissionController.success("正在准备领取今日奖励")
        except DailyMissionException as e:
            return DailyMissionController.error(message=e.args)

    @staticmethod
    @daily_mission_bp.route('/daily_mission/stop')
    def playback_stop():
        socketio_instance = current_app.extensions['socketio']
        DailyMissionService.stop(socketio_instance=socketio_instance)
        return DailyMissionController.success('已发送停止信号')
    @staticmethod
    @daily_mission_bp.post('/daily_mission/set_config')
    def set_config():
        json_dict = request.get_json()
        DailyMissionService.set_config(json_dict)
        return DailyMissionController.success('设置成功')

    @staticmethod
    @daily_mission_bp.route('/daily_mission/get_config')
    def get_config():
        data = DailyMissionService.get_config()
        return DailyMissionController.success(data=data)
