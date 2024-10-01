import time
from myexecutor.BasePathExecutor2 import BasePathExecutor, ExecuteTerminateException
from mylogger.MyLogger3 import MyLogger
logger = MyLogger(__name__)
class DailyRewardExecutor(BasePathExecutor):


    @staticmethod
    def go_to_kaiselin():
        """
        前往凯瑟琳处
        :return:
        """
        from myutils.fileutils import getjson_path_byname
        # p = getjson_path_byname('奖励_凯瑟琳_须弥_1个_20241001_234749.json')
        p = getjson_path_byname('奖励_凯瑟琳_枫丹_1个_20241002_000026.json')
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
        time.sleep(2)
        start_wait = time.time()
        # 等待对话框重新出现
        while time.time() - start_wait < 5:
            if len(dc.gc.get_icon_position(dc.gc.icon_dialog_message)) > 0:
                break
        dc.explore_reward_dialog()

    def on_nearby(self, coordinates):
        if len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))>0:
            raise ExecuteTerminateException("已经到达")


if __name__ == '__main__':
    DailyRewardExecutor.click_encounter_point_gift()
    DailyRewardExecutor.go_to_kaiselin()
    DailyRewardExecutor.claim_reward()
