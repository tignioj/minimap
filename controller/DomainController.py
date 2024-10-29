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
from myutils.configutils import resource_path, FightConfig
from controller.UIController import TeamUIController

yolo_path = os.path.join(resource_path, "model", "bgi_tree.onnx")
model = YOLO(yolo_path)


class ClaimTimeoutException(Exception): pass


class NotInDomainException(Exception): pass


class NoResinException(Exception): pass


class DomainController(BaseController):
    def __init__(self, domain_name=None, fight_team=None, domain_timeout=60*30):
        super(DomainController, self).__init__()
        self.domain_name = domain_name
        self.ocr = OCRController()
        if fight_team is None or len(fight_team)==0:
            fight_team = FightConfig.get(FightConfig.KEY_DEFAULT_FIGHT_TEAM)
        self.fight_team = fight_team
        self.fight_controller = FightController(fight_team)
        self.__last_direction = None
        from myutils.configutils import resource_path
        from controller.MapController2 import MapController
        self.map_controller = MapController()
        with open(os.path.join(resource_path, "domain.json"), "r", encoding="utf8") as f:
            self.domain_list = json.load(f)
        self.domain_timeout = domain_timeout  # 设置秘境最长执行时间为30分钟
        self.is_domain_end = False
        self.is_character_dead = False

    def __process_results(self, img, results):
        # Process results list
        self.kb_release('a')
        self.kb_release('d')
        time.sleep(0.1)
        for result in results:
            boxes = result.boxes  # Boxes object for bounding box outputs
            masks = result.masks  # Masks object for segmentation masks outputs
            keypoints = result.keypoints  # Keypoints object for pose outputs
            probs = result.probs  # Probs object for classification outputs
            obb = result.obb  # Oriented boxes object for OBB outputs
            # result.show()  # display to screen
            # self.logger.debug(boxes)
            if len(boxes) > 0:
                x1, y1, x2, y2 = boxes.xyxy.numpy()[0]
                ret_img = cv2.rectangle(img.copy(), (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 5)
                cv2.namedWindow('show', cv2.WINDOW_NORMAL)
                cv2.moveWindow('show', 0, 0)
                ret_img = cv2.resize(ret_img, None, fx=0.3, fy=0.3)
                cv2.imshow('show', ret_img)
                cv2.waitKey(2)
                left_width = x1
                right_width = self.gc.w - x2
                self.logger.debug(f"{left_width},{right_width}")
                current_diff = left_width - right_width
                if abs(current_diff) < 15:
                    self.logger.debug("GOOD")
                    cv2.imwrite('before.jpg', self.gc.get_screenshot())
                    time.sleep(0.3)
                    self.to_degree(-90, threshold=2, inverse_alpha=False)
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
                        self.__last_direction = 'a'
                    else:
                        self.logger.debug("向右边走")
                        self.kb_release("a")
                        self.kb_press("d")
                        self.__last_direction = 'd'
            else:
                self.to_degree(-90, threshold=2, inverse_alpha=False)
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
                    self.logger.debug(f"未找到树，按照上次的方向{self.__last_direction}调整中...")
                    self.kb_press(self.__last_direction)
                    time.sleep(0.2)
                    self.kb_release(self.__last_direction)

    def enter_domain(self):
        # 1. 点击秘境名称
        # self.ocr.find_text_and_click(domain)
        self.kb_press_and_release('f')
        # 2. 点击单人挑战
        # self.ocr.find_text_and_click('单人挑战')
        self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)

        time.sleep(1)
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
        if self.ocr.is_text_in_screen("自动退出"):
            self.logger.debug("战斗已经结束,无需开启战斗")
            return
        start_wait = time.time()
        while True:
            if time.time() - start_wait > 20:
                self.logger.error("超时未检测到地脉异常文字，无法开启战斗")
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
        while time.time() - start < 300 and not self.is_domain_end:
            self.logger.debug(f'等待战斗结束{300 - int(time.time() - start)}')
            if self.is_character_dead:
                self.logger.error("秘境中角色死亡，结束秘境")
                self.map_controller.go_to_seven_anemo_for_revive()
                raise NotInDomainException("死亡后被传送到了七天神像, 结束秘境")
            if self.gc.has_paimon(delay=False):
                self.logger.debug("检测到左上角的派蒙，表示不在秘境中，结束秘境")
                self.fight_controller.stop_fighting()
                raise NotInDomainException("检测到左上角的派蒙，表示不在秘境中，结束秘境")
            if self.ocr.is_text_in_screen("挑战达成", "自动退出"): break
            time.sleep(1)
        # 8. 秘境结束
        self.logger.debug('结束战斗')
        self.fight_controller.stop_fighting()

    def to_degree(self, degree, threshold=10, detected_paimon=True, inverse_alpha=True):
        """
        这里重写了BaseController的转视角方法，此方法转向速度更柔和
        将当前视角朝向转至多少度
        :param degree:
        :param threshold:
        :param inverse_alpha:  秘境中要关掉alpha反色否则无法获取角度
        :return:
        """
        if degree is None: return
        if threshold is None or threshold < 2: threshold = 2
        start = time.time()
        while True:
            if time.time() - start > 10: break  # 避免超过10秒
            current_rotation = self.tracker.get_rotation(inverse_alpha=inverse_alpha)
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
        while not self.ocr.is_text_in_screen("退出秘境"):
            if self.gc.has_paimon(delay=False):
                self.logger.debug("已经在大世界，无需退出秘境")
                break
            if time.time() - start_exit_time > 20: raise Exception("超时未能退出秘境")
            self.kb_press_and_release(self.Key.esc)
            time.sleep(3)
        self.ocr.find_text_and_click("确认")

    def ocr_and_click_reward(self):
        ocr_result = self.ocr.get_ocr_result()
        self.logger.debug("ocr检测中")
        claim_ok = False
        for result in ocr_result:
            self.logger.debug(f'ocr:{result.text}')
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
                claim_ok = True

            elif result.text in "使用浓缩树脂":
                self.logger.debug("点击使用浓缩树脂")
                self.ocr.click_ocr_result(result)
                time.sleep(3)
                # 点击确认
                # 可能会抛出超时异常
                self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)
                claim_ok = True
                break
            elif result.text in "使用原粹树脂":
                self.logger.debug("点击使用原粹树脂")
                self.ocr.click_ocr_result(result)
                time.sleep(3)
                # 点击确认
                # 可能会抛出超时异常
                self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)
                claim_ok = True
        return claim_ok



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
        while True:
            if time.time() - start_process > 60:
                self.logger.error("对准树超时！")
                raise ClaimTimeoutException("对准树超时!")
            self.to_degree(-90, threshold=2, inverse_alpha=False)
            sc = self.gc.get_screenshot(use_alpha=False)
            results = model(sc, verbose=False)  # verbose=False 关闭日志
            ok = self.__process_results(sc, results)
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
        time.sleep(1)
        claim_ok = self.ocr_and_click_reward()
        return claim_ok

    def loop_domain(self):
        start_domain_time = time.time()
        try:
            while not self.is_domain_end:
                if time.time() - start_domain_time > self.domain_timeout:
                    self.logger.error("超时结束秘境")
                # 开启挑战
                if self.gc.has_paimon(delay=False):
                    self.logger.debug("不是秘境，结束")
                    break
                # 前往钥匙处开启挑战
                self.go_to_key_f()
                time.sleep(3)
                # 领取奖励
                if not self.go_to_claim_reward():
                    self.logger.error("未能成功点击领取奖励，秘境结束")
                    break
                time.sleep(3)
        except (ClaimTimeoutException, TimeoutError) as e:
            self.logger.error(f"超时异常:{e.args}")
            raise e
        except NotInDomainException as e:
            self.logger.error(f"不在秘境异常:{e.args}")
            raise e
        except NoResinException as e:
            self.logger.error(f"树脂耗尽异常:{e.args}")
            raise e
        self.logger.debug("秘境结束")

    def teleport_to_domain(self, domain_name):
        if self.domain_list is None:
            self.logger.error("秘境列表为空！")
        for domain in self.domain_list:
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
    def one_key_run_domain(domain_name=None,fight_team=None,time_out=1200):
        """
        一键运行秘境
        :param domain_name: 秘境名称
        :param time_out: 最长执行时间（秒）
        :return:
        """
        dm = DomainController(domain_name=domain_name,fight_team=fight_team, domain_timeout=time_out)
        # 切换队伍
        dm.change_fight_team()
        # 传送到秘境附近
        dm.teleport_to_domain(domain_name)
        # 进入秘境
        dm.enter_domain()
        # 执行秘境直到体力耗尽
        try:
            dm.loop_domain()
        except Exception as e:
            dm.logger.error(f"因异常结束秘境:{e.args}")
        finally:
            try:
                dm.exit_domain()
            except Exception as e:
                dm.logger.error(f"超时未能退出秘境{e.args}")

def test_claim_reward():
    name = '罪祸的终末'
    fight_team = '纳西妲_芙宁娜_钟离_那维莱特_(草龙芙中).txt'
    dm = DomainController(domain_name=name, fight_team=fight_team)
    while True:
        dm.go_to_claim_reward()
        time.sleep(4)
        dm.kb_release('w')
        dm.kb_press('s')
        dm.kb_release(dm.Key.shift)
        time.sleep(4)
        dm.kb_release("s")
        dm.kb_release(dm.Key.shift)
        d = random.choice("wsad")
        deg = random.randint(-160, 160)
        dm.to_degree(deg, inverse_alpha=False)
        dm.kb_press(d)
        time.sleep(1)
        dm.kb_press(d)


if __name__ == '__main__':
    # name = '罪祸的终末'
    name = '虹灵的净土'
    fight_team = '纳西妲_芙宁娜_钟离_那维莱特_(草龙芙中).txt'
    # print(dm.ocr.is_text_in_screen("自动退出"))
    # test()
    DomainController.one_key_run_domain(domain_name=name, fight_team=fight_team)
    # DomainController().exit_domain()
