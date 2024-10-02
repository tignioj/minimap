
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('one_dragon_service')
# todoList = [
#   { id: 1, name: '清单', value: 'todo' , checked: false },
#   { id: 2, name: '战斗委托', value: 'dailyMission' , checked: false},
#   { id: 3, name: '地脉', value: 'leyLine' , checked: false},
#   { id: 4, name: '领取奖励', value: 'claimReward' , checked: false}
# ]
from server.dto.DataClass import OneDragon


class OneDragonService:
    @staticmethod
    def start_one_dragon(one_dragon_list=None,socketio_instance=None):
        for task in one_dragon_list:
            one_dragon = OneDragon.from_dict(task)
            logger.info(one_dragon)
            if not one_dragon.checked: continue
            elif one_dragon.value == 'todo':
                from server.service.TodoService import TodoService
                # 传入空代表从已经保存的文件中执行
                TodoService.todo_run(todo_json=None,socketio_instance=socketio_instance)
                TodoService.todo_runner_thread.join()
            elif one_dragon.value == 'dailyMission':
                from server.service.DailyMissionService import DailyMissionService
                DailyMissionService.start_daily_mission(socketio_instance=socketio_instance)
                DailyMissionService.daily_mission_thread.join()

            elif one_dragon.value == 'leyLine':
                from server.service.LeyLineOutcropService import LeyLineOutcropService
                LeyLineOutcropService.start_leyline(leyline_type=None,socketio_instance=socketio_instance)
                LeyLineOutcropService.leyline_outcrop_thread.join()
            elif one_dragon.value == 'claimReward':
                from server.service.DailyMissionService import DailyMissionService
                DailyMissionService.start_claim_reward(socketio_instance=socketio_instance)
                DailyMissionService.daily_mission_thread.join()

