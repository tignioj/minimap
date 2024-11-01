# 秘境
import json
import os.path
import threading
import time

from ultralytics import YOLO
from controller.BaseController import BaseController
from controller.OCRController import OCRController
import cv2
from controller.FightController import FightController
import random
from myutils.configutils import resource_path, FightConfig, DomainConfig
from controller.UIController import TeamUIController
from mylogger.MyLogger3 import MyLogger

logger = MyLogger("domain_controller")

yolo_path = os.path.join(resource_path, "model", "bgi_tree.onnx")
model = YOLO(yolo_path)


# 抛出领取奖励异常，则重试，直到树脂为空
class ClaimTimeoutException(Exception): pass


# 背包已满异常
class NotEnoughSpaceException(Exception): pass


# 抛出这个异常表面则表示超过预期运行时间，不再进行循环
class TotalExecuteTimeoutException(Exception): pass


class NotInDomainException(Exception): pass


# 抛出这个异常表面则表示没有树脂了，不再进行循环
class NoResinException(Exception): pass


class CharacterDeadException(Exception): pass


class DomainController(BaseController):
    def __init__(self, domain_name=None, fight_team=None, domain_timeout=60 * 30):
        super(DomainController, self).__init__()
        self.domain_name = domain_name
        self.ocr = OCRController()
        if fight_team is None or len(fight_team) == 0:
            fight_team = FightConfig.get(FightConfig.KEY_DEFAULT_FIGHT_TEAM)
        self.fight_team = fight_team
        self.fight_controller = FightController(fight_team)
        self.__last_direction = None
        from controller.MapController2 import MapController
        self.map_controller = MapController()
        try:
            domain_timeout = int(domain_timeout)
        except (ValueError, TypeError):
            domain_timeout = DomainConfig.get(DomainConfig.KEY_DOMAIN_LOOP_TIMEOUT, default=30, min_val=1, max_val=600)
        if domain_timeout < 1:
            domain_timeout = 1
        elif domain_timeout > 600:
            domain_timeout = 600

        self.domain_timeout = domain_timeout  # 设置秘境最长执行时间(分钟)
        self.is_character_dead = False

    __domain_list = None

    @staticmethod
    def get_domain_list():
        if DomainController.__domain_list is None:
            with open(os.path.join(resource_path, "domain.json"), "r", encoding="utf8") as f:
                DomainController.__domain_list = json.load(f)
        return DomainController.__domain_list

    @staticmethod
    def detect_tree(img):
        results = model(img, verbose=False)  # verbose=False 关闭日志
        time.sleep(0.1)
        for result in results:
            boxes = result.boxes  # Boxes object for bounding box outputs
            if len(boxes) > 0:
                x1, y1, x2, y2 = boxes.xyxy.numpy()[0]
                return (x1, y1, x2, y2)
                # ret_img = cv2.rectangle(img.copy(), (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 5)
        return None

    def go_left_or_right_by_tree_xyxy(self, img, xyxy):
        if xyxy is not None:
            x1, y1, x2, y2 = xyxy
            ret_img = cv2.rectangle(img.copy(), (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 5)
            ret_img = cv2.resize(ret_img, None, fx=0.4, fy=0.4)
            cv2.namedWindow('show', cv2.WINDOW_NORMAL)
            cv2.moveWindow('show', 0, 0)
            cv2.imshow('show', ret_img)
            cv2.waitKey(2)

            left_width = x1
            right_width = self.gc.w - x2
            self.logger.debug(f"{left_width},{right_width}")
            current_diff = left_width - right_width
            if abs(current_diff) < 15:
                self.logger.debug("GOOD")
                cv2.imwrite('before.jpg', self.gc.get_screenshot())
                time.sleep(0.1)
                # 最后一次计算视角并调整
                xyxy_final = self.detect_tree(img)
                if xyxy_final is not None:
                    x1, y1, x2, y2 = xyxy_final
                    left_width = x1
                    right_width = self.gc.w - x2
                    self.logger.debug(f"final left width: {left_width}, right width:{right_width}")

                self.to_deg(-90, threshold=2)
                time.sleep(0.3)
                cv2.imwrite('after.jpg', self.gc.get_screenshot())
                time.sleep(0.1)
                self.kb_release('a')
                self.kb_release('d')
                time.sleep(0.1)
                cv2.imwrite('ok.jpg', self.gc.get_screenshot())
                cv2.imwrite('ret.jpg', ret_img)
                return True
            else:
                if current_diff < 0:
                    self.logger.debug("向左边走")
                    self.kb_release("d")
                    self.kb_press("a")
                    if abs(current_diff) > 100:
                        time.sleep(0.2)
                    else:
                        time.sleep(0.04)
                    self.kb_release("a")
                    self.__last_direction = 'a'
                else:
                    self.logger.debug("向右边走")
                    self.kb_release("a")
                    self.kb_press("d")
                    if abs(current_diff) > 100:
                        time.sleep(0.2)
                    else:
                        time.sleep(0.04)
                    self.kb_release('d')
                    self.__last_direction = 'd'

    def enter_domain(self):
        # 1. 点击秘境名称
        # self.ocr.find_text_and_click(domain)
        self.kb_press_and_release('f')
        # 2. 点击单人挑战
        # self.ocr.find_text_and_click('单人挑战')
        self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)
        time.sleep(2)
        if self.ocr.is_text_in_screen("仍要挑战"):
            self.ocr.find_text_and_click("取消")
            time.sleep(1)
            self.click_ui_close_button()
            raise NoResinException("你已经没有树脂了，无需进入秘境")
        # 3. 确认队伍界面点击开始挑战
        # self.ocr.find_text_and_click('开始挑战')
        self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)
        time.sleep(1)
        # 4. 等到直到出现秘境介绍
        time.sleep(4)

    def go_to_key_f(self):
        """
        前往钥匙处开启挑战
        :return:
        """
        self.logger.debug("准备走到秘境开启的齿轮。在此之前判断是否处于战斗结束状态")
        if self.ocr.is_text_in_screen("仍要挑战"): raise NoResinException("没有树脂了")

        if self.ocr.is_text_in_screen("自动退出"):
            self.logger.debug("战斗已经结束,无需开启战斗")
            return
        start_wait = time.time()
        while True:
            if self.gc.has_gear():
                self.logger.debug("检测到齿轮，开始挑战")
                break
            if time.time() - start_wait > 20:
                self.logger.error("超时未检测到地脉异常文, 无法开启战斗")
                raise TimeoutError("超时未检测到地脉异常, 无法开启战斗")
            if self.ocr.is_text_in_screen("地脉异常"):
                time.sleep(1)
                self.logger.debug("点击任意位置关闭")
                self.kb_press_and_release(self.Key.esc)
                time.sleep(0.5)
                break
        # 6. 疯狂f往前走直到出现齿轮
        self.kb_press('w')
        start_wait = time.time()
        while True:
            # 模板检测倒计时图标
            if time.time() - start_wait > 12:
                msg = "超时未检测到齿轮，无法开启战斗"
                self.logger.error(msg)
                raise TimeoutError(msg)
            if self.gc.has_gear():
                self.logger.debug("检测到之轮，开始战斗")
                self.kb_release("w")
                self.kb_press_and_release('f')
                break
            time.sleep(0.02)
        self.logger.debug('开始战斗')

        def callback():
            self.is_character_dead = True

        self.fight_controller.start_fighting(stop_on_no_enemy=False,
                                             character_dead_callback=callback)
        # 7. 检测战斗结束
        start = time.time()
        while time.time() - start < 300:
            self.logger.debug(f'等待战斗结束{300 - int(time.time() - start)}')
            if self.is_character_dead:
                raise CharacterDeadException("死亡后被传送到了七天神像, 结束秘境")
            if self.gc.has_paimon(delay=False):
                self.logger.debug("检测到左上角的派蒙，表示不在秘境中，结束秘境")
                self.fight_controller.stop_fighting()
                raise NotInDomainException("检测到左上角的派蒙，表示不在秘境中，结束秘境")
            if self.ocr.is_text_in_screen("挑战达成", "退出"): break
            time.sleep(5)
        # 8. 秘境结束
        self.logger.debug('结束战斗')
        self.fight_controller.stop_fighting()

    def to_deg(self, degree, threshold=10):
        """
        这里重写了BaseController的转视角方法，此方法转向速度更柔和
        将当前视角朝向转至多少度
        :param degree:
        :param threshold:
        :return:
        """
        if degree is None: return
        if threshold is None or threshold < 2: threshold = 2
        start = time.time()
        while True:
            if time.time() - start > 10: break  # 避免超过10秒
            # 设置confidence=0时，保证返回的一定是GIA值，因为秘境里面减背景法完全不可用
            current_rotation = self.tracker.get_rotation(use_alpha=False, confidence=0)
            # 假设要求转向到45，获取的是60，则 degree - current_rotation = -15
            # 假设要求转向到45，获取的是10则 degree - current_rotation = 30
            if current_rotation is None:
                self.logger.error("获取视角失败！")
                continue
            diff = current_rotation - degree
            # 求方向
            s = abs(diff)
            if s < threshold: return

            direction = diff / abs(diff)
            if degree * current_rotation > 0:  # 同向
                # 直接做差
                s = abs(diff)
                direction = -direction
            else:  # 异向
                # 做差后得到s， 判断s是否大于180, 大于180则距离取360-s
                # 求距离
                if abs(diff) > 180:
                    s = 360 - abs(diff)
                else:
                    s = abs(diff)
                    direction = -direction
            if s < threshold: return
            max_rate = 200
            # s = s * 2
            if s > max_rate: s = max_rate
            # win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -int(direction * s), 0, 0, 0)
            self.camera_chage(-direction * s, 0, 0)

    def exit_domain(self):
        self.logger.debug("退出秘境")
        start_exit_time = time.time()
        while not self.gc.has_paimon(delay=False):
            if time.time() - start_exit_time > 30: raise Exception("超时未能退出秘境")
            self.kb_press_and_release(self.Key.esc)
            time.sleep(1)
            self.ocr.find_text_and_click("确认")
            time.sleep(1)
            self.ocr.find_text_and_click("退出秘境")
            time.sleep(1)
        self.logger.debug("成功退出秘境")

    def ocr_and_click_reward(self):
        ocr_result = self.ocr.get_ocr_result()

        # 如果有浓缩树脂，但是没有原粹树脂，此时文字仍然有“原粹树脂数量不足”,因此在判断"数量不足"前，先判断是否有使用树脂的按钮
        self.logger.debug("ocr检测中")
        for result in ocr_result:
            self.logger.debug(f'ocr:{result.text}')
            if result.text in "使用浓缩树脂":
                self.logger.debug("点击使用浓缩树脂")
                self.ocr.click_ocr_result(result)
                time.sleep(3)
                # 点击确认
                # 可能会抛出超时异常
                if self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10):
                    time.sleep(2)
                    if self.ocr.is_text_in_screen("仍要挑战"): raise NoResinException("没有树脂了")
                return True
            elif result.text in "使用原粹树脂":
                self.logger.debug("点击使用原粹树脂")
                self.ocr.click_ocr_result(result)
                time.sleep(3)
                # 点击确认
                # 可能会抛出超时异常
                if self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10):
                    time.sleep(2)
                    if self.ocr.is_text_in_screen("仍要挑战"): raise NoResinException("没有树脂了")
                return True

        # 如果没有上面检测的两个按钮，且出现数量不足，则表明树脂耗尽
        for result in ocr_result:
            if "数量不足" in result.text:
                raise NoResinException("没有树脂了，结束秘境")
            elif "仍要挑战" in result.text:
                self.ocr.find_text_and_click("取消")
                raise NoResinException("没有树脂了，结束秘境")
            elif result.text in "继续挑战":
                self.logger.debug("点击继续挑战")
                self.ocr.click_ocr_result(result)
                time.sleep(3)
                if self.ocr.is_text_in_screen("仍要挑战"):
                    self.ocr.find_text_and_click("取消")
                    raise NoResinException("没有树脂了，结束秘境")
                return True
        return False

    def go_to_claim_reward(self):
        """
        :return:
        """
        # model = YOLO('weights/best.pt')
        start_process = time.time()
        time.sleep(0.5)
        self.ms_press(self.Button.middle)
        self.ms_release(self.Button.middle)
        time.sleep(0.1)

        tree_found_last_time = None
        while True:
            if time.time() - start_process > 60:
                self.logger.error("对准树超时！")
                raise ClaimTimeoutException("对准树超时!")
            self.to_deg(-90, threshold=2)
            # time.sleep(0.1)  # 等待视角稳定
            sc = self.gc.get_screenshot(use_alpha=False)
            # results = model(sc, verbose=False)  # verbose=False 关闭日志
            xyxy = self.detect_tree(sc)
            if xyxy is None:
                ok = False
                self.to_deg(-90, threshold=2)
                self.kb_release("w")
                self.kb_release("s")
                self.kb_release("a")
                self.kb_release("d")
                if self.__last_direction is None:
                    random_direction = random.choice("wsad")
                    self.logger.debug(f"未找到树，随机方向{random_direction}调整中...")
                    self.kb_press(random_direction)
                    time.sleep(0.2)
                    self.kb_release(random_direction)
                else:
                    if tree_found_last_time is not None and time.time() - tree_found_last_time > 8:
                        self.logger.debug(
                            f"按照上次的方向{self.__last_direction}调整了8秒后仍旧没有找到树，重新进入随机模式")
                        self.__last_direction = None  # 超过5秒仍然没找到树，清空上次发现的方向
                        continue
                    self.logger.debug(f"未找到树，按照上次的方向{self.__last_direction}调整中...")
                    self.kb_press(self.__last_direction)
                    time.sleep(0.1)
                    self.kb_release(self.__last_direction)
            else:
                tree_found_last_time = time.time()
                ok = self.go_left_or_right_by_tree_xyxy(sc, xyxy)
                self.kb_release('a')
                self.kb_release('d')
            # time.sleep(0.04)
            # self.kb_release('a')
            # self.kb_release('d')
            if ok: break

        self.logger.debug("已经对准，冲向领奖台中")

        self.kb_press('w')
        self.kb_press(self.Key.shift)
        # self.kb_release(self.Key.shift)
        start_reward = time.time()
        # 检测到树脂图标就停下
        has_resin = False
        while time.time() - start_reward < 20:
            self.kb_press_and_release('f')
            if len(self.gc.get_icon_position(self.gc.icon_origin_resin)) > 0:
                has_resin = True
                self.kb_release(self.Key.shift)
                break
            time.sleep(0.05)
        self.logger.debug(f"是否检测到树脂图标：{has_resin}")

        self.logger.debug("开始处理点击领取奖励逻辑")
        self.kb_release('w')
        self.kb_release(self.Key.shift)
        time.sleep(1)
        claim_ok = self.ocr_and_click_reward()
        return claim_ok

    def re_enter_domain(self):
        self.logger.debug("正在尝试重新进入秘境, 先取七天神像")
        # 重试机制：先出秘境再回来
        self.map_controller.go_to_seven_anemo_for_revive()
        self.logger.debug("正在返回秘境")
        self.teleport_to_domain(self.domain_name)
        self.logger.debug("正在进入秘境")
        self.enter_domain()  # 可能会抛出超时异常

    def loop_domain(self):
        """
        循环执行秘境直到超时或者树脂耗尽
        :return:
        """
        start_domain_time = time.time()
        timeout_second = self.domain_timeout * 60  # 分钟转换成秒
        while True:
            try:
                if time.time() - start_domain_time > timeout_second: raise TotalExecuteTimeoutException(
                    "秘境执行总时间超时")
                # 开启挑战
                if self.gc.has_paimon(delay=False): raise NotInDomainException("不在秘境，结束")
                # 前往钥匙处开启挑战
                self.go_to_key_f()
                time.sleep(3)
                # 领取奖励
                if not self.go_to_claim_reward(): raise ClaimTimeoutException("未能成功点击领取奖励，重试")
                time.sleep(2)  # 等待2秒后进入下一轮，避免过快检测到“自动退出”
                self.logger.debug("开启下一轮秘境")
            except (ClaimTimeoutException, TimeoutError) as e:
                self.logger.error(f"领取奖励超时异常:{e.args}")
                # 尝试检测是否有小齿轮，如果有，说明背包已满
                time.sleep(5)  # 等待文字消失
                if self.gc.has_key(): raise NotEnoughSpaceException("背包已经满")
                self.re_enter_domain()
            except NotInDomainException as e:
                self.logger.error(f"不在秘境异常:{e.args}")
                raise e
            except NoResinException as e:
                self.logger.error(f"树脂耗尽异常:{e.args}")
                raise e
            except CharacterDeadException as e:
                self.logger.error(f"角色死亡异常:{e.args}")
                self.re_enter_domain()

    def teleport_to_domain(self, domain_name):
        domain_list = DomainController.get_domain_list()
        if domain_list is None:
            self.logger.error("秘境列表为空！")
            raise Exception("秘境列表为空！")
        for domain in domain_list:
            if domain_name == domain.get("name"):
                country = domain.get("country")
                pos = domain.get("position")
                self.logger.debug(f"正在传送:{domain}")
                self.map_controller.teleport(pos, country, waypoint_name=domain_name, start_teleport_time=time.time())
        # 等待派蒙出现
        start_wait = time.time()
        while not self.gc.has_paimon(delay=False) and time.time() - start_wait < 15:
            self.logger.debug("等待派蒙中")
            time.sleep(1)

        # 边前进边按f直到派蒙消失，表示打开秘境入口
        start_wait = time.time()
        while self.gc.has_paimon(delay=False) and time.time() - start_wait < 10:
            self.kb_press('w')
            time.sleep(0.02)
            self.kb_press_and_release('f')
            time.sleep(0.02)
        self.kb_release('w')

    def change_fight_team(self):
        tuic = TeamUIController()
        tuic.switch_team(self.fight_team)
        tuic.navigation_to_world_page()

    @staticmethod
    def one_key_run_domain(domain_name=None, fight_team=None, time_out=None):
        """
        一键运行秘境
        :param domain_name: 秘境名称
        :param time_out: 最长执行时间（秒）
        :return:
        """
        # 传送到秘境附近
        dm = None
        try:
            dm = DomainController(domain_name=domain_name, fight_team=fight_team, domain_timeout=time_out)
            # 切换队伍
            dm.change_fight_team()
            # 进入秘境
            dm.teleport_to_domain(domain_name)
            # 执行秘境直到体力耗尽
            dm.enter_domain()
            dm.loop_domain()
        except Exception as e:
            logger.error(f"因异常结束秘境:{e.args}")
            raise e
        finally:
            try:
                if dm is not None: dm.exit_domain()
            except Exception as e:
                logger.error(f"超时未能退出秘境{e.args}")


def test_claim_reward():
    name = '罪祸的终末'
    fight_team = '纳西妲_芙宁娜_钟离_那维莱特_(草龙芙中).txt'
    dm = DomainController(domain_name=name, fight_team=fight_team)
    while True:
        dm.go_to_claim_reward()
        time.sleep(3)
        dm.kb_release('w')
        dm.kb_press('s')
        dm.kb_release(dm.Key.shift)
        time.sleep(3)
        dm.kb_release("s")
        dm.kb_release(dm.Key.shift)
        d = random.choice("wsad")
        deg = random.randint(-160, 160)
        dm.to_deg(deg)
        dm.kb_press(d)
        time.sleep(0.3)
        dm.kb_press(d)
        dm.kb_release('w')
        dm.kb_release('s')
        dm.kb_release('a')
        dm.kb_release('d')


if __name__ == '__main__':
    # name = '罪祸的终末'
    name = '虹灵的净土'
    # name = '震雷连山密宫'
    fight_team = '纳西妲_芙宁娜_钟离_那维莱特_(草龙芙中).txt'
    # fight_team = '那维莱特_莱依拉_迪希雅_行秋_(龙莱迪行).txt'
    # fight_team = '芙宁娜_行秋_莱依拉_流浪者_(芙行莱流).txt'
    # l = DomainController.get_domain_list()
    # test_claim_reward()
    # print(dm.ocr.is_text_in_screen("自动退出"))
    # test_claim_reward()
    DomainController.one_key_run_domain(domain_name=name, fight_team=fight_team)
    # dm = DomainController(domain_name=name,fight_team=fight_team)
    # dm.enter_domain()
    # dm.loop_domain()
    # dm.go_to_claim_reward()
    # DomainController().exit_domain()
