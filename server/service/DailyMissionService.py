import threading
from mylogger.MyLogger3 import MyLogger
from server.controller.DailyMissionController import SOCKET_EVENT_DAILY_MISSION_UPDATE, SOCKET_EVENT_DAILY_MISSION_END, \
    SOCKET_EVENT_DAILY_MISSION_EXCEPTION

logger = MyLogger("daily_mission_service")


class DailyMissionException(Exception): pass


class DailyMissionService:

    __daily_mission_thread = None
    daily_mission_lock = threading.Lock()

    @staticmethod
    def start_daily_mission(socketio_instance=None):
        with DailyMissionService.daily_mission_lock:
            if DailyMissionService.__daily_mission_thread and DailyMissionService.__daily_mission_thread.is_alive():
                raise DailyMissionException("已经有任务正在运行中, 请先停止")
            def run():
                from controller.BaseController import BaseController
                BaseController.stop_listen = False
                from myexecutor.DailyMissionPathExecutor import DailyMissionPathExecutor
                try:
                    DailyMissionPathExecutor.execute_all_mission(emit=socketio_instance.emit)
                finally:
                    DailyMissionService.__daily_mission_thread = None

            DailyMissionService.__daily_mission_thread = threading.Thread(target=run)
            DailyMissionService.__daily_mission_thread.start()
            return "成功创建每日委托线程,正在执行中"

    @staticmethod
    def start_claim_reward(socketio_instance=None):
        if DailyMissionService.__daily_mission_thread and DailyMissionService.__daily_mission_thread.is_alive():
            raise DailyMissionException("已经有任务正在运行中, 请先停止")
        def run():
            from myexecutor.DailyRewardExecutor import DailyRewardExecutor
            from controller.BaseController import BaseController
            BaseController.stop_listen = False
            try: DailyRewardExecutor.one_key_claim_reward(emit=socketio_instance.emit)
            finally: DailyMissionService.__daily_mission_thread = None

        DailyMissionService.__daily_mission_thread = threading.Thread(target=run)
        DailyMissionService.__daily_mission_thread.start()
        socketio_instance.emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '成功创建领取奖励线程')

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
        from myutils.configutils import DailyMissionConfig, FightConfig
        et = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_EXECUTE_TIMEOUT)
        ft = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TIMEOUT)
        dt = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_DESTROY_TIMEOUT)
        fight_team = DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TEAM)
        # default_fight_team = FightConfig.get(FightConfig.KEY_DEFAULT_FIGHT_TEAM)
        # if fight_team is None or len(fight_team) == 0:
        #     fight_team = default_fight_team
        return {
            'daily_task_execute_timeout': et,
            'daily_task_fight_timeout': ft,
            'daily_task_destroy_timeout': dt,
            'daily_task_fight_team': fight_team
        }

    @staticmethod
    def set_config(json_dict):
        from myutils.configutils import DailyMissionConfig
        et = json_dict.get('daily_task_execute_timeout', 40)
        ft = json_dict.get('daily_task_fight_timeout', 20)
        dt = json_dict.get('daily_task_destroy_timeout', 20)

        fight_team = json_dict.get('daily_task_fight_team')

        DailyMissionConfig.set(DailyMissionConfig.KEY_DAILY_TASK_EXECUTE_TIMEOUT,
                               DailyMissionService.valid_number(et, 60, 3600))
        DailyMissionConfig.set(DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TIMEOUT,
                               DailyMissionService.valid_number(ft, 10, 400))
        DailyMissionConfig.set(DailyMissionConfig.KEY_DAILY_TASK_DESTROY_TIMEOUT,
                               DailyMissionService.valid_number(dt, 10, 400))

        DailyMissionConfig.set(DailyMissionConfig.KEY_DAILY_TASK_FIGHT_TEAM, fight_team)

        DailyMissionConfig.save_config()
