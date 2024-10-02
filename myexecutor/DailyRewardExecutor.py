import time
from myexecutor.BasePathExecutor2 import BasePathExecutor, ExecuteTerminateException
from mylogger.MyLogger3 import MyLogger
from server.controller.DailyMissionController import SOCKET_EVENT_DAILY_MISSION_UPDATE, SOCKET_EVENT_DAILY_MISSION_END

logger = MyLogger('daily_reward_executor')
class DailyRewardExecutor(BasePathExecutor):


    @staticmethod
    def go_to_kaiselin():
        """
        前往凯瑟琳处
        :return:
        """
        from myutils.configutils import DailyMissionConfig
        from myutils.fileutils import getjson_path_byname
        p = getjson_path_byname(DailyMissionConfig.get(DailyMissionConfig.KEY_DAILY_TASK_KAISELIN))
        DailyRewardExecutor(json_file_path=p).execute()

    @staticmethod
    def click_encounter_point_gift():
        """
        点击冒险之证的历练点奖励
        :return:
        """
        from controller.UIController import UIController
        from controller.OCRController import OCRController
        ocr = OCRController()
        uic = UIController()
        uic.navigate_to_adventure_handbook_page()
        time.sleep(0.5)
        if ocr.find_text_and_click('委托', match_all=True):
            time.sleep(0.5)
            if ocr.click_if_appear(ocr.gc.button_icon_encounter_point_gift):
                logger.debug('成功点击历练点图标')
        else:
            logger.debug('未能点击委托')
        uic.navigation_to_world_page()

    @staticmethod
    def claim_reward():
        from controller.DialogController import DialogController
        dc = DialogController()
        dc.daily_reward_dialog()
        start_wait = time.time()
        # 等待对话框重新出现
        while time.time() - start_wait < 6:
            if dc.gc.has_template_icon_in_screen(dc.gc.icon_dialog_message): break
        dc.explore_reward_dialog()

    @staticmethod
    def one_key_claim_reward(emit=lambda val1,val2:logger.debug(val2)):
        # 写一个空的lambda方法便于调试, 服务器运行时会传递一个方法

        from controller.BaseController import BaseController, StopListenException
        try:
            if not BaseController.stop_listen:
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '正在点击历练点奖励')
                DailyRewardExecutor.click_encounter_point_gift()
            if not BaseController.stop_listen:
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '正在前往枫丹凯瑟琳处')
                DailyRewardExecutor.go_to_kaiselin()
            if not BaseController.stop_listen:
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '正在领取奖励')
                DailyRewardExecutor.claim_reward()
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '结束领取')
        except StopListenException as e:
            emit(SOCKET_EVENT_DAILY_MISSION_END, '中断任务')


    def on_nearby(self, coordinates):
        if len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))>0:
            raise ExecuteTerminateException("已经到达")


if __name__ == '__main__':
    # DailyRewardExecutor.click_encounter_point_gift()
    # DailyRewardExecutor.go_to_kaiselin()
    DailyRewardExecutor.claim_reward()
    # DailyRewardExecutor.one_key_claim_reward()
