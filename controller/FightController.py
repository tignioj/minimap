import os.path
import re
import threading
import time

# 战斗
from controller.BaseController import BaseController
from fightmapper.FightMapperImpl import FightMapperImpl
from controller.BaseController import StopListenException


# e:2  e长按两秒
# attack(10) 连续攻击10秒
# charge(10) 重击
# , 等待10秒

class StopFightException(Exception): pass

class CharacterDieException(StopFightException): pass
class SwitchCharacterTimeOutException(Exception): pass

class CharacterNotFoundException(Exception): pass

class FightController(BaseController):

    def __init__(self, filename, memory_mode=False):
        super().__init__()
        self.memory_mode = memory_mode
        self.fighting_thread = None
        self.characters_with_skills = []
        self.current_character = None
        self.stop_fight = False
        self.lastmod: float = None
        if not filename:
            from myutils.configutils import FightConfig
            filename = FightConfig.get(FightConfig.KEY_DEFAULT_FIGHT_TEAM)

        self.filename = filename
        self.team_name = None
        self.characters_name = None
        self.fight_mapper = FightMapperImpl(character_name=None)
        self.load_characters_with_skills_from_file()
        from controller.OCRController import OCRController
        self.ocr = OCRController(debug_enable=self.debug_enable)

    @staticmethod
    def get_teamname_from_string(file_name):
        team_name = file_name[file_name.index("(") + 1:file_name.rindex(")")]
        return team_name

    def get_characters_from_string(self, file_name):
        character_names = file_name[:file_name.index("(")].split("_")
        return character_names

    def load_data_from_text(self, text):
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("//") or len(line) == 0:
                continue
            character_with_skills = {'name': None, 'skills': []}
            # 角色
            character = line[:line.index(" ")]
            skill_str = line[line.index(" ") + 1:]
            character_with_skills['name'] = character
            sp = skill_str.split(",")
            for key in sp:
                skey = key.strip()
                character_with_skills['skills'].append(skey)
            self.characters_with_skills.append(character_with_skills)

    def update_data(self, team_name, characters_name, text):
        self.team_name = team_name
        # 去掉空白字符串
        self.characters_name = list(filter(None, characters_name))
        self.load_data_from_text(text)
    #
    def load_characters_with_skills_from_memory(self, characters_name:[], text:str, team_name:str):
        self.update_data(team_name=team_name, characters_name=characters_name, text=text)

    def load_characters_with_skills_from_file(self):
        # 如果是从内存中读取，则不需要读取文件
        if self.memory_mode: return

        filename = self.filename
        # 1. 读取队伍列表
        from myutils.configutils import get_user_folder
        team_folder = os.path.join(get_user_folder(), 'team')
        fight_file = os.path.join(team_folder, filename)
        # 没改变不用重新读取
        if self.lastmod == os.path.getmtime(fight_file):
            return
        self.lastmod = os.path.getmtime(fight_file)
        # print(self.team_name, self.character_names)
        with open(fight_file, 'r', encoding='utf8') as f:
            text = f.read()

        teamname = self.get_teamname_from_string(filename)
        characters = self.get_characters_from_string(filename)
        self.update_data(team_name=teamname, characters_name=characters, text=text)

    def switch_character(self, character_name, wait_time=8):
        """
        切角色。
        :param character_name: 角色名称
        :param wait_time: 最多等待多少秒
        :return:
        """
        character_number = self.get_character_number(character_name)
        start_time = time.time()
        from random import randint
        while self.gc.get_team_current_number() != character_number:
            if time.time() - start_time > wait_time: raise SwitchCharacterTimeOutException(f"切{character_name}超时！")
            close_button_pos = self.gc.get_icon_position(self.gc.icon_close_while_arrow)
            if len(close_button_pos) > 0:
                has_eggs = self.gc.has_revive_eggs()
                if has_eggs:
                    from myutils.configutils import PathExecutorConfig
                    if PathExecutorConfig.get(
                            PathExecutorConfig.KEY_ENABLE_FOOD_REVIVE, True):
                        self.logger.debug('复活道具-1')
                        self.click_if_appear(self.gc.icon_message_box_button_confirm)
                        time.sleep(0.2)  # 等待对话框消失
                    else:
                        msg = "由于没有开启使用道具复活，已无法继续战斗, 前往七天神像复活"
                        self.click_if_appear(self.gc.icon_message_box_button_cancel)
                        raise CharacterDieException(msg)
                else:
                    # 检测到有关闭按钮, 但是没检测到鸡蛋(被倒计时数字遮挡)，说明鸡蛋在倒计时，此时已经无法继续战斗
                    msg = "复活仍在倒计时, 已无法继续战斗, 前往七天神像复活"
                    self.logger.debug(msg)
                    self.click_screen(close_button_pos[0])
                    raise CharacterDieException(msg)
            # 稍微动一下屏幕让模板匹配更容易成功
            x = randint(-100, 100)
            y = randint(-100, 100)
            self.camera_chage(x, y)

            # 如果处于攀爬状态则按x
            if self.gc.is_climbing():
                self.kb_press_and_release('x')

            time.sleep(0.1)
            self.kb_press_and_release(str(character_number))

        self.logger.debug(f"切人{character_number}成功")

    def get_character_number(self, name):
        if name not in self.characters_name:
            # TODO： 子线程的异常如何捕捉？
            raise CharacterNotFoundException(f"你指定的角色{name}不在队伍${self.characters_name}中")
        return self.characters_name.index(name) + 1

    def character_fight(self, character_with_skills, start_fight_time,stop_on_no_enemy ):
        character = character_with_skills['name']
        character_number = self.get_character_number(character)
        skills = character_with_skills['skills']
        # 释放技能
        self.logger.debug(f'character{character}, num {character_number}, skills {skills}')
        try:
            self.switch_character(character)
            # 5秒后才开始检测，确保充分进入战斗状态
            if time.time() - start_fight_time > 5 and stop_on_no_enemy:
                if not self.has_enemy():
                    self.stop_fight = True
                    raise StopFightException("切人后:未发现敌人，结束战斗")
            self.current_character = character
            self.fight_mapper.character_name = character
            for skill in skills:
                time.sleep(0.1)
                self.do_skill(skill)
        except SwitchCharacterTimeOutException as e:
            self.logger.error(e)

    def parse_method_call(self, method_call_str):
        # 使用正则表达式提取方法名称和参数
        pattern = r'(\w+)\((.*)\)'
        match = re.match(pattern, method_call_str)

        if not match:
            # raise ValueError("Invalid method call string format")
            return method_call_str, []

        method_name = match.group(1)
        params_str = match.group(2)

        # 处理参数（假设参数是简单的标识符或数字，并用逗号分隔）
        params = [param.strip() for param in params_str.split(',')]

        return method_name, params

    def do_skill(self, skill):
        method_name, params = self.parse_method_call(skill)
        if self.stop_fight: raise StopFightException()
        # 使用反射调用方法
        if hasattr(self.fight_mapper, method_name):
            method = getattr(self.fight_mapper, method_name)
            if callable(method):
                method(*params)
            else:
                print(f"{method_name} is not callable")
        else:
            print(f"{method_name} does not exist")

    def execute(self,  stop_on_no_enemy=False):
        start_time = time.time()
        for character_with_skill in self.characters_with_skills:
            if self.stop_fight: raise StopFightException()
            self.character_fight(character_with_skill, start_fight_time=start_time, stop_on_no_enemy=stop_on_no_enemy)

    def execute_infinity(self, stop_on_no_enemy=False):
        try:
            while not self.stop_fight:
                self.execute(stop_on_no_enemy)
        except CharacterDieException as e:
            self.logger.debug(e.args)
        except StopFightException as e:
            self.logger.debug(e.args)
            # 打断所有动作， 恢复状态
            if self.current_character == '散兵' or self.current_character == '流浪者':
                # 连续按2次e避免还在空中
                self.gc.is_flying()
                self.kb_press_and_release('e')
                time.sleep(0.5)
                self.kb_press_and_release('e')
                time.sleep(0.1)

            # 跳跃打断所有动作
            self.kb_press_and_release(self.Key.space)
            self.current_character = None
            self.team_name = None
        except StopListenException as e:
            self.logger.debug(e.args)

        self.stop_fight = True

    def start_fighting(self, stop_on_no_enemy=False):
        self.stop_fight = False
        if self.fighting_thread:
            raise StopFightException("已经有线程正在执行，请先停止！")
            # try:
            #     self.stop_fighting()
            # except Exception as e:
            #     self.logger.debug(e)
        if self.memory_mode:
            # 如果是内存模式，检查数据是否成功加载
            if len(self.characters_name) == 0:
                raise StopFightException("正处于内存模式运行，但是未检测到队伍信息")
        else:
            self.load_characters_with_skills_from_file()

        self.fighting_thread = threading.Thread(target=self.execute_infinity, args=(stop_on_no_enemy,))
        self.fighting_thread.start()

    def stop_fighting(self):
        self.stop_fight = True
        if self.fighting_thread:
            self.fighting_thread.join()
            self.fighting_thread = None

    def shield(self, adjust_direction=True):
        """
        :param adjust_direction:  专门为钟离优化的参数。True表示向身后开盾，避免前进时候撞到柱子
        :return:
        """
        try:
            for character in self.characters_name:
                if character == "钟离":
                    self.switch_character('钟离')
                    if adjust_direction:
                        self.fight_mapper.s(0.1)
                    self.fight_mapper.e(hold=True)
                elif character == "迪奥娜":
                    self.switch_character('迪奥娜')
                    self.fight_mapper.e(hold=True)
                elif character == '莱依拉':
                    self.switch_character('莱依拉')
                    self.fight_mapper.e()
                elif character == '绮良良':
                    self.switch_character('绮良良')
                    self.fight_mapper.e()
                elif character == '诺艾尔':
                    self.switch_character('诺艾尔')
                    self.fight_mapper.e()
        except (SwitchCharacterTimeOutException,CharacterNotFoundException) as e:
            self.logger.error(e.args)

    def wanye_pickup(self):
        # 切万叶
        if not '枫原万叶' in self.characters_name:
            self.logger.debug("万叶不在队伍中，停止聚材料")
            return
        self.logger.debug("万叶拾取中")
        try:
            self.switch_character('枫原万叶')
        except SwitchCharacterTimeOutException as e:
            self.logger.error(e)  # 超时异常
            return
        except CharacterNotFoundException as e:
            self.logger.debug(e)
            return
        time.sleep(0.1)
        # 万叶长e
        self.logger.debug('万叶长e')
        self.fight_mapper.e(hold=True)
        # 下落攻击
        # 不知道为什么有时候下落攻击失败，多a几次
        self.fight_mapper.attack(0.4)
        for i in range(25):  # 疯狂f
            time.sleep(0.1)
            self.crazy_f()
        self.logger.debug("万叶拾取结束")

    def has_enemy(self):
        """
        判断是否有敌人
        按下L按过0.15秒检测派蒙，如果没有派蒙说明已经在读条，判断为脱战, 否则判断为有敌人
        经过测试不能检测太快，刚进入战斗的瞬间，系统仍然可以一小段条，这样会导致误判
        因此在调用本方法时，确保足够的时间进入战斗状态
        TODO 本方法目前还不靠谱，需要结合YOLO判断敌人血量和箭头
        :return:
        """
        self.log('正在检测敌人')
        self.kb_press_and_release("l")
        time.sleep(0.15)
        has = self.gc.has_paimon()
        if has:
            self.log('有敌人')
            return True
        else:
            # 打断读条
            # cv2.imwrite(f'sc{time.time()}.jpg', self.gc.screenshot)
            self.log('没有敌人')
            self.kb_press_and_release("l")  # 不要使用空格,避免下一个角色无法释放技能
            time.sleep(0.02)
            return False






if __name__ == '__main__':
    # FightController.has_enemy()
    # from myutils.configutils import get_user_folder, PathExecutorConfig

    from pynput.keyboard import Listener, Key

    # file_name = '那维莱特_莱伊拉_迪希雅_行秋(龙莱迪行).txt'
    # file_name = '那维莱特_莱伊拉_行秋_枫原万叶(龙莱行万).txt'
    # file_name = '莱依拉_芙宁娜_枫原万叶_流浪者_(莱芙万流).txt'
    # file_name = '莱依拉_芙宁娜_枫原万叶_流浪者_(莱芙万流).txt'
    fc = FightController(None)
    # fc.execute_infinity()
    fc.has_enemy()
    # while True:
    #     time.sleep(1)
    #     has = fc.has_enemy()
    #     print(has)
    # fc.switch_character('纳西妲')
    # def _on_press(key):
    #     try:
    #         if key.char == '`':
    #             fc.start_fighting()
    #         elif key.char == '~':
    #             fc.stop_fighting()
    #     except AttributeError as e:
    #         pass
    #
    # l = Listener(on_press=_on_press)
    # l.start()
    # l.join()

    # time.sleep(12)
    # print('等待结束中', time.time())
    # fc.stop_fighting()
    # print('结束了', time.time())
