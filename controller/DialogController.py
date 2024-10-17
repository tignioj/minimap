import time

from controller.BaseController import BaseController


class DialogController(BaseController):
    def __init__(self, debug_enable=None):
        super().__init__(debug_enable=debug_enable)
        from controller.OCRController import OCRController
        self.ocr = OCRController()

    def f_dialog(self):
        """
        点击f进入对话
        :return:
        """
        pos = self.gc.get_icon_position(self.gc.icon_dialog_message)
        if len(pos)>0:
            self.kb_press_and_release('f')
            return True
        return False

    def skip_dialog(self):
        # 出现了对话眼睛
        if len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))>0:
            # 点击最后一个图标
            if self.click_if_appear(self.gc.icon_dialog_message, index=-1):
                self.logger.debug('点击最后一个选项')
            else: self.kb_press_and_release(self.Key.space)
        elif self.ocr.find_text_and_click('点击后继续'):
            time.sleep(0.5)

    def daily_reward_dialog(self):
        """
        先进入对话框然后点击每日委托
        :return:
        """
        start_time = time.time()
        while not len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))> 0:
            if time.time()-start_time > 4 or self.f_dialog():
                break

        # 出现了对话眼睛
        time.sleep(2)
        start_time = time.time()
        while not self.gc.has_paimon(delay=False) and time.time()-start_time < 10:
            if self.ocr.find_text_and_click('每日委托'):
                self.logger.debug('成功点击每日委托')
            else:
                if not self.gc.has_paimon(delay=False):
                    self.click_screen((30, self.gc.h-30))
            time.sleep(1.5)

    def explore_reward_dialog(self):
        """
        先进入对话框然后点击探索派遣
        :return:
        """
        start_time = time.time()
        while not len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))> 0:
            if time.time()-start_time > 4 or self.f_dialog():
                break

        # 出现了对话眼睛
        time.sleep(2)
        start_time = time.time()
        from controller.UIController import UIController
        uic = UIController()
        while not self.gc.has_paimon(delay=False) and time.time()-start_time < 15:
            if len(self.gc.get_icon_position(self.gc.icon_dialog_eyes))> 0:
                if self.ocr.find_text_and_click('探索派遣'):
                    self.logger.debug('成功点击探索派遣')
            else:
                if self.ocr.find_text_and_click('全部领取'):
                    self.logger.debug('成功点击全部领取')
                elif self.click_if_appear(self.gc.icon_button_retry):
                    self.logger.debug('成功点击再次派遣')
                    uic.navigation_to_world_page()
                    return
                else:
                    uic.navigation_to_world_page()
                    return

            time.sleep(0.1)
            self.click_screen((5, self.gc.h-5))
            time.sleep(1)

if __name__ == '__main__':
    dialog = DialogController()
    dialog.daily_reward_dialog()
    # while True:
    #     time.sleep(1)
        # dialog.skip_dialog()
    # dialog.daily_reward_dialog()
    # time.sleep(2)
    # start_wait = time.time()
    # 等待对话框重新出现
    # while time.time() - start_wait < 8:
    #     if len(dialog.gc.get_icon_position(dialog.gc.icon_dialog_message)) > 0:
    #         break
    # dialog.explore_reward_dialog()