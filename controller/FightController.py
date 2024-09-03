import os.path
import re
import sys
import threading
import time
from array import array
from random import random

# 战斗
from controller.BaseController import BaseController

# e:2  e长按两秒
# attack(10) 连续攻击10秒
# charge(10) 重击
# , 等待10秒

class StopFightException(Exception): pass


class FightController(BaseController):
    def __init__(self, file_name='莱依拉_芙宁娜_枫原万叶_散兵(莱芙万散).txt'):
        super().__init__()
        self.characters_with_skills = []
        self.team_name = ''
        self.character_names = []
        self.current_character = None
        self.read_txt(file_name)
        self.stop_fight = False

    def read_txt(self, file_name):
        # 1. 读取队伍列表
        from myutils.configutils import resource_path
        team_folder = os.path.join(resource_path, 'user', 'team')
        user_team = os.path.join(team_folder, file_name)

        self.team_name = file_name[file_name.index("(")+1:file_name.rindex(")")]
        self.character_names = file_name[:file_name.index("(")].split("_")
        print(self.team_name, self.character_names)

        with open(user_team, 'r', encoding='utf8') as f:
            line = f.readline()
            while line:
                if line.strip().startswith("//"):
                    line = f.readline()
                    continue
                character_with_skills = {'name': None, 'skills': []}
                # 角色
                character = line[:line.index(" ")]
                skill_str = line[line.index(" ")+1:]
                character_with_skills['name'] = character
                sp = skill_str.split(",")
                for key in sp:
                    skey = key.strip()
                    character_with_skills['skills'].append(skey)
                self.characters_with_skills.append(character_with_skills)
                line = f.readline()
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
            if time.time() - start_time > wait_time: break
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
        self.logger.debug(f"切人{character_number}成功")

        return True

    def get_character_number(self, name):
        return self.character_names.index(name) + 1

    def people_fight(self, character_with_skills):
        # 切人
        character = character_with_skills['name']
        character_number = self.get_character_number(character)
        skills = character_with_skills['skills']
        # 释放技能
        print(f'character{character}, num {character_number}, skills {skills}')
        while not self.switch_character(character): time.sleep(0.1)
        self.current_character = character
        for skill in skills:
            time.sleep(0.1)
        #     TODO: 检验键盘值是否在允许字符内避免恶意按键
            self.do_skill(skill)

    def parse_method_call(self,method_call_str):
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
        from fightmapper.BaseFightMapper import BaseFightMapper
        fight_mapper = BaseFightMapper()
        method_name, params = self.parse_method_call(skill)
        if self.stop_fight: raise StopFightException()
        # 使用反射调用方法
        if hasattr(fight_mapper, method_name):
            method = getattr(fight_mapper, method_name)
            if callable(method):
                method(*params)
            else:
                print(f"{method_name} is not callable")
        else:
            print(f"{method_name} does not exist")

    def execute(self):
        for character_with_skill in self.characters_with_skills:
            self.people_fight(character_with_skill)

    def execute_infinity(self):
        try:
            while not self.stop_fight:
                for character_with_skill in self.characters_with_skills:
                    self.people_fight(character_with_skill)
        except StopFightException as e:
            raise e
        finally:
            # 打断所有动作， 恢复状态
            if self.current_character == '散兵':
                # 连续按2次e避免还在空中
                self.kb_press_and_release('e')
                time.sleep(0.05)
                self.kb_press_and_release('e')

            # 跳跃打断所有动作
            self.kb_press_and_release(self.Key.space)


if __name__ == '__main__':
    f = FightController()
    threading.Thread(target=f.execute_infinity).start()
    time.sleep(10)
    f.stop_fight = True