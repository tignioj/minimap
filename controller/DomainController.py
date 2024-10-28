# 秘境
import os.path
import threading
import time

from ultralytics import YOLO
from controller.BaseController import BaseController
from controller.OCRController import OCRController
import cv2
from controller.FightController import FightController
import random
from myutils.configutils import resource_path
yolo_path = os.path.join(resource_path, "model", "bgi_tree.onnx")
model = YOLO(yolo_path)


class DomainController(BaseController):
    def __init__(self, domain_name=None):
        super(DomainController, self).__init__()
        # self.domain_name = domain_name
        self.ocr = OCRController()
        self.fight_controller = FightController("纳西妲_芙宁娜_钟离_那维莱特_(草龙芙中).txt")
        self.__last_direction = None

    def __process_results(self,img, results):
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
                ret_img = cv2.resize(ret_img, None, fx=0.5, fy=0.5)
                cv2.imshow('show', ret_img)
                cv2.waitKey(2)
                left_width = x1
                right_width = self.gc.w - x2
                self.logger.debug(f"{left_width},{right_width}")
                current_diff = left_width - right_width
                if abs(current_diff) < 15:
                    self.logger.debug("GOOD")
                    # self.unlock_view()
                    cv2.imwrite('before.jpg',self.gc.get_screenshot())
                    time.sleep(0.5)
                    self.to_degree(-90, threshold=2, inverse_alpha=False)
                    time.sleep(0.5)
                    cv2.imwrite('after.jpg',self.gc.get_screenshot())
                    time.sleep(0.3)
                    self.kb_release('a')
                    self.kb_release('d')
                    time.sleep(0.5)
                    cv2.imwrite('ok.jpg',self.gc.get_screenshot())
                    cv2.imwrite('ret.jpg',ret_img)
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
        self.click_if_appear(self.gc.icon_message_box_button_confirm,timeout=10)

        time.sleep(2)
        # 3. 确认队伍界面点击开始挑战
        # self.ocr.find_text_and_click('开始挑战')
        self.click_if_appear(self.gc.icon_message_box_button_confirm,timeout=10)
        time.sleep(2)

        # 4. 等到直到出现秘境介绍

    def go_to_key_f(self):
        if self.ocr.is_text_in_screen("自动退出"):
            self.logger.debug("战斗已经结束,无需开启战斗")
            return
        start_wait = time.time()
        while True:
            if time.time() - start_wait > 5: break
            if self.ocr.is_text_in_screen("地脉异常"):
                time.sleep(1)
                self.logger.debug("点击任意位置关闭")
                self.kb_press_and_release(self.Key.esc)
                break
        # 6. 疯狂f往前走直到出现齿轮
        self.kb_press('w')
        while True:
            if self.ocr.is_text_in_screen("击败"): break
            self.kb_press_and_release('f')
        self.kb_release('w')
        self.logger.debug('开始战斗')
        self.fight_controller.start_fighting()
        # 7. 检测战斗结束
        start = time.time()
        while time.time() - start < 300:
            self.logger.debug(f'等待战斗结束{300 - int(time.time() - start)}')
            if self.gc.has_paimon(delay=False):
                self.logger.debug("您已退出秘境，肯能是死亡后被传送到了七天神像")
                raise Exception("结束秘境")
                break
            if self.ocr.is_text_in_screen("挑战达成", "自动退出"): break
            time.sleep(1)
        # 8. 秘境结束
        self.logger.debug('结束战斗')
        self.fight_controller.stop_fighting()

    locking_view = False
    def unlock_view(self):
        self.logger.debug("解锁视角")
        BaseController.locking_view = False
    def to_degree(self, degree, threshold=10, detected_paimon=True, inverse_alpha=True):
        """
        将当前视角朝向转至多少度
        :param degree:
        :param threshold:
        :param inverse_alpha:  秘境中要关掉alpha反色否则无法获取角度
        :return:
        """
        if degree is None: return
        if threshold is None or threshold < 2: threshold=2
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
            # self.logger.debug(f"current: {current_rotation}, target{degree},diff{diff}, 转向:{direction}, 转动距离:{s}")
            if s < threshold: return
            max_rate = 200
            # s = s * 2
            if s > max_rate: s = max_rate
            # win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -int(direction * s), 0, 0, 0)
            self.camera_chage(-direction*s, 0,0)
    def lock_view(self):
        if DomainController.locking_view:
            self.logger.error("不要重复锁定视角")
            return
        DomainController.locking_view = True
        def lock_thread_method():
            self.ms_click(self.Button.middle)
            self.ms_release(self.Button.middle)
            start_lock_time = time.time()
            while DomainController.locking_view and time.time() - start_lock_time < 120:
                if BaseController.stop_listen: return
                self.to_degree(-90, 2, detected_paimon=False, inverse_alpha=False)
        t = threading.Thread(target=lock_thread_method)
        t.setDaemon(True)
        t.start()

    def go_to_claim_reward(self):
        """
        :return:
        """
        # model = YOLO('weights/best.pt')
        # self.lock_view()
        start_process = time.time()
        time.sleep(0.5)
        self.ms_press(self.Button.middle)
        self.ms_release(self.Button.middle)
        time.sleep(0.1)
        while True:
            if time.time() - start_process > 60:
                self.logger.error("对准树超时！")
            self.to_degree(-90,threshold=2, inverse_alpha=False)
            sc = self.gc.get_screenshot(use_alpha=False)
            results = model(sc,verbose=False)  # verbose=False 关闭日志
            ok = self.__process_results(sc,results)
            if ok: break
        self.logger.debug("已经对准，冲向领奖台中")
        self.kb_press('w')
        self.kb_press(self.Key.shift)
        start_reward = time.time()
        while True:
            if time.time() - start_reward > 60: break
            self.kb_press_and_release('f')
            ocr_result = self.ocr.get_ocr_result()
            self.logger.debug("ocr检测中")
            for result in ocr_result:
                # self.logger.debug(f'ocr:{result.text}')
                if "仍要挑战" in result.text or "数量不足" in result.text:
                    self.kb_release(self.Key.shift)
                    self.ocr.find_text_and_click("取消")
                    raise Exception("没有树脂了，结束秘境")
                elif result.text in "继续挑战":
                    self.logger.debug("点击继续挑战")
                    self.ocr.click_ocr_result(result)
                    time.sleep(3)
                    if self.ocr.is_text_in_screen("仍要挑战"):
                        self.ocr.find_text_and_click("取消")
                        raise Exception("没有树脂了，结束秘境")
                    return
                elif result.text in "使用浓缩树脂":
                    self.logger.debug("点击使用浓缩树脂")
                    self.ocr.click_ocr_result(result)
                    time.sleep(3)
                    self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)
                    return
                elif result.text in "使用原粹树脂":
                    self.logger.debug("点击使用原粹树脂")
                    self.ocr.click_ocr_result(result)
                    time.sleep(3)
                    self.click_if_appear(self.gc.icon_message_box_button_confirm, timeout=10)
                    return
            time.sleep(0.05)

    def back(self):
        self.kb_release('w')
        self.kb_press('s')
        self.kb_release(self.Key.shift)

    def loop_domain(self):
        # 检测当前处于什么阶段
        # 如果没有派蒙，说明在秘境内
        if self.gc.has_paimon(delay=False):
            dm.enter_domain()
        while True:
            try:
                # 开启挑战
                if self.gc.has_paimon(delay=False):
                    self.logger.debug("不是秘境，结束")
                    break
                dm.go_to_key_f()
                time.sleep(3)
                dm.go_to_claim_reward()
                time.sleep(3)
            except Exception as e:
                self.logger.error(f"检测到异常:{e.args}")
                break
        self.logger.debug("秘境结束")

def test():
    while True:
        dm.go_to_claim_reward()
        time.sleep(4)
        dm.back()
        time.sleep(4)
        dm.kb_release("s")
        dm.kb_release(dm.Key.shift)
        d = random.choice("wsad")
        deg = random.randint(-160,160)
        dm.to_degree(deg, inverse_alpha=False)
        dm.kb_press(d)
        time.sleep(1)
        dm.kb_press(d)


if __name__ == '__main__':
    # name = '罪祸的终末'
    dm = DomainController()
    dm.loop_domain()
    # print(dm.ocr.is_text_in_screen("自动退出"))
    # test()


