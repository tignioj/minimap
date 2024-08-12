import time
from capture.capture_factory import capture
from controller.BaseController import BaseController
from server.ServerAPI import get_ocr_result
# ocr_obj = PaddleOCR(use_gpu=True)
# gc = GenShinCapture()
# def get_ocr_result():
#     return ocr_obj.ocr(gc.get_screenshot())

# @cache
class OCRController(BaseController):
    def __init__(self, debug_enable=False):
        self.debug_enable = debug_enable
        self.gc = capture
        super().__init__(debug_enable, self.gc)
        self.ocr_result = None

        self.update_timer = 0
        self.UPDATE_TIME_SLEEP_TIME = 0.2  # 0.2秒刷新一次
        self.update_ocr_result()

    def get_ocr_result(self):
        self.update_ocr_result()
        return self.ocr_result

    def update_ocr_result(self):
        """
        OCR是一比巨大的开销，添加时间间隔防止调用卡顿
        :return:
        """
        if time.time() - self.update_timer > self.UPDATE_TIME_SLEEP_TIME:
            self.ocr_result = get_ocr_result()
            self.update_timer = time.time()

    def click(self, x, y):
        pos = self.gc.get_screen_position((x, y))
        self.log((x, y), "->", pos)
        self.set_ms_position(pos)
        self.mouse_left_click()

    def get_line_center(self, rect):
        """
        获取行文字的中心点坐标
        :param rect:
        :return:
        """
        left_top = rect[0]
        right_top = rect[1]
        right_bottom = rect[2]
        left_bottom = rect[3]
        # print(left_top, right_top, right_bottom, left_bottom)

        center_x = (left_top[0] + right_top[0]) / 2
        center_y = (left_top[1] + left_bottom[1]) / 2
        return center_x, center_y

    def find_match_text(self, target_text, match_all=False):
        if self.stop_listen or target_text is None: return
        self.log(f"正在查找'{target_text}'")
        # img = self.gc.get_screenshot()
        result = self.get_ocr_result()
        match_texts = []
        try:
            if result is not None:
                for idx in range(len(result)):
                    res = result[idx]
                    for line in res:
                        if target_text in line[1][0]:
                            if match_all and target_text != line[1][0]: continue
                            match_texts.append(line)
        except TypeError as e:
            self.logger.error(e)
        return match_texts
    def find_text_and_click(self, target_text, match_all=False, index=0, click_all=False):
        """
        找到屏幕中匹配的文字并点击
        :param target_text:
        :param match_all: 是否完全匹配文本
        :param index: 出现多个选项时候，点击的索引
        :param click_all: 点击所有匹配的文本，此选项优先于index
        :return:
        """
        match_texts = self.find_match_text(target_text, match_all)

        if match_texts is None: return False

        l = len(match_texts)
        if index < 0 or l == 0: return False

        self.log(f"共发现{l}个匹配的文本")
        if index >= l:
            self.log('你选择的下标超过了匹配数量，自动设置为最后一个')
            index = l - 1

        if click_all:
            self.log(f"点击所有匹配的文本")
            for match in match_texts:
                x, y = self.get_line_center(match[0])
                self.click(x, y)
                self.log(f"已经执行点击'{target_text}'操作")
        else:
            self.log(f"点击第{index + 1}个匹配的文本")
            match = match_texts[index]
            x, y = self.get_line_center(match[0])
            self.click(x, y)
            self.log(f"已经执行点击'{target_text}'操作")
        return True


    def is_text_in_screen(self, *args):
        if self.stop_listen or args is None: return
        self.log(f"在屏幕中查找{args}")
        result = self.get_ocr_result()
        if result is None: return False
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                # if target_text in line[1][0]:
                for arg in args:
                    try:
                        if arg is None: return False
                        if arg in line[1][0]:
                            self.log("屏幕上出现文本{}, 原文是{}:".format(arg, line[1][0]))
                            return True
                    except TypeError as e:
                        self.log(line, e)
                        return False
        self.log(f"没有找到{args}")
        return False


if __name__ == '__main__':
    # cv2.imshow('sc', gc.get_screenshot())
    # cv2.waitKey(0)
    ocr = OCRController(debug_enable=True)
    # ocr.is_text_in_screen('探索度')
    # ocr.find_text_and_click("锚点")
    # ocr.find_text_and_click("七天神像")
    # ocr.find_text_and_click("点击空白")
    # ocr.find_text_and_click("传送")
    # ocr.find_text_and_click("钓鱼")
    # ocr.find_text_and_click("UID:")
    # print(ocr.is_text_in_screen("传送锚点"))
    # print(ocr.find_text_and_click("传送锚点"))
    # print(ocr.is_text_in_screen("蔷薇"))
    while True:
        start = time.time()
        ocr.update_ocr_result()
        result = ocr.is_text_in_screen("探索度")
        # print(result)
        print("cost{}".format(time.time() - start))


