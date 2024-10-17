import time
from myexecutor.BasePathExecutor2 import BasePathExecutor, ExecuteTerminateException
from mylogger.MyLogger3 import MyLogger
from server.controller.DailyMissionController import SOCKET_EVENT_DAILY_MISSION_UPDATE, SOCKET_EVENT_DAILY_MISSION_END

# TODO: 有可能在终点处没有和凯瑟琳对话导致无法领取奖励
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
    def claim_reward_kaiselin():
        """
        凯瑟琳奖励：领取每日奖励和探索派遣
        :return:
        """
        from controller.DialogController import DialogController
        from controller.UIController import UIController
        dc = DialogController()
        dc.daily_reward_dialog()
        start_wait = time.time()
        # 回到大世界页面
        UIController().navigation_to_world_page()
        # 等待对话框重新出现
        while time.time() - start_wait < 6:
            if dc.gc.has_template_icon_in_screen(dc.gc.icon_dialog_message): break
        dc.explore_reward_dialog()

    @staticmethod
    def claim_reward_battle_pass():
        """
        领取纪行奖励
        :return:
        """
        from controller.UIController import UIController
        start_wait = time.time()

        # 回到大世界页面
        uic = UIController()
        uic.navigation_to_world_page()

        # 打开纪行页面
        from controller.OCRController import OCRController
        ocr = OCRController()
        uic.kb_press_and_release(uic.Key.f4)

        ok = False
        while time.time() - start_wait < 10:
            if ocr.is_text_in_screen("纪行等级"):
                ok = True
                break
            time.sleep(2)
            uic.kb_press_and_release(uic.Key.f4)
        if not ok:
            logger.error("超时无法打开纪行页面")
            return False

        # 点击导航栏中的任务图标, 由于是固定在顶部中间位置，因此无需识别
        uic.click_screen((uic.gc.w / 2, 30))  # 这个是任务按钮的位置，直接点击
        time.sleep(0.5)
        if ocr.find_text_and_click("一键领取"):
            logger.debug("任务：成功点击一键领取")
            time.sleep(0.5)  # 点击任意位置退出领取信息
            uic.click_screen((30, 30))
            time.sleep(0.5)

        uic.click_screen((uic.gc.w / 2-100, 30))  # 这个是奖励按钮的位置
        time.sleep(0.5)
        if ocr.find_text_and_click("一键领取"):
            logger.debug("奖励：成功点击一键领取")
            time.sleep(0.5)  # 点击任意位置退出领取信息
            uic.click_screen((30, 30))
            time.sleep(0.5)

        # 回大世界页面
        uic.navigation_to_world_page()
        return True


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
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '正在领取凯瑟琳奖励')
                DailyRewardExecutor.claim_reward_kaiselin()
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '结束领取凯瑟琳奖励')
            if not BaseController.stop_listen:
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '正在领取纪行奖励')
                DailyRewardExecutor.claim_reward_battle_pass()
                emit(SOCKET_EVENT_DAILY_MISSION_UPDATE, '结束领取纪行奖励')
        except StopListenException as e:
            emit(SOCKET_EVENT_DAILY_MISSION_END, '中断任务')


    def on_nearby(self, coordinates):
        # 接近凯瑟琳时疯狂按f避免错过对话位置；注意枫丹凯瑟琳会有npc干扰，因此枫丹凯瑟琳不建议开启疯狂f
        # 由于城内视角已经修复，因此可以考虑蒙德凯瑟琳，凯瑟琳附近无npc干扰
        if self.next_point.type == self.next_point.TYPE_TARGET:
            self.kb_press_and_release('f')
        if len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))>0:
            raise ExecuteTerminateException("已经到达")


if __name__ == '__main__':
    # DailyRewardExecutor.click_encounter_point_gift()
    # DailyRewardExecutor.go_to_kaiselin()
    # DailyRewardExecutor.claim_reward()
    # DailyRewardExecutor.one_key_claim_reward()
    DailyRewardExecutor.claim_reward_battle_pass()
    # while True:
    #     DailyRewardExecutor.one_key_claim_reward()
    #     time.sleep(1)
