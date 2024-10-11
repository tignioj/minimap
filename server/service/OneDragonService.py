import json
import os

from mylogger.MyLogger3 import MyLogger
logger = MyLogger('one_dragon_service')
# todoList = [
#   { id: 1, name: '清单', value: 'todo' , checked: false },
#   { id: 2, name: '战斗委托', value: 'dailyMission' , checked: false},
#   { id: 3, name: '地脉', value: 'leyLine' , checked: false},
#   { id: 4, name: '领取奖励', value: 'claimReward' , checked: false}
# ]
SOCKET_EVENT_ONE_DRAGON_START = 'socket_event_one_dragon_start'
SOCKET_EVENT_ONE_DRAGON_UPDATE = 'socket_event_one_dragon_update'
SOCKET_EVENT_ONE_DRAGON_END = 'socket_event_one_dragon_end'
SOCKET_EVENT_ONE_DRAGON_EXCEPTION = 'socket_event_one_dragon_exception'

from server.dto.DataClass import OneDragon
class OneDragonException(Exception): pass
import threading
one_dragon_lock = threading.Lock()

class OneDragonService:
    one_dragon_thread = None

    @staticmethod
    def run(one_dragon_list, socketio_instance):
        from controller.BaseController import BaseController
        try:
            for task in one_dragon_list:
                if BaseController.stop_listen:
                    logger.debug('停止监听')
                    return

                one_dragon = OneDragon.from_dict(task)
                logger.info(one_dragon)
                if not one_dragon.checked:
                    continue
                elif one_dragon.value == 'todo':
                    from server.service.TodoService import TodoService
                    # 传入空代表从已经保存的文件中执行
                    TodoService.todo_run(todo_json=None, socketio_instance=socketio_instance)
                    TodoService.todo_runner_thread.join()
                elif one_dragon.value == 'dailyMission':
                    from server.service.DailyMissionService import DailyMissionService
                    DailyMissionService.start_daily_mission(socketio_instance=socketio_instance)
                    DailyMissionService.daily_mission_thread.join()

                elif one_dragon.value == 'leyLine':
                    from server.service.LeyLineOutcropService import LeyLineOutcropService
                    LeyLineOutcropService.start_leyline(leyline_type=None, socketio_instance=socketio_instance)
                    LeyLineOutcropService.leyline_outcrop_thread.join()
                elif one_dragon.value == 'claimReward':
                    from server.service.DailyMissionService import DailyMissionService
                    DailyMissionService.start_claim_reward(socketio_instance=socketio_instance)
                    DailyMissionService.daily_mission_thread.join()

        except Exception as e:
            socketio_instance.emit(SOCKET_EVENT_ONE_DRAGON_EXCEPTION, str(e.args))
        finally:
            OneDragonService.one_dragon_thread = None
            socketio_instance.emit(SOCKET_EVENT_ONE_DRAGON_END, "一条龙已停止")

    @staticmethod
    def start_one_dragon(one_dragon_list=None,socketio_instance=None):
        if OneDragonService.one_dragon_thread is not None:
            raise OneDragonException('一条龙已经在运行中，请勿重复执行')
        with one_dragon_lock:
            from controller.BaseController import BaseController
            BaseController.stop_listen = False
            OneDragonService.one_dragon_thread = threading.Thread(target=OneDragonService.run,
                                                                  args=(one_dragon_list, socketio_instance,))
            OneDragonService.one_dragon_thread.start()


    @staticmethod
    def stop_one_dragon(socketio_instance=None):
        from controller.BaseController import BaseController
        BaseController.stop_listen = True
        socketio_instance.emit(SOCKET_EVENT_ONE_DRAGON_END,'已停止一条龙')

    @staticmethod
    def save_one_dragon(data:str):
        from myutils.configutils import BaseConfig
        user_folder = BaseConfig.get_user_folder()
        one_dragon_path = os.path.join(user_folder, 'one_dragon.json')
        with open(one_dragon_path,'w', encoding='utf8') as f:
            f.write(data)

    @staticmethod
    def get_one_dragon_json():
        from myutils.configutils import BaseConfig, AccountConfig
        user_folder = BaseConfig.get_user_folder()
        one_dragon_path = os.path.join(user_folder, 'one_dragon.json')
        if not os.path.exists(one_dragon_path):
            raise Exception(f'实例"{AccountConfig.get_current_instance_name()}"还没有配置一条龙')
        with open(one_dragon_path,'r', encoding='utf8') as f:
            return json.load(f)

