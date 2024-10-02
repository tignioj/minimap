import threading
from mylogger.MyLogger3 import MyLogger

logger = MyLogger("ley_line_outcrop_service")

SOCKET_EVENT_LEYLINE_OUTCROP_START = 'socket_event_leyline_mission_start'
SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE = 'socket_event_leyline_outcrop_update'
SOCKET_EVENT_LEYLINE_OUTCROP_END = 'socket_event_leyline_outcrop_end'
SOCKET_EVENT_LEYLINE_OUTCROP_EXCEPTION = 'socket_event_leyline_outcrop_exception'


class LeyLineOutcropException(Exception): pass


class LeyLineOutcropService:
    leyline_outcrop_running = False
    leyline_outcrop_thread: threading.Thread = None
    lock = threading.Lock()

    @staticmethod
    def start_leyline(leyline_type=None, socketio_instance=None):
        with LeyLineOutcropService.lock:
            if LeyLineOutcropService.leyline_outcrop_thread and LeyLineOutcropService.leyline_outcrop_thread.is_alive():
                raise LeyLineOutcropException("地脉任务已经在运行中, 请勿重复执行")
            from controller.BaseController import BaseController
            BaseController.stop_listen = False
            from myexecutor.LeyLineOutcropPathExecutor import LeyLineOutcropPathExecutor
            if leyline_type is None:
                from myutils.configutils import LeyLineConfig
                leyline_type = LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_TYPE)

            LeyLineOutcropService.leyline_outcrop_thread = threading.Thread(
                target=LeyLineOutcropPathExecutor.execute_all_mission, args=(leyline_type, socketio_instance.emit,))
            LeyLineOutcropService.leyline_outcrop_thread.start()
            return "成功创建地脉任务线程,正在执行中"

    @staticmethod
    def stop(socketio_instance=None):
        from controller.BaseController import BaseController
        BaseController.stop_listen = True
        if LeyLineOutcropService.leyline_outcrop_thread:
            try:
                socketio_instance.emit(SOCKET_EVENT_LEYLINE_OUTCROP_UPDATE, "正在停止线程，请稍后")
                LeyLineOutcropService.leyline_outcrop_thread.join()
                LeyLineOutcropService.leyline_outcrop_thread = None
                socketio_instance.emit(SOCKET_EVENT_LEYLINE_OUTCROP_END, "成功停止")
            except Exception as e:
                msg = f"地脉任务线程没有开始或者已经终止,不需要停止{e.args}"
                logger.exception(msg, exc_info=True)
                socketio_instance.emit(SOCKET_EVENT_LEYLINE_OUTCROP_EXCEPTION, msg)

    @staticmethod
    def valid_number(num, min_value, max_value):
        valid = int(num)
        if valid < min_value:
            valid = min_value
        elif valid > max_value:
            valid = max_value
        return valid

    @staticmethod
    def get_config():
        from myutils.configutils import LeyLineConfig
        et = LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_OUTCROP_TASK_EXECUTE_TIMEOUT)
        ft = LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_OUTCROP_TASK_FIGHT_TIMEOUT)
        pickup_enable = LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_ENABLE_WANYE_PICKUP_AFTER_REWARD)
        fight_team = LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_FIGHT_TEAM)
        leyline_type = LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_TYPE)
        return {
            'leyline_outcrop_task_execute_timeout': et,
            'leyline_outcrop_task_fight_timeout': ft,
            'leyline_enable_wanye_pickup_after_reward': pickup_enable,
            'leyline_fight_team': fight_team,
            'leyline_type': leyline_type
        }

    @staticmethod
    def set_config(json_dict):
        from myutils.configutils import LeyLineConfig
        et = json_dict.get('leyline_outcrop_task_execute_timeout', 40)
        ft = json_dict.get('leyline_outcrop_task_fight_timeout', 20)
        pickup_enable = json_dict.get('leyline_enable_wanye_pickup_after_reward', True)

        fight_team = json_dict.get('leyline_fight_team')
        leyline_type = json_dict.get('leyline_type')

        LeyLineConfig.set(LeyLineConfig.KEY_LEYLINE_OUTCROP_TASK_EXECUTE_TIMEOUT,
                          LeyLineOutcropService.valid_number(et, 60, 3600))
        LeyLineConfig.set(LeyLineConfig.KEY_LEYLINE_OUTCROP_TASK_FIGHT_TIMEOUT,
                          LeyLineOutcropService.valid_number(ft, 10, 400))
        LeyLineConfig.set(LeyLineConfig.KEY_LEYLINE_ENABLE_WANYE_PICKUP_AFTER_REWARD, pickup_enable)

        LeyLineConfig.set(LeyLineConfig.KEY_LEYLINE_FIGHT_TEAM, fight_team)

        LeyLineConfig.set(LeyLineConfig.KEY_LEYLINE_TYPE, leyline_type)

        LeyLineConfig.save_config()
