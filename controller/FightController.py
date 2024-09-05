import os.path
import re
import threading
import time

# 战斗
from controller.BaseController import BaseController
from fightmapper.FightMapperImpl import FightMapperImpl


# e:2  e长按两秒
# attack(10) 连续攻击10秒
# charge(10) 重击
# , 等待10秒

class StopFightException(Exception): pass


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
            from myutils.configutils import get_config, YAML_KEY_DEFAULT_FIGHT_TEAM
            filename = get_config(YAML_KEY_DEFAULT_FIGHT_TEAM)

        self.filename = filename
        self.team_name = None
        self.characters_name = None
        self.fight_mapper = FightMapperImpl(character_name=None)
        self.load_characters_with_skills_from_file()

    def get_teamname_from_string(self, file_name):
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
        success = True

        start_time = time.time()
        from random import randint
        while self.gc.get_team_current_number() != character_number:
            if time.time() - start_time > wait_time:
                success = False
                break
            # if self.stop_fight: raise StopFightException()
            # 稍微动一下屏幕让模板匹配更容易成功
            x = randint(-100, 100)
            y = randint(-100, 100)
            self.camera_chage(x, y)

            # 如果处于攀爬状态则按x
            if self.gc.is_climbing():
                self.kb_press_and_release('x')

            time.sleep(0.1)
            self.kb_press_and_release(str(character_number))

        # self.logger.debug(f"切人{character_number} {'成功' if success else '失败'}")
        if success:
            self.logger.debug(f"切人{character_number}成功")
        else:
            self.logger.warning(f"切人{character_number}超时失败")

        return success

    def get_character_number(self, name):
        if name not in self.characters_name:
            raise StopFightException(f"你指定的角色{name}不在队伍${self.characters_name}中")
        return self.characters_name.index(name) + 1

    def character_fight(self, character_with_skills):
        # 切人
        character = character_with_skills['name']
        character_number = self.get_character_number(character)
        skills = character_with_skills['skills']
        # 释放技能
        print(f'character{character}, num {character_number}, skills {skills}')
        while not self.switch_character(character): time.sleep(0.1)
        self.current_character = character
        self.fight_mapper.character_name = character
        for skill in skills:
            time.sleep(0.1)
            self.do_skill(skill)

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

    def execute(self):
        for character_with_skill in self.characters_with_skills:
            if self.stop_fight: raise StopFightException()
            self.character_fight(character_with_skill)

    def execute_infinity(self):
        try:
            while not self.stop_fight:
                self.execute()
        except StopFightException as e:
            self.logger.debug(e.args)
        finally:
            # 打断所有动作， 恢复状态
            if self.current_character == '散兵':
                # 连续按2次e避免还在空中
                self.kb_press_and_release('e')
                time.sleep(0.6)
                self.kb_press_and_release('e')
                time.sleep(0.1)

            # 跳跃打断所有动作
            self.kb_press_and_release(self.Key.space)
            self.current_character = None
            self.team_name = None

    def start_fighting(self):
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

        self.fighting_thread = threading.Thread(target=self.execute_infinity)
        self.fighting_thread.start()

    def stop_fighting(self):
        self.stop_fight = True
        if self.fighting_thread:
            self.fighting_thread.join()
            self.fighting_thread = None


if __name__ == '__main__':
    from myutils.configutils import get_user_folder

    from pynput.keyboard import Listener, Key

    # file_name = '那维莱特_莱伊拉_迪希雅_行秋(龙莱迪行).txt'
    # file_name = '那维莱特_莱伊拉_行秋_枫原万叶(龙莱行万).txt'
    file_name = '莱依拉_芙宁娜_枫原万叶_流浪者_(莱芙万流).txt'
    fc = FightController(file_name)
    # def _on_press(key):
    #     try:
    #         if key.char == '`':
    #             if fc.stop_fight:
    #                 fc.start_fighting()
    #             else:
    #                 fc.stop_fighting()
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
