import datetime
import os.path
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from matchmap.minimap_interface import MinimapInterface

"""
PyCharm需要用管理员方式启动，否则游戏内输入无效！
"""
from pynput import keyboard
from pynput.keyboard import Key
import json
from myutils.configutils import cfg
from myexecutor.BasePathExecutor2 import Point, BasePathExecutor, PointEncoder
from typing import List

class PathRecorder:
    """
    功能：键盘按下HOME开始记录路径，按照一定的频率记录点位
    键盘按下END结束记录，并保存路径到json文件
    """

    def __init__(self, country=None, name='untitled', region='any', debug_enable=False, edit_mode=False,
                 edit_file_path=None):
        """
        路径记录器
        :param country:  在什么国家？（必要参数)
        :param name:  目标检测对象
        :param region: 在什么区域? 可选，仅为了方便分类
        """
        self.debug_enable = debug_enable
        self.auto_tracker = MinimapInterface
        # 记录路径的列表，内容为x,y,type
        self.positions: List[Point] = []
        self.path_viewer_scale = 1.5  # 预览地图放大倍率

        self.path_viewer_width = cfg.get('path_viewer_width', 500)
        if edit_mode:
            if os.path.exists(edit_file_path):
                json_obj = BasePathExecutor.load_basepath_from_json_file(edit_file_path)
                name = json_obj['name']
                self.positions:List[Point] = json_obj["positions"]
                country = json_obj['country']
                x = self.positions[0].x
                y = self.positions[0].y
                self.auto_tracker.create_cached_local_map((x,y))
                self.record_json_path = edit_file_path
            else:
                raise FileNotFoundError(edit_file_path)
        else:
            save_path = f"../resources/pathlist/{name}"
            if not os.path.exists(save_path):
                os.mkdir(save_path)
            timestr = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
            self.record_json_path = f"../resources/pathlist/{name}/{name}_{country}_{region}_{timestr}.json"

        if country is None:
            raise Exception('必须指定国家')

        self.name = name
        self.region = region
        self.country = country

        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()

        txt = """
        快捷键介绍：
        1. 全局快捷键:
            F9: 进入记录模式, 再次按下F9退出记录模式。
            -: 缩小展示地图
            =: 放大展示地图
            PageUP: 根据当前记录的点位进行回放
        2. 进入记录模式后的快捷键:
            1) Insert: 目标检测点位 (首个点位无论是否为目标对象，必须在锚点附近，用于传送)
            2) .: 插入途径点
            3) Delete: 清空路径
            4) BackSpace: 删除上一个点位
            5) End: 保存为json
        
        流程：
        1) 传送到锚点附近别动, 按下F9进入记录模式
        2) 按下Insert插入第一个点。接下来可以自由行动.
        3) 按下英文句号插入途径点（非检测对象）
        4) 重复2，3直到不需要再插入任何点位
        5) 按下End保存json
        6) 按下F9退出记录模式
        7) 按下Page UP回放
        """
        print(txt)
        self.is_recording = False  # 是否开始录制的标志

        threading.Thread(target=self.points_viewer).start()

        self.listener.join()

    def __putText(self, img, text, org=(0,20), font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.5, color=(0,0,255), thickness=2):
        # 在图像上添加文字
        cv2.putText(img, text, org, font, font_scale, color, thickness)

    def user_position_map(self):
        pos = self.auto_tracker.get_position()
        if pos:
            img = self.auto_tracker.get_region_map(x=pos[0], y=pos[1], width=self.path_viewer_width)
            if img is not None:
                w,h = img.shape[0], img.shape[1]
                img = cv2.circle(img, (w//2,h//2), 5, (0,255,255), 2)
                return img


    def points_viewer(self):
        from myexecutor.KeyPointViewer import get_points_img_live

        while True:
            time.sleep(0.02)
            if len(self.positions) < 1:
                img = self.user_position_map()
            else:
                img = get_points_img_live(self.positions, self.name, width=self.path_viewer_width, scale=self.path_viewer_scale)

            if img is None: continue
            if self.is_recording:
                self.__putText(img, 'Recording', color=(0, 255, 0), font_scale=0.9)
            else:
                self.__putText(img, 'Press F9 to start record', color=(0, 0, 255), font_scale=0.9)

            # img = cv2.resize(img, None, fx=0.6, fy=0.6)
            cv2.imshow('path viewer', img)
            cv2.moveWindow('path viewer', 10,10)
            # 窗口置顶
            cv2.setWindowProperty('path viewer', cv2.WND_PROP_TOPMOST, 1)
            cv2.waitKey(20)
        cv2.destroyAllWindows()

    def start_record(self):
        print("你调用了start_record")
        if self.is_recording:
            print("已经开始记录了，无需再次开始，如果需要停止请按下END")
        else:
            print("成功开启记录")
            self.is_recording = True

    def stop_record(self):
        if self.is_recording:
            print("停止记录")
            self.is_recording = False
        else:
            print("你还没有开始记录,无需停止，请按下HOME开始记录")

    def save_json(self):
        # Serializing json
        dictionary = {
            "name": self.name,
            "positions": self.positions,
            "country": self.country
        }
        json_object = json.dumps(dictionary, indent=4, ensure_ascii=False, cls=PointEncoder)
        with open(self.record_json_path, mode="w",
                  encoding="utf-8") as outfile:
            outfile.write(json_object)
        print(f"保存{self.record_json_path}成功")

    def save_current_position(self, type='path'):
        if not self.is_recording:
            print("你还没有进入记录模式, 无法编辑路径，请先用键盘按下F9进入记录模式")
            return False

        print("正在获取位置")
        position = self.auto_tracker.get_position()
        print("结束获取位置", position)
        # rotation = self.auto_tracker.get_rotation()
        if position:
            # point = {'x': position[0], 'y': position[1], 'type': type}
            p = Point(position[0], position[1], type)
            print("成功记录当前点位", p)
            self.positions.append(p)
            return True
        else:
            print(f"无法插入{type}点位, 原因是位置无法正确获取")
            return False

    def __get_temp_json_file(self):
        # 生成临时路径文件，用于回放内存中的路径
        # Serializing json
        dictionary = {
            "name": self.name,
            "positions": self.positions,
            "country": self.country  # TODO BUG: 没有写country的时候，MapController进入黑屏时，可能会一直找不到位置
        }
        json_object = json.dumps(dictionary, indent=4, ensure_ascii=False,cls=PointEncoder)
        # Writing to sample.json
        timestr = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        if not os.path.exists('../resources/pathlist/temp'):
            os.mkdir('../resources/pathlist/temp')
        temp_record_json_path = f"../resources/pathlist/temp/{self.name}_{self.country}_{self.region}_{timestr}.json"
        with open(temp_record_json_path, mode="w",
                  encoding="utf-8") as outfile:
            outfile.write(json_object)
        print(f"生成临时json文件{self.record_json_path}成功")
        return temp_record_json_path

    def on_press(self, key):
        try:
            c = key.char
            if c == '=':
                self.path_viewer_scale += 0.5
            elif c == '-':
                self.path_viewer_scale -= 0.5
            elif c == '.':
                print("你按下了., 手动插入途径点位'path'")
                self.save_current_position('path')  # 插入点位

            if self.path_viewer_scale < 0.1:
                self.path_viewer_scale = 0.1
            if self.path_viewer_scale > 10:
                self.path_viewer_scale =10

            # print('alphanumeric key {0} pressed'.format(key.char))
        except AttributeError:
            if key == Key.f9:
                if not self.is_recording:
                    self.start_record()
                else:
                    self.stop_record()
            # print('special key {0} pressed'.format(key))
            elif key == Key.insert:
                print(f'你按下了insert, 插入{self.name}点位')
                print('你按下了end, 尝试存储当前点位为json')
                self.save_json()
            elif key == Key.page_up:
                print("你按下了page_up, 准备回放")
                if self.is_recording:
                    print("请先停止记录再回放")
                else:
                    from myexecutor.BasePathExecutor2 import BasePathExecutor
                    jsonfile = self.__get_temp_json_file()
                    try:
                        if os.path.exists(jsonfile):
                            BasePathExecutor(jsonfile, debug_enable=True).execute()
                        else:
                            print(f"回放的文件路径'{jsonfile}'不存在！")
                    except Exception as e:
                        print("回放出现了异常", e)
                    finally:
                        print(f"删除临时文件{jsonfile}")
                        try:
                            os.remove(jsonfile)
                        except Exception as e:
                            print("删除临时文件失败，原因", e)
            elif key == Key.backspace:
                print("你按下了Backspace，删掉上一个点位")
                if not self.is_recording:
                    print("你还没有进入记录模式，禁止操作")
                    return
                if len(self.positions) > 0:
                    self.positions.pop()
                else:
                    print("点位为空，无法执行删除上一个点位操作")
            elif key == Key.delete:
                if not self.is_recording:
                    print("你还没有进入记录模式，禁止操作")
                    return
                print("你按下了delete，清空当前路径并停止记录")
                self.stop_record()
                self.positions = []

    def on_release(self, key):
        pass

    def debug(self):
        print("get_position")
        print(self.auto_tracker.get_position())
        # print("get_direction")
        # print(self.auto_tracker.get_direction())
        print("get_rotation")
        print(self.auto_tracker.get_rotation())
        print("ocrtest end")


def gouliange():
    # PathRecorder(name='调查', region='雪山', country='蒙德', debug_enable=True)
    # PathRecorder(name='调查', region='山脊守望', country='蒙德', debug_enable=True)
    # PathRecorder(name='调查', region='地中之岩', country='璃月', debug_enable=True)
    # PathRecorder(name='调查', region='珉林东北', country='璃月', debug_enable=True)
    # PathRecorder(name='调查', region='碧水河西岸', country='璃月', debug_enable=True)
    # PathRecorder(name='调查', region='碧水河西岸2', country='璃月', debug_enable=True)
    # PathRecorder(name='调查', region='奥藏山东侧', country='璃月', debug_enable=True)
    # PathRecorder(name='调查', region='绝云间南路', country='璃月', debug_enable=True)
    # PathRecorder(name='调查', region='翠玦坡北', country='璃月', debug_enable=True)  # 有怪物
    # PathRecorder(name='调查', region='采樵谷', country='璃月', debug_enable=True)  # 有怪物
    # 稻妻
    # PathRecorder(name='调查', region='无相火', country='稻妻', debug_enable=True)  # 有怪物
    # PathRecorder(name='调查', region='九条阵屋西', country='稻妻', debug_enable=True)  # 有怪物
    # PathRecorder(name='调查', region='名椎滩', country='稻妻', debug_enable=True)  # 有水史莱姆
    # PathRecorder(name='调查', region='绯木村', country='稻妻', debug_enable=True)
    # PathRecorder(name='调查', region='海祈岛离岛西南', country='稻妻', debug_enable=True)  # good
    # PathRecorder(name='调查', region='沉眠之庭副本西侧', country='稻妻', debug_enable=True)
    # PathRecorder(name='调查', region='平海砦东野伏众营地', country='稻妻', debug_enable=True)  # 终点有耶夫中
    # PathRecorder(name='调查', region='越石村', country='稻妻', debug_enable=True)
    # PathRecorder(name='调查', region='清籁丸', country='稻妻', debug_enable=True)

    # 须弥
    # PathRecorder(name='调查', region='无郁稠林', country='须弥', debug_enable=True)  # 终点有怪
    # PathRecorder(name='调查', region='卡萨扎莱宫南', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='香醉坡东北', country='须弥', debug_enable=True)  # 有怪
    # PathRecorder(name='调查', region='化城郭西', country='须弥', debug_enable=True) # good
    # PathRecorder(name='调查', region='维摩庄', country='须弥', debug_enable=True)  # 有怪
    # PathRecorder(name='调查', region='维摩庄2', country='须弥', debug_enable=True)  # good
    # PathRecorder(name='调查', region='奥摩斯港', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='奥摩斯港2', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='二净旬神像右边', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='二净旬神像右上角', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='善见地-童梦的切片', country='须弥', debug_enable=True)  # good
    # PathRecorder(name='调查', region='须弥城1', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='沙漠-列柱沙原-阿赫曼营地', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='沙漠-列柱沙原-阿如村北', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='沙漠-列柱沙原-阿如村东-小推车', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='沙漠-列柱沙原-阿如村内部', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='沙漠-列柱沙原-下风蚀地', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='沙漠-列柱沙原-吞羊岩', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='鸡哥左下角', country='须弥', debug_enable=True)
    # PathRecorder(name='调查', region='鸡哥左下角-南', country='须弥', debug_enable=True)

    # 测试
    PathRecorder(name='调查', region='测试3珉林桥边', country='璃月', debug_enable=True)
    # 枫丹


def getjson(filename):
    # 获取当前脚本所在的目录
    target = filename.split("_")[0]
    relative_path = f"../resources/pathlist/{target}"
    # 拼接资源目录的路径
    file = os.path.join(relative_path, filename)
    return file


def edit_json(filename):
    # file_to_edit = "调查_稻妻_沉眠之庭副本西侧_2024-04-28_15_56_01.json"
    # file_to_edit = "调查_稻妻_越石村_2024-04-28_18_46_34.json"
    # file_to_edit = "调查_须弥_香醉坡东北_2024-04-29_01_55_09.json"
    # file_to_edit = "调查_璃月_采樵谷_2024-04-28_07_12_25.json"
    # file_to_edit = "调查_稻妻_无相火_2024-04-27_15_37_44.json"
    file_to_edit = filename
    sp = file_to_edit.split("_")
    name = sp[0]
    country = sp[1]
    region = sp[2]
    PathRecorder(name, country, region, edit_mode=True, edit_file_path=getjson(file_to_edit))


def collect_path_record():
    # PathRecorder(name='甜甜花', region='誓言岬', country='蒙德', debug_enable=True)
    # PathRecorder(name='甜甜花', region='清泉镇', country='蒙德', debug_enable=True)
    PathRecorder(name='月莲', region='降魔山2', country='须弥', debug_enable=True)
    # PathRecorder(name='搜刮', region='望风角', country='蒙德', debug_enable=True)
    # PathRecorder(name='甜甜花', region='中央实验室遗址_test', country='枫丹', debug_enable=True)
    # PathRecorder(name='甜甜花', region='中央实验室遗址', country='枫丹', debug_enable=True)


if __name__ == '__main__':
    # gouliange()
    collect_path_record()
    # edit_json('搜刮_蒙德_望风角_2024-08-04_16_52_58.json')
    # edit_json('甜甜花_蒙德_清泉镇_2024-07-31_07_30_39.json')
    # edit_json('调查_璃月_地中之岩_2024-04-29_06_23_28.json')
    # edit_json('甜甜花_枫丹_中央实验室遗址_2024-07-31_07_01_37.json')
