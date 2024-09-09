import threading
import json, os
import time
from typing import Callable

from controller.BaseController import BaseController
from mylogger.MyLogger3 import MyLogger

SOCKET_EVENT_PLAYBACK_START = 'socket_event_playback_start'
SOCKET_EVENT_PLAYBACK_UPDATE = 'socket_event_playback_update'
SOCKET_EVENT_PLAYBACK_END = 'socket_event_playback_end'
SOCKET_EVENT_PLAYBACK_EXCEPTION = 'socket_event_playback_exception'
logger = MyLogger(__name__)

class PlayBackException(Exception):
    def __init__(self, message=None, status=None):
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
    # from myexecutor.GouliangPathExecutor import GouLiangPathExecutor # 目前用BasePathExecutor2就行

    executor_map = {
        "BasePathExecutor": BasePathExecutor,
        "CollectPathExecutor": CollectPathExecutor,
        "FightPathExecutor": FightPathExecutor,
        "DailyMissionPathExecutor": DailyMissionPathExecutor,
        # "GouLiangPathExecutor": GouLiangPathExecutor,
        "GouLiangPathExecutor": BasePathExecutor,  # 目前用BasePathExecutor就行
        None: BasePathExecutor,
        "": BasePathExecutor
    }

    @staticmethod
    def playBack(jsondict, socketio_instance=None):
        if jsondict is None:
            raise PlayBackException(message='空json对象，无法回放')
        # TODO BaseController会影响到全局键盘监听?还有没有其他办法控制线程退出？
        BaseController.stop_listen = False
        if PlayBackService.playing_thread_running:
            raise PlayBackException( status=PlayBackService.PLAYBACK_STATUS_ALREADY_RUNNING, message='已经有脚本正在运行中，请退出该脚本后再重试!')
        threading.Thread(target=PlayBackService.playback_runner, args=(jsondict,socketio_instance)).start()
        return True

    @staticmethod
    def playback_stop(socketio_instance):
        BaseController.stop_listen = True
        # if socketio_instance: socketio_instance.emit(SOCKET_EVENT_PLAYBACK_END)
        return True

    # 定义一个函数，接受两个str参数，一个返回值
    # 等号右边定义了一个lambda的空函数，其中val1是第一个参数，val2是第二个参数
    # 写一个空函数的作用是防止当None无法调用的问题,避免函数内每次调用都要判断空值一次
    # socket_io_emit: Callable[[str, str], None] = lambda val1, val2:None
    @staticmethod
    def playback_runner(jsondict: dict, socketio_instance=None):
        with PlayBackService.playback_lock:
            PlayBackService.playing_thread_running = True
            try:
                if socketio_instance:
                    socketio_instance.emit(SOCKET_EVENT_PLAYBACK_START, f'开始执行{jsondict.get("name")}')

                start_time = time.time()
                json_object = json.dumps(jsondict, indent=4, ensure_ascii=False)
                from myutils.configutils import resource_path
                temp_json_path = os.path.join(resource_path, 'temp.json')
                from_index = jsondict.get('from_index', None)
                with open(temp_json_path, mode="w", encoding="utf-8") as outfile:
                    outfile.write(json_object)

                executor_text = jsondict.get('executor')
                executor = PlayBackService.executor_map.get(executor_text)
                bp = executor(json_file_path=temp_json_path)
                if socketio_instance:
                    socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f'正在执行{jsondict.get("name")}')
                bp.execute(from_index=from_index)
                if socketio_instance: socketio_instance.emit(SOCKET_EVENT_PLAYBACK_END, f"{jsondict.get('name')}执行结束，用时:{time.time() - start_time}")
            except Exception as e:
                logger.exception(e, exc_info=True)
                if socketio_instance: socketio_instance.emit(SOCKET_EVENT_PLAYBACK_EXCEPTION, str(e.args))
            finally:
                PlayBackService.playing_thread_running = False

if __name__ == '__main__':
    # PlayBackService.test(print, 'hello', 'world')
    pass
