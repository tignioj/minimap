import os
import threading

from myutils.configutils import get_user_folder

class FightTeamServiceException(Exception): pass
from controller.FightController import FightController
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('fight_team_service')

class FightTeamService:

    def __init__(self):
        user_folder = get_user_folder()
        self.team_folder_path = os.path.join(user_folder, 'team')
        self.fight_controller:FightController = None

    def check_team_content_valid(self, team_file_name, content):
        # 检查内容中选择的角色是否在文件名中给出，没有则抛出异常
        team_str = team_file_name[:team_file_name.find('(')-1]
        team_split = team_str.split("_")
        # 去掉空字符串
        team_split = [item for item in team_split if item]
        if len(team_split) != 4:
            raise FightTeamServiceException("队伍长度必须是4")

        lines = content.split("\n")
        # 检查每一行第一列角色是否在team list中
        error_character = []
        for line in lines:
            line:str = line.strip()
            if len(line) == 0: continue
            if line.startswith("//"): continue

            # 提取角色名称
            character_name = line[:line.find(" ")+1].strip()
            if character_name not in team_split:
                # 不存重复的
                if character_name not in error_character:
                    error_character.append(character_name)
        if len(error_character) > 0:
            raise FightTeamServiceException(f"请检查{str(error_character)}角色是否包含在文件名中!")

        return True

    def create_team(self, team_file_name, content):
        team_file_path = os.path.join(self.team_folder_path, team_file_name)
        if os.path.exists(team_file_path):
            raise FightTeamServiceException("已存在同命名文件队伍，创建失败!")
        self.check_team_content_valid(team_file_name, content)
        with open(team_file_path, 'w', encoding='utf8') as f:
            f.write(content)
        return f"成功创建队伍{team_file_name}"

    def __get_team_file_path(self, team_file_name):
        team_file_path = os.path.join(self.team_folder_path, team_file_name)
        if not os.path.exists(team_file_path):
            raise FightTeamServiceException(f'你要查找的{team_file_name}文件未找到')
        return team_file_path
    def get_team(self, team_file_name):
        team_file_path = self.__get_team_file_path(team_file_name)
        with open(team_file_path, 'r', encoding='utf8') as f:
            return f.read()

    def update_team(self, team_file_name, new_team_name, data):
        team_file_path = self.__get_team_file_path(team_file_name)

        self.check_team_content_valid(new_team_name, data)
        with open(team_file_path, 'w', encoding='utf8') as f:
            f.write(data)

        new_name = os.path.join(get_user_folder(), 'team', new_team_name)

        # 如果名称没改变，直接返回更新成功
        if new_team_name == team_file_name:
            return f"成功更新{team_file_name}"

        # 如果名称改变了，但是新的名称已经存在，则抛出异常
        if os.path.exists(new_name) and new_team_name != team_file_name:
            raise FightTeamServiceException("文件内容更新成功，但是已经存在同名文件，改名失败")

        # 其余情况就是名称改变了,且新的文件名可用，则返回成功
        try:
            os.rename(team_file_path, new_name)
            return f"成功更新{team_file_name},并且更名为{new_team_name}"
        except Exception as e:
            logger.exception(e)
            raise FightTeamServiceException(f"文件内容已经更新，但是重命名失败{str(e.args)}")


    def delete_team(self, team_file_name=None):
        team_file_path = self.__get_team_file_path(team_file_name)
        try:
            os.remove(team_file_path)
            return f"删除{team_file_name}成功"
        except Exception as e:
            logger.exception(e)
            return f"删除{team_file_name}失败{str(e.args)}"

    def list_teams(self):
        default_team = self.get_default()
        files = os.listdir(self.team_folder_path)
        return {'default': default_team, 'files': files}

    def run_teams_from_saved_file(self, filename):
        from controller.BaseController import BaseController
        BaseController.stop_listen = False
        if self.fight_controller:
            try: self.fight_controller.stop_fighting()
            except:pass
        self.__get_team_file_path(filename)
        self.fight_controller = FightController(filename)
        self.fight_controller.start_fighting()
        return f"成功运行{filename}"

    def stop_fighting(self):
        from controller.BaseController import BaseController
        BaseController.stop_listen = True
        if self.fight_controller:
            try: self.fight_controller.stop_fighting()
            except Exception as e:
                logger.exception(e)
                raise FightTeamServiceException("你没有运行，无需停止")
        self.fight_controller = None
        return "成功停止"

    def set_default(self, filename):
        from myutils.configutils import FightConfig
        try:
            FightConfig.set(FightConfig.KEY_DEFAULT_FIGHT_TEAM, filename)
            FightConfig.save_config()
            return f"设置默认战斗队伍为{filename}成功"
        except Exception as e:
            logger.exception(e,exc_info=True)
            raise FightTeamServiceException(f"设置默认队伍失败:{e.args}")


    def get_default(self):
        from myutils.configutils import FightConfig
        try:
            return FightConfig.get(FightConfig.KEY_DEFAULT_FIGHT_TEAM)
        except Exception as e:
            logger.exception(e,exc_info=True)
            raise FightTeamServiceException(f"设置默认队伍失败:{e.args}")

    def run_teams_from_memory_text(self, filename, text):
        from controller.BaseController import BaseController
        BaseController.stop_listen = False
        if self.fight_controller:
            raise FightTeamServiceException("请先停止正在执行的脚本")
            # try:
            #     self.fight_controller.stop_fighting()
            # except:pass
        self.fight_controller = FightController(None, memory_mode=True)
        team_name = self.fight_controller.get_teamname_from_string(filename)
        characters = self.fight_controller.get_characters_from_string(filename)
        self.fight_controller.load_characters_with_skills_from_memory(characters_name=characters, text=text, team_name=team_name)
        self.fight_controller.start_fighting()
        return f"正在从临时内容中运行{filename}"


if __name__ == '__main__':
    import time
    ft = FightTeamService()
    # ft.run_teams_from_saved_file("莱依拉_芙宁娜_枫原万叶_流浪者_(莱芙万流).txt")
    # ft.run_teams_from_memory_text("1_2_3_散兵(xx).txt", "散兵 e, charge, charge, charge, charge, charge")
    ft.run_teams_from_memory_text("1_2_3_散兵(xx).txt", "散兵 charge")
    time.sleep(1)
    ft.stop_fighting()