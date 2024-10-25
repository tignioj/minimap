# 打开游戏
import cv2
import time, os
from capture.capture_factory import capture
import subprocess
from myutils.configutils import resource_path
template_path = os.path.join(resource_path, 'template')
img_login_bilibili_user = cv2.imread(os.path.join(template_path, 'login', 'img_bilibili_login_user.png'),
                                     cv2.IMREAD_GRAYSCALE)
img_login_bilibili_password = cv2.imread(os.path.join(template_path, 'login', 'img_bilibili_login_password.png'),
                                         cv2.IMREAD_GRAYSCALE)

from pathlib import Path
from pynput.mouse import Button
from pynput.mouse import Controller as MouseController
ms = MouseController()
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("login_bilibili")

class LoginControllerBilibili:
    def __init__(self):
        from capture.windowcapture3 import WindowCapture
        self.wc = WindowCapture('bilibili游戏 登录')
        from pynput.keyboard import Key
        self.Key = Key
        from pynput.keyboard import Controller
        self.kb = Controller()
        from controller.OCRController import OCRController
        self.ocr = OCRController()

    def open_game(self):
        from myutils.configutils import WindowsConfig
        game_path = WindowsConfig.get(WindowsConfig.KEY_GAME_PATH)
        gp = Path(game_path)
        game_folder = gp.parent
        game_executable = gp.name
        # 启动应用程序
        subprocess.Popen([game_executable], cwd=game_folder, shell=True)
        start_wait = time.time()
        while not self.wc.is_active() and time.time() - start_wait < 120:
            try:
                self.wc.activate_window()
            except Exception as e:
                logger.error(e.args)
                logger.debug(f'正在打开游戏中, 剩余等待时间{120-(time.time() - start_wait)}')
            time.sleep(2)

        poss = capture.get_icon_position(icon=img_login_bilibili_user, image=capture.get_screenshot(mss_mode=True))
        start_wait = time.time()
        while len(poss) < 1 and time.time()-start_wait < 120:
            logger.debug(f'正在载入登录界面, 剩余等待时间:{120-(time.time()-start_wait)}秒')
            poss = capture.get_icon_position(icon=img_login_bilibili_user, image=capture.get_screenshot(mss_mode=True))
            logger.debug(len(poss))
            time.sleep(2)

        if len(poss)>0:
            logger.debug('成功加载登录界面')
            return True
        else:
            logger.debug('无法加载登录界面')
            return False


    def click_screen(self,pos, button: Button = Button.left):
        """
        点击游戏内坐标
        :param pos:
        :param button:
        :return:
        """
        sc_pos = capture.get_screen_position(pos)
        ms.position = sc_pos
        ms.click(button)

    def user_input_focus(self):
        capture.activate_window()
        time.sleep(0.5)
        img = capture.get_screenshot(mss_mode=True)
        poss = capture.get_icon_position(icon=img_login_bilibili_user, image=img)
        pos = poss[0]
        self.ocr.click_screen((pos[0]+100, pos[1]))
    def password_input_focus(self):
        capture.activate_window()
        time.sleep(0.5)
        img = capture.get_screenshot(mss_mode=True)
        poss = capture.get_icon_position(icon=img_login_bilibili_password, image=img)
        pos = poss[0]
        self.ocr.click_screen((pos[0]+100, pos[1]))

    def kb_press_and_release(self,key):
        self.kb.press(key)
        self.kb.release(key)

    def is_activate(self):
        import win32gui
        current_win_name = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        return current_win_name in ['bilibili游戏 登录', 'bilibili游戏 防沉迷提示', '原神']

    def user_pwd_input(self,user_name, password):
        # 输入框获取焦点
        logger.debug('输入框获取焦点')
        self.user_input_focus()
        logger.debug('删除旧数据')
        self.kb_press_and_release(self.Key.end)
        for _ in range(20):
            time.sleep(0.02)
            self.kb_press_and_release(self.Key.backspace)

        logger.debug('输入账号')
        self.kb_press_and_release(self.Key.backspace)
        for c in user_name:
            time.sleep(0.05)
            self.kb_press_and_release(str(c))
        time.sleep(0.1)
        logger.debug('输入账号完毕')

        # 密码框获取焦点
        logger.debug('密码框获取焦点')
        self.password_input_focus()
        logger.debug('删除旧数据')
        self.kb_press_and_release(self.Key.end)

        for _ in range(30):
            time.sleep(0.02)
            self.kb_press_and_release(self.Key.backspace)

        logger.debug('输入密码')
        self.kb_press_and_release(self.Key.backspace)
        for c in password:
            time.sleep(0.05)
            self.kb_press_and_release(str(c))
        logger.debug('输入密码完毕')
        time.sleep(0.1)
        logger.debug('点击登录')
        ocr_results = self.ocr.find_match_text('登录', match_all=True,mss_mode=True)
        if len(ocr_results) < 1:
            logger.error('未找到登录按钮, 登录失败')
            return
        res = ocr_results[0]
        self.click_screen(res.center)  # 此时'聚焦于bilibili 游戏 防沉迷提示'窗口
        time.sleep(5)
        start_wait = time.time()
        while not capture.has_paimon() and time.time()-start_wait < 90:
            logger.debug(f'等待进入游戏界面中, 剩余{90-(time.time()-start_wait)}秒')
            time.sleep(2)
            if self.is_activate():
                self.click_screen((10,10))
            else:
                logger.debug('不是原神登录窗口，暂停点击')
        logger.debug('成功进入游戏')
        capture.activate_window()  # 将游戏窗口置于前台

    def click_login_button(self):
        login_count = 5
        while not self.ocr.find_text_and_click("登录") and login_count > 0:
            login_count -= 1
            time.sleep(5)


if __name__ == '__main__':
    login = LoginControllerBilibili()
    from myutils.os_utils import kill_game
    try:
        kill_game()
    except Exception as e:
        logger.debug(e.args)
    login.open_game()
    from myutils.configutils import AccountConfig
    ci = AccountConfig.get_current_instance()
    account = ci.get("account")
    password = ci.get("password")
    login.user_pwd_input(account, password)