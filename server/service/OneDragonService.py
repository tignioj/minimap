import json
import os
import time

from mylogger.MyLogger3 import MyLogger
# todoList = [
#   { id: 1, name: '清单', value: 'todo' , checked: false },
#   { id: 2, name: '战斗委托', value: 'dailyMission' , checked: false},
#   { id: 3, name: '地脉', value: 'leyLine' , checked: false},
#   { id: 4, name: '领取奖励', value: 'claimReward' , checked: false}
# ]
from server.dto.DataClass import OneDragon
import threading
from myutils.os_utils import sleep_sys, shutdown_sys, kill_game

class OneDragonException(Exception): pass

logger = MyLogger('one_dragon_service')
one_dragon_lock = threading.Lock()
SOCKET_EVENT_ONE_DRAGON_START = 'socket_event_one_dragon_start'
SOCKET_EVENT_ONE_DRAGON_UPDATE = 'socket_event_one_dragon_update'
SOCKET_EVENT_ONE_DRAGON_END = 'socket_event_one_dragon_end'
SOCKET_EVENT_ONE_DRAGON_EXCEPTION = 'socket_event_one_dragon_exception'

class OneDragonService:
    one_dragon_thread = None

    @staticmethod
    def run(one_dragon_list, socketio_instance):
        from controller.BaseController import BaseController
        from server.service.DailyMissionService import DailyMissionService
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
                    DailyMissionService.start_daily_mission(socketio_instance=socketio_instance)
                    DailyMissionService.daily_mission_thread.join()

                elif one_dragon.value == 'leyLine':
                    from server.service.LeyLineOutcropService import LeyLineOutcropService
                    LeyLineOutcropService.start_leyline(leyline_type=None, socketio_instance=socketio_instance)
                    LeyLineOutcropService.leyline_outcrop_thread.join()
                elif one_dragon.value == 'claimReward':
                    DailyMissionService.start_claim_reward(socketio_instance=socketio_instance)
                    DailyMissionService.daily_mission_thread.join()
                elif one_dragon.value == 'login':
                    from myutils.configutils import AccountConfig
                    instance = AccountConfig.get_current_instance()
                    account = instance.get("account")
                    password = instance.get("password")
                    server = instance.get("server")
                    OneDragonService.login(account=account,password=password,server=server)

                # 系统命令相关
                # close_game: 关闭游戏
                # sleep_sys: 休眠
                # shutdown_sys: 关机
                elif one_dragon.value == 'closeGame':
                    OneDragonService.close_game()

                elif one_dragon.value == 'sleepSys':
                    sleep_sys()
                    # 下面的操作能执行到吗？
                    raise OneDragonException('休眠，执行结束')
                elif one_dragon.value == 'shutdownSys':
                    shutdown_sys()
                    # 下面的操作能执行到吗？
                    raise OneDragonException('关机，执行结束')

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

    @staticmethod
    def close_game():
        kill_game()

    @staticmethod
    def login(account, password, server):
        if account is None or password is None or server is None: raise Exception("账户或者密码或者服务器为空")
        account = str(account).strip()
        password = str(password).strip()
        server = str(server).strip()
        if len(account.strip()) == 0 or len(password.strip()) == 0 or len(server.strip()) == 0:
            raise Exception("账户或者密码或者服务器为空")

        from controller.LoginController import LoginController
        from controller.BaseController import BaseController
        BaseController.stop_listen = False
        login = LoginController()
        if server == "official":
            # 先关掉游戏
            try: OneDragonService.close_game()
            except Exception as e: logger.debug("无需关闭游戏")
            time.sleep(1)
            login.open_game()
            login.user_pwd_input(account, password)
        elif server == "bilibili":
            try: OneDragonService.close_game()
            except Exception as e: logger.debug("无需关闭游戏")
            from controller.LoginControllerBilibili import LoginControllerBilibili

            login = LoginControllerBilibili()
            time.sleep(1)
            login.open_game()
            login.user_pwd_input(account, password)

        else:
            raise Exception(f"未知服务器:{server}")

    all_instance_running = False
    @staticmethod
    def run_all_instance(socketio_instance=None):
        from myutils.configutils import AccountConfig

        if OneDragonService.all_instance_running:
            raise OneDragonException("已经正在运行所有实例，请勿重复运行")
        OneDragonService.all_instance_running = True
        try:
            obj = AccountConfig.get_account_obj()
            from controller.BaseController import BaseController
            instances = obj.get("instances", [])
            for instance in instances:
                if instance.get("enable") is True:
                    # 切换当前实例
                    if BaseController.stop_listen is True:
                        logger.info("中断执行所有实例")
                        return
                    name = instance.get("name")
                    logger.debug(f'切换实例:{name}')
                    AccountConfig.set_instance(name)
                    one_dragon_list = AccountConfig.get_current_one_dragon()
                    OneDragonService.start_one_dragon(one_dragon_list=one_dragon_list, socketio_instance=socketio_instance)
                    OneDragonService.one_dragon_thread.join()
        finally:
            OneDragonService.all_instance_running = False


if __name__ == '__main__':
    class DemoSocket: # 虚假的socket
        def emit(self, *args, **kwargs):
            print(args, kwargs)
    OneDragonService.run_all_instance(socketio_instance=DemoSocket())