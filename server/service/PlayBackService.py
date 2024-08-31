import threading
import json,os

from controller.BaseController import BaseController
from mylogger.MyLogger3 import MyLogger
logger = MyLogger(__name__)
class PlayBackException(Exception):
    def __init__(self, status=None, message=None):
        super(PlayBackException, self).__init__(message)
        self.status = status
        self.message = message


class PlayBackService:
    playback_lock = threading.Lock()
    playing_thread_running = False

    PLAYBACK_STATUS_RUNNING = 'playback_running'
    PLAYBACK_STATUS_ALREADY_RUNNING = 'playback_already_running'
    PLAYBACK_STATUS_STOP = 'playback_stopped'

    from myexecutor.BasePathExecutor2 import BasePathExecutor
    from myexecutor.CollectPathExecutor import CollectPathExecutor
    from myexecutor.FightPathExecutor import FightPathExecutor
    from myexecutor.DailyMissionPathExecutor import DailyMissionPathExecutor
    from myexecutor.GouliangPathExecutor import GouLiangPathExecutor

    executor_map = {
        "BasePathExecutor": BasePathExecutor,
        "CollectPathExecutor": CollectPathExecutor,
        "FightPathExecutor": FightPathExecutor,
        "DailyMissionPathExecutor": DailyMissionPathExecutor,
        "GouLiangPathExecutor": GouLiangPathExecutor,
        None: BasePathExecutor,
        "": BasePathExecutor
    }

    @staticmethod
    def playBack(jsondict):
        if jsondict is None:
            raise PlayBackException('空json对象，无法回放')

        BaseController.stop_listen = False
        if PlayBackService.playing_thread_running:
            raise PlayBackException(
                status=PlayBackService.PLAYBACK_STATUS_ALREADY_RUNNING,
                message='已经有脚本正在运行中，请退出该脚本后再重试!')
        threading.Thread(target=PlayBackService.playback_runner, args=(jsondict,)).start()
        return True

    @staticmethod
    def playback_stop():
        BaseController.stop_listen = True
        return True

    @staticmethod
    def playback_runner(jsondict: dict):
        with PlayBackService.playback_lock:
            PlayBackService.playing_thread_running = True
            playback_ok = False
            try:
                json_object = json.dumps(jsondict, indent=4, ensure_ascii=False)
                from myutils.configutils import resource_path
                temp_json_path = os.path.join(resource_path, 'temp.json')
                from_index = jsondict.get('from_index', None)
                with open(temp_json_path, mode="w", encoding="utf-8") as outfile:
                    outfile.write(json_object)

                # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'正在执行{jsondict.get("name")}')
                executor_text = jsondict.get('executor')
                executor = PlayBackService.executor_map.get(executor_text)
                bp = executor(json_file_path=temp_json_path)
                bp.execute(from_index=from_index)
                playback_ok = True
            except Exception as e:
                logger.error(e)
                playback_ok = False
            finally:
                PlayBackService.playing_thread_running = False
                # socket_emit(SOCKET_EVENT_PLAYBACK, success=playback_ok, msg="执行结束")

