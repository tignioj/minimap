import os,json
import time
from threading import Lock, Thread

from controller.BaseController import BaseController
from server.service.PlayBackService import PlayBackService
from myutils.configutils import get_user_folder
from myutils.jsonutils import getjson_path_byname


class TodoException(Exception):pass
class TodoExecuteException(Exception):pass

todo_runner_lock = Lock()
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('todo_service')
_is_thread_todo_running = True


class TodoService:

    def get_todo_by_name(self): pass

    @staticmethod
    def get_unrepeated_file(todo_json):
        # 提取非重复文件
        json_file_set = []
        for item in todo_json:
            enable = item.get('enable', False)
            # 只保留启用的清单
            if not enable: continue
            files = item.get('files', [])
            for file in files:
                if file not in json_file_set:
                    json_file_set.append(file)
        return json_file_set

    @staticmethod
    def _thread_todo_runner(todo_json=None):
        with todo_runner_lock:  # 子线程嵌套时，不要用同一个锁！
            global _is_thread_todo_running

            if _is_thread_todo_running or PlayBackService.playing_thread_running:
                logger.error("已经有清单线程正在执行中，不要重复创建线程！")
                return
            try:
                if todo_json:
                    json_file_set = TodoService.get_unrepeated_file(todo_json)
                else:
                    todo_path = os.path.join(get_user_folder(), 'todo.json')
                    with open(todo_path, 'r', encoding='utf8') as f:
                        todo_dict = json.load(f)
                        json_file_set = TodoService.get_unrepeated_file(todo_dict)

                # 加载json并执行
                for json_file_name in json_file_set:
                    json_file_path = getjson_path_byname(json_file_name)
                    # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'正在执行{json_file_name}')
                    if not os.path.exists(json_file_path):
                        # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'{json_file_name}不存在', success=False)
                        continue

                    while PlayBackService.playing_thread_running:
                        logger.debug(f'回放线程正在执行中，请等待')
                        time.sleep(1)
                        if not _is_thread_todo_running:
                            logger.debug("停止执行清单")
                            BaseController.stop_listen = True
                            return

                    with open(json_file_path, 'r', encoding='utf8') as f:
                        json_dict = json.load(f)
                    PlayBackService.playback_runner(json_dict)
            finally:
                _is_thread_todo_running = False
                logger.debug('结束执行清单了')
                # socket_emit(SOCKET_EVENT_PLAYBACK, msg='结束执行清单了')

    @staticmethod
    def todo_run(todo_json):
        # # 每次请求是不同的线程，意味着可能存在资源共享问题
        if not _is_thread_todo_running:
            files = TodoService.get_unrepeated_file(todo_json)
            if len(files) == 0:
                raise TodoExecuteException('空清单，无法执行')

            BaseController.stop_listen = False

            Thread(target=TodoService._thread_todo_runner, args=(todo_json,)).start()
            return True
        else:
            raise TodoExecuteException('已经有线程执行清单中')
            # return jsonify( {'success': False, 'status': PLAYBACK_STATUS_ALREADY_RUNNING, 'data': '已经有线程执行清单中'})

    @staticmethod
    def get_all_todos():
        todo_path = os.path.join(get_user_folder(), 'todo.json')
        if not os.path.exists(todo_path):
            with open(todo_path, 'w', encoding='utf8') as f:
                todo_dict = {'采集清单': {"enable": True, "files": []}}
                f.write(json.dumps(todo_dict))
            return todo_dict
        with open(todo_path, 'r', encoding='utf8') as f:
            try:
                data = json.load(f)
                return data
            except json.decoder.JSONDecodeError as e:
                raise TodoException('json解析错误！')

    @staticmethod
    def todo_stop():
        BaseController.stop_listen = True
        if not TodoService._is_thread_todo_running:
            raise TodoExecuteException('未执行清单，无需停止')
        else:
            TodoService._is_thread_todo_running = False
            return True

    def remove_todo_by_name(self): pass

    @staticmethod
    def save_todo(data):
        todo_path = os.path.join(get_user_folder(), 'todo.json')
        with open(todo_path, 'w', encoding='utf8') as f:
            f.write(data)
        return True
