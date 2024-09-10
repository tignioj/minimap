import threading
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("ley_line_outcrop_service")

SOCKET_EVENT_LEYLINE_OUTCROP_START = 'socket_event_leyline_mission_start'
SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE = 'socket_event_leyline_outcrop_update'
SOCKET_EVENT_LEYLINE_OUTCROP_END = 'socket_event_leyline_outcrop_end'
SOCKET_EVENT_LEYLINE_OUTCROP_EXCEPTION = 'socket_event_leyline_outcrop_exception'

class LeyLineOutcropException(Exception):pass
class LeyLineOutcropService:
    leyline_outcrop_running = False
    __leyline_outcrop_thread: threading.Thread = None
    lock = threading.Lock()


    @staticmethod
    def run(leyline_type,socketio_instance=None):
        with LeyLineOutcropService.lock:
            if LeyLineOutcropService.__leyline_outcrop_thread and LeyLineOutcropService.__leyline_outcrop_thread.is_alive():
                raise LeyLineOutcropException("地脉任务已经在运行中, 请勿重复执行")
            from controller.BaseController import BaseController
            BaseController.stop_listen = False
            from myexecutor.LeyLineOutcropPathExecutor import LeyLineOutcropPathExecutor

            LeyLineOutcropService.__leyline_outcrop_thread = threading.Thread(
                target=LeyLineOutcropPathExecutor.execute_all_mission, args=(leyline_type,socketio_instance.emit,))
            LeyLineOutcropService.__leyline_outcrop_thread.start()
            return "成功创建地脉任务线程,正在执行中"

    @staticmethod
    def stop(socketio_instance=None):
        from controller.BaseController import BaseController
        BaseController.stop_listen = True
        if LeyLineOutcropService.__leyline_outcrop_thread:
            try:
                socketio_instance.emit(SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE, "正在停止线程，请稍后")
                LeyLineOutcropService.__leyline_outcrop_thread.join()
                LeyLineOutcropService.__leyline_outcrop_thread = None
                socketio_instance.emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, "成功停止")
            except Exception as e:
                msg = f"地脉任务线程没有开始或者已经终止,不需要停止{e.args}"
                logger.exception(msg, exc_info=True)
                socketio_instance.emit(SOCKET_EVENT_LEYLINE_OUTCROP_EXCEPTION, msg)




