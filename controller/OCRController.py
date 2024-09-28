import time
from typing import List

from capture.capture_factory import capture
from controller.BaseController import BaseController
from matchmap.minimap_interface import MinimapInterface
# ocr_obj = PaddleOCR(use_gpu=True)
# gc = GenShinCapture()
# def get_ocr_result():
#     return ocr_obj.ocr(gc.get_screenshot())

class OCRResult:
    def __init__(self, corner,text,percent):
        self.corner = corner
        self.text = text
        self.percent = percent
        self.center = self.get_line_center(corner)

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

    def __str__(self):
        return str(self.text)

# @cache
class OCRController(BaseController):
    def __init__(self, debug_enable=False):
        self.debug_enable = debug_enable
        self.gc = capture
        super().__init__(debug_enable, self.gc)
        self.ocr_result:List[OCRResult] = []
        from myutils.timerutils import RateLimiter
        self.ocr_update_limiter = RateLimiter(0.2)
        self.ocr_update_limiter.execute(self.update_ocr_result)

    def get_ocr_result(self)->List[OCRResult]:
        self.ocr_update_limiter.execute(self.update_ocr_result)

        return self.ocr_result

    def update_ocr_result(self):
        """
        OCR是一比巨大的开销，添加时间间隔防止调用卡顿
        :return:
        """
        result = MinimapInterface.get_ocr_result()
        if not result: return

        result = result[0]
        if not result: return
        self.ocr_result = []
        for item in result:
            ocr_result_obj = OCRResult(corner=item[0], text=item[1][0], percent=item[1][1])
            self.ocr_result.append(ocr_result_obj)


    def click(self, x, y):
        """
        点击根据游戏内坐标转为屏幕坐标
        :param x:
        :param y:
        :return:
        """
        pos = self.gc.get_screen_position((x, y))
        self.log((x, y), "->", pos)
        self.set_ms_position(pos)
        self.mouse_left_click()

    def click_ocr_result(self, ocr_item:OCRResult):
        center = ocr_item.center
        self.click(center[0], center[1])

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

    def find_match_text(self, target_text, match_all=False)->List[OCRResult]:
        try:
            if self.stop_listen or target_text is None: return []
            self.log(f"正在查找'{target_text}'")
            # img = self.gc.get_screenshot()
            result = self.get_ocr_result()
            match_texts:List[OCRResult] = []
            for item in result:
                if target_text in item.text:
                    if match_all and target_text != item.text: continue
                    match_texts.append(item)
            return match_texts
        except Exception as e:
            self.logger.error(e.args)

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

        l = len(match_texts)
        if index < 0 or l == 0: return False

        self.log(f"共发现{l}个匹配的文本")
        if index >= l:
            self.log('你选择的下标超过了匹配数量，自动设置为最后一个')
            index = l - 1

        if click_all:
            self.log(f"点击所有匹配的文本")
            for match in match_texts:
                self.click_ocr_result(match)
                self.log(f"已经执行点击'{target_text}'操作")
        else:
            self.log(f"点击第{index + 1}个匹配的文本")
            match = match_texts[index]
            self.click_ocr_result(match)
            self.log(f"已经执行点击'{target_text}'操作")
        return True


    def is_text_in_screen(self, *args):
        if self.stop_listen or args is None: return
        self.log(f"在屏幕中查找{args}")
        result = self.get_ocr_result()
        for item in result:
            for arg in args:
                if arg in item.text:
                    self.logger.debug(f"屏幕上出现文本{arg},原文是{item.text}")
                    return True

        # if result is None: return False
        # for idx in range(len(result)):
        #     res = result[idx]
        #     for line in res:
        #         # if target_text in line[1][0]:
        #         for arg in args:
        #             try:
        #                 if arg is None: return False
        #                 if arg in line[1][0]:
        #                     self.log("屏幕上出现文本{}, 原文是{}:".format(arg, line[1][0]))
        #                     return True
        #             except TypeError as e:
        #                 self.log(line, e)
        #                 return False
        # self.log(f"没有找到{args}")
        return False


if __name__ == '__main__':
    # cv2.imshow('sc', gc.get_screenshot())
    # cv2.waitKey(0)
    ocr = OCRController(debug_enable=True)
    ocr.find_text_and_click('渊下宫', match_all=True)
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
    # while True:
    #     result = ocr.get_ocr_result()
    #     print(result)
        # time.sleep(15)
        # ocr.is_text_in_screen('复苏')
        # matches = ocr.find_match_text('复苏')
        # for match in matches:
        #     center = ocr.get_line_center(match.corner)
        #     ocr.click(center[0], center[1])




