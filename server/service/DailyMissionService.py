import threading
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("daily_mission_service")

SOCKET_EVENT_DAILY_MISSION_START = 'socket_event_daily_mission_start'
SOCKET_EVENT_DAILY_MISSION_UPDATE = 'socket_event_daily_mission_update'
SOCKET_EVENT_DAILY_MISSION_END = 'socket_event_daily_mission_end'
SOCKET_EVENT_DAILY_MISSION_EXCEPTION = 'socket_event_daily_mission_exception'

class DailyMissionException(Exception):pass
class DailyMissionService:
    daily_mission_running = False
    __daily_mission_thread: threading.Thread = None
    lock = threading.Lock()



    @staticmethod
    def run(socketio_instance=None):
        with DailyMissionService.lock:
            if DailyMissionService.__daily_mission_thread and DailyMissionService.__daily_mission_thread.is_alive():
                raise DailyMissionException("每日委托已经在运行中")
            from controller.BaseController import BaseController
            BaseController.stop_listen = False
            from myexecutor.DailyMissionPathExecutor import DailyMissionPathExecutor

            DailyMissionService.__daily_mission_thread = threading.Thread(
                target=DailyMissionPathExecutor.execute_all_mission, args=(socketio_instance.emit,))
            DailyMissionService.__daily_mission_thread.start()
            return "成功创建每日委托线程,正在执行中"

    @staticmethod
    def stop(socketio_instance=None):
        from controller.BaseController import BaseController
        BaseController.stop_listen = True
        if DailyMissionService.__daily_mission_thread:
            try:
                socketio_instance.emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, "正在停止线程，请稍后")
                DailyMissionService.__daily_mission_thread.join()
                DailyMissionService.__daily_mission_thread = None
                socketio_instance.emit(SOCKET_EVENT_DAILY_MISSION_END, "成功停止")
            except Exception as e:
                msg = f"每日委托线程没有开始或者已经终止,不需要停止{e.args}"
                logger.exception(msg, exc_info=True)
                socketio_instance.emit(SOCKET_EVENT_DAILY_MISSION_EXCEPTION, msg)




