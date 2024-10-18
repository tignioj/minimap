# 打开游戏
import cv2
import time, os
from capture.capture_factory import capture
from controller.BaseController import BaseController
from myutils.clipboard_utils import copy_string, paste_text
from myutils.configutils import resource_path
template_path = os.path.join(resource_path, 'template')
icon_button_logout = cv2.imread(os.path.join(template_path, 'login','icon_button_logout.png'), cv2.IMREAD_GRAYSCALE)
icon_button_agreement = cv2.imread(os.path.join(template_path, 'login','icon_button_login_agreement.png'), cv2.IMREAD_GRAYSCALE)
from controller.OCRController import OCRController

class LoginController(BaseController):
    
    def __init__(self):
        super(LoginController, self).__init__()
        self.ocr = OCRController()
        
    def open_game(self):
        from myutils.configutils import WindowsConfig
        game_path = WindowsConfig.get(WindowsConfig.KEY_GAME_PATH)
        os.startfile(game_path)
        start_wait = time.time()
        while not capture.is_active() and time.time() - start_wait < 120 and not self.stop_listen:
            try:
                capture.activate_window()
            except Exception as e:
                self.logger.debug(e.args)
                self.logger.debug(f'正在打开游戏中, 剩余等待时间{120-(time.time() - start_wait)}')
            time.sleep(2)

        start_wait = time.time()
        while not self.ocr.is_text_in_screen("进入游戏", "点击进入", match_all=True) and time.time()-start_wait < 120:
            if self.stop_listen: return
            self.logger.debug(f'正在载入登录界面, 剩余等待时间:{120-(time.time()-start_wait)}秒')
            time.sleep(2)

        if self.ocr.is_text_in_screen("进入游戏", "点击进入"):
            self.logger.debug('成功加载登录界面')
        else:
            self.logger.debug('无法加载登录界面')
            return False

        self.logger.debug('点击切换账号')
        self.ocr.click_if_appear(icon_button_logout,timeout=0.5)
        time.sleep(1)
        self.ocr.find_text_and_click('确定', match_all=True)

    def user_input_focus(self):
        capture.activate_window()
        time.sleep(0.5)
        self.ocr.find_text_and_click('输入手机号')
        
    def password_input_focus(self):
        capture.activate_window()
        time.sleep(0.5)
        self.ocr.find_text_and_click('输入密码')

    def user_pwd_input(self,user_name, password):
        # 输入框获取焦点
        from controller.BaseController import BaseController
        self.logger.debug('输入框获取焦点')
        self.user_input_focus()
        self.logger.debug('删除旧数据')
        self.kb_press_and_release(self.Key.end)
        for _ in range(30):
            time.sleep(0.02)
            self.kb_press_and_release(self.Key.backspace)

        self.logger.debug('输入账号')
        self.kb_press_and_release(self.Key.backspace)
        copy_string(user_name)
        paste_text()
        self.logger.debug('输入账号完毕')
        time.sleep(0.5)

        self.logger.debug('密码框获取焦点')
        self.password_input_focus()
        self.logger.debug('删除旧数据')
        self.kb_press_and_release(self.Key.end)
        for _ in range(30):
            time.sleep(0.02)
            self.kb_press_and_release(self.Key.backspace)

        self.logger.debug('输入密码')
        copy_string(password)
        paste_text()
        self.logger.debug('输入密码完毕')
        time.sleep(0.5)
        self.logger.debug('点击进入游戏')

        # 点击同意协议
        ocr_results = self.ocr.find_match_text('立即注册')
        if len(ocr_results) < 1: self.logger.debug('未找到立即注册按钮')
        time.sleep(0.5)
        self.click_if_appear(icon_button_agreement, timeout=0.5)
        time.sleep(0.5)

        ocr_results = self.ocr.find_match_text('进入游戏', match_all=True)
        if len(ocr_results) < 1: self.logger.debug('未找到进入游戏按钮')
        res = ocr_results[0]
        self.click_screen(res.center)
        time.sleep(5)
        start_wait = time.time()
        while not capture.has_paimon() and time.time()-start_wait < 80 and not self.stop_listen:
            self.logger.debug(f'等待进入游戏界面中, 剩余{80-(time.time()-start_wait)}秒')
            self.click_screen((10,10))
            time.sleep(3)
        self.logger.debug('成功进入游戏')


    def click_login_button(self):
        login_count = 5
        while not self.ocr.find_text_and_click("登录") and login_count > 0:
            login_count -= 1
            time.sleep(5)

    # # 指定账户密码登录
    # open_game()
    # user_pwd_input(user_name, password)

    # cv2.imwrite('login2.jpg', capture.get_screenshot())

if __name__ == '__main__':
    login = LoginController()
    login.open_game()
    from myutils.configutils import AccountConfig
    ci = AccountConfig.get_current_instance()
    account = ci.get("account")
    password = ci.get("password")
    login.user_pwd_input(user_name=account, password=password)