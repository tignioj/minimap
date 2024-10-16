import os, json
import time
from datetime import datetime,timedelta
from threading import Lock, Thread
from typing import List

from controller.BaseController import BaseController, StopListenException
from server.dto.DataClass import Todo
from server.service.PlayBackService import PlayBackService
from myutils.configutils import BaseConfig
from myutils.fileutils import getjson_path_byname



# TODO: 按顺序执行
# TODO: 重复执行
# TODO: 导入、导出清单？


class TodoException(Exception): pass


class TodoExecuteException(Exception): pass

todo_runner_lock = Lock()
from mylogger.MyLogger3 import MyLogger

logger = MyLogger('todo_service')

from server.service.PlayBackService import SOCKET_EVENT_PLAYBACK_EXCEPTION, SOCKET_EVENT_PLAYBACK_END, \
    SOCKET_EVENT_PLAYBACK_UPDATE

class TodoService:
    _is_thread_todo_running: bool = False
    todo_runner_thread = None

    def get_todo_by_name(self):
        pass

    @staticmethod
    def get_unrepeated_file(todo_json):
        from server.dto.DataClass import Todo
        # 提取非重复文件
        json_file_set = []
        for item in todo_json:
            todo = Todo.from_dict(item)
            # 只保留启用的清单
            if not todo.enable: continue
            for file in todo.files:
                if file not in json_file_set:
                    json_file_set.append(file)
        return json_file_set

    @staticmethod
    def change_team(fight_team):
        from controller.UIController import TeamUIController
        from myutils.configutils import FightConfig
        if fight_team is None or len(fight_team) == 0:
            fight_team = FightConfig.get(FightConfig.KEY_DEFAULT_FIGHT_TEAM)
        if fight_team is None: raise TodoException("未选择队伍!")

        tuic = TeamUIController()
        tuic.navigation_to_world_page()
        tuic.switch_team(fight_team)
        tuic.navigation_to_world_page()

    @staticmethod
    def run_one_todo(todo, socketio_instance=None):
        fight_team = todo.fight_team
        if fight_team is None or len(fight_team) == 0:
            socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f'正在执行清单{todo.name}, 未指定队伍，使用默认队伍')
        else:
            socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f'正在执行清单{todo.name}, 指定队伍为{todo.fight_team}')
        # 切换队伍
        if todo.team_enable:
            socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f'正在切换队伍')
            from controller.UIController import TeamNotFoundException
            try: TodoService.change_team(todo.fight_team)
            except TeamNotFoundException as e:
                raise TodoException(e.args)

        for file in todo.files:
            json_file_path = getjson_path_byname(file)
            # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'正在执行{json_file_name}')
            if not os.path.exists(json_file_path):
                # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'{json_file_name}不存在', success=False)
                continue
            while PlayBackService.playing_thread_running:
                logger.debug(f'回放线程正在执行中，请等待')
                time.sleep(1)
                if not TodoService._is_thread_todo_running:
                    logger.debug("停止执行清单")
                    BaseController.stop_listen = True
                    return

            if not TodoService._is_thread_todo_running:
                logger.debug("停止执行清单")
                BaseController.stop_listen = True
                return
            with open(json_file_path, 'r', encoding='utf8') as f:
                json_dict = json.load(f)

            # 添加战斗信息
            json_dict['fight_team'] = todo.fight_team
            json_dict['fight_duration'] = todo.fight_duration
            PlayBackService.playback_runner(json_dict, socketio_instance=socketio_instance)

    @staticmethod
    def updatelastExecuteDateTime(todo_name,last_execute_date_time:str):
        all_todo = TodoService.get_all_todos()
        for todo in all_todo:
            if todo_name == todo.name:
                todo.lastExecutionDate = last_execute_date_time
                break
        # 生成可序列化的字典列表
        TodoService.save_todo(all_todo)

    @staticmethod
    def _thread_todo_runner(todo_json=None, socketio_instance=None):
        with todo_runner_lock:  # 子线程嵌套时，不要用同一个锁！
            if TodoService._is_thread_todo_running or PlayBackService.playing_thread_running:
                msg = "已经有清单线程正在执行中，不要重复创建线程！"
                logger.error(msg)
                socketio_instance.emit(SOCKET_EVENT_PLAYBACK_EXCEPTION, msg)
                return
            try:
                TodoService._is_thread_todo_running = True
                from server.dto.DataClass import Todo
                # 加载json并执行

                from controller.UIController import TeamUIController
                TeamUIController.last_selected_team = None
                for todo in todo_json:
                    todo_obj = Todo.from_dict(todo)
                    try:
                        if todo_obj.enable:
                            # 查看下次执行日期是否为今天，是则执行，否则不执行
                            # 将字符串转换为日期对象
                            date_obj = datetime.strptime(todo_obj.lastExecutionDate, "%Y-%m-%d")

                            # 加执行频率
                            next_day = date_obj + timedelta(days = todo_obj.frequency)

                            # 判断是否为今天之前（包括今天）
                            is_today_or_before_today = next_day.date() <= datetime.now().date()
                            if is_today_or_before_today:
                                TodoService.run_one_todo(todo_obj, socketio_instance=socketio_instance)
                                try:
                                    TodoService.updatelastExecuteDateTime(todo_obj.name, datetime.now().strftime("%Y-%m-%d"))
                                    socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f"更新执行时间为:{next_day.date()}")
                                except Exception as e:
                                    socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f"更新'清单上次执行时间'出现异常:{e.args}")
                            else:
                                socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, f"未到执行日期，下次执行时间为:{next_day.date()}, 本次跳过")
                    except TodoException as e:
                        logger.error(e)
                        socketio_instance.emit(SOCKET_EVENT_PLAYBACK_UPDATE, str(e.args))
            except StopListenException as e:
                TodoService._is_thread_todo_running = False
                logger.debug('结束执行清单了')
                socketio_instance.emit(SOCKET_EVENT_PLAYBACK_END, '结束执行清单了')
            finally:
                TodoService._is_thread_todo_running = False
                logger.debug('结束执行清单了')
                socketio_instance.emit(SOCKET_EVENT_PLAYBACK_END, '结束执行清单了')
                TodoService.todo_runner_thread = None

    @staticmethod
    def todo_run(todo_json, socketio_instance=None):
        # # 每次请求是不同的线程，意味着可能存在资源共享问题
        if TodoService._is_thread_todo_running: raise TodoExecuteException('已经有线程执行清单中')

        if not todo_json:
            todo_path = os.path.join(BaseConfig.get_user_folder(), 'todo.json')
            with open(todo_path, 'r', encoding='utf8') as f:
                todo_json = json.load(f)

        files = TodoService.get_unrepeated_file(todo_json)

        if len(files) == 0: raise TodoExecuteException('空清单，无法执行')

        BaseController.stop_listen = False
        TodoService.todo_runner_thread = Thread(target=TodoService._thread_todo_runner, args=(todo_json, socketio_instance))
        TodoService.todo_runner_thread.start()

        return True

    @staticmethod
    def get_all_todos()->List[Todo]:
        """
        获取指定用户目录的todo
        :return:
        """
        todo_path = os.path.join(BaseConfig.get_user_folder(), 'todo.json')
        if not os.path.exists(todo_path):
            raise TodoException("todo.json文件丢失！")
            # with open(todo_path, 'w', encoding='utf8') as f:
            #     todo_dict = {'test': {"enable": True, "files": []}}
            #     f.write(json.dumps(todo_dict))
            # return todo_dict
        with open(todo_path, 'r', encoding='utf8') as f:
            try:
                data = json.load(f)
                l = []
                for todo in data:
                    todo_obj = Todo.from_dict(todo)
                    l.append(todo_obj)
                return l
            except json.decoder.JSONDecodeError as e:
                raise TodoException('json解析错误！')

    @staticmethod
    def remove_none_exists_files():
        data = TodoService.get_all_todos()
        files_removed = []
        # 遍历所有的项目，检查文件路径是否存在，并移除不存在的文件
        for item in data:
            if item.files is not None:
                original_files = item.files
                item.files = [f for f in original_files if os.path.exists(getjson_path_byname(f))]
                removed_files = set(original_files) - set(item.files)
                if removed_files:
                    files_removed.append(removed_files)
                    logger.debug(f"Removed nonexistent files {removed_files} from {item.name}")
        TodoService.save_todo(data)
        return files_removed

    @staticmethod
    def todo_stop():
        BaseController.stop_listen = True
        if not TodoService._is_thread_todo_running:
            raise TodoExecuteException('未执行清单，无需停止')
        else:
            TodoService._is_thread_todo_running = False
            return True

    def remove_todo_by_name(self):
        pass

    @staticmethod
    def save_todo(data:List[Todo]):
        todos = [obj.to_dict(obj) for obj in data]
        todo_path = os.path.join(BaseConfig.get_user_folder(), 'todo.json')
        with open(todo_path, 'w', encoding='utf8') as f:
            json.dump(todos, f, ensure_ascii=False, indent=4)
        return True

    @staticmethod
    def updateFileName(old_filename, new_filename):
        try:
            data = TodoService.get_all_todos()
            for item in data:
                item.files = [new_filename if file == old_filename else file for file in item.files]

            # 将修改后的数据写回JSON文件
            TodoService.save_todo(data)
        except TodoException as e:
            raise TodoException(e)
        return True

    @staticmethod
    def removeFiles(files_to_remove):
        # TODO: 所有实例的清单都要修改？
        # 遍历所有的项目，寻找并移除指定文件
        data = TodoService.get_all_todos()
        # 遍历所有的项目，寻找并移除指定文件
        for item in data:
            if item.files is not None:
                original_files = item.files
                item.files = [f for f in original_files if f not in files_to_remove]

                removed_files = set(original_files) - set(item.files)
                if removed_files:
                    logger.debug(f"Removed {removed_files} from {item.name}")

        TodoService.save_todo(data)

    @staticmethod
    def updateAllFileName(old_filename, new_filename):
        # 更新所有清单
        from myutils.configutils import AccountConfig, resource_path
        obj = AccountConfig.get_account_obj()
        instances = obj.get("instances")
        import fileinput
        for instance in instances:
            f = os.path.join(resource_path, f"user-{instance.get('name')}", "todo.json")
            with open(f, 'r', encoding='utf-8') as file:
                content = file.readlines()  # 读取所有行

            with open(f, 'w', encoding='utf-8') as new_file:
                for line in content:
                    # 替换字符串并写入新文件
                    new_file.write(line.replace(old_filename, new_filename))


if __name__ == '__main__':
    # TodoService.updatelastExecuteDateTime('123', '2024-01-01')
    # print(datetime.now().strftime("%Y-%m-%d"))
    TodoService.remove_none_exists_files()


    # 定义要修改的文件名和新文件名
    # old_filename = "月莲_卡扎莱宫_须弥_5个.json"
    # new_filename = "月莲_卡扎莱宫_须弥_5个.json"
    # TodoService.updateFileName(old_filename, new_filename)

    # files_to_remove = [
    #     '月莲_禅那园_须弥_4个_20240814_113747.json',
    #     '丘丘萨满_千风神殿下_蒙德_1个_20240822_014632.json',
    #     '甜甜花1_测试_蒙德_0个_20240901_080854.json'
    #     # 添加更多要移除的文件名称
    # ]
    # TodoService.removeFiles(files_to_remove)
    # data = TodoService.remove_none_exists_files()
    # logger.debug(data)
