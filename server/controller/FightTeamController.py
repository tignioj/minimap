import json
import os

from flask import Blueprint, jsonify, request, render_template

from server.controller.ServerBaseController import ServerBaseController

fight_team_bp = Blueprint('fight_team', __name__)

from server.service.FightTeamService import FightTeamService, FightTeamServiceException
fightteam_service = FightTeamService()
class FightTeamController(ServerBaseController):

    @staticmethod
    @fight_team_bp.get('/fight_team/list')
    def get_fight_team_list():
        try:
            team_list = fightteam_service.list_teams()
            return FightTeamController.success(data=team_list)
        except Exception as e:
            return FightTeamController.error(str(e.args))

    @staticmethod
    @fight_team_bp.post('/fight_team/create/<team_name>')
    def create_fightteam(team_name):
        plain_text = request.get_data(as_text=True)
        try:
            result = fightteam_service.create_team(team_name, plain_text)
            return FightTeamController.success(message=result)
        except FightTeamServiceException as e:
            return FightTeamController.error(message=str(e.args))

    @staticmethod
    @fight_team_bp.delete('/fight_team/delete/<team_file_name>')
    def delete_fightteam(team_file_name):
        try:
            result = fightteam_service.delete_team(team_file_name)
            return FightTeamController.success(message=result)
        except FightTeamServiceException as e:
            return FightTeamController.error(message=str(e.args))

    @staticmethod
    @fight_team_bp.put('/fight_team/update/<team_file_name>')
    def update_fightteam(team_file_name):
        data = request.get_data(as_text=True)
        new_team_name = request.args.get('new_team_name')
        try:
            result = fightteam_service.update_team(team_file_name, new_team_name, data)
            return FightTeamController.success(message=result)
        except (FileNotFoundError, FightTeamServiceException) as e:
            return FightTeamController.error(message=e.args)

    @staticmethod
    @fight_team_bp.get('/fight_team/get/<filename>')
    def get_fightteam(filename):
        try:
            content = fightteam_service.get_team(filename)
            return FightTeamController.success(data=content)
        except (FileNotFoundError, FightTeamServiceException) as e:
            return FightTeamController.error(message=e.args)



    # get方法，直接从文件读取战斗脚本
    @staticmethod
    @fight_team_bp.get('/fight_team/run/<filename>')
    def run_fightteam_file(filename):
        try:
            return FightTeamController.success(fightteam_service.run_teams_from_saved_file(filename))
        except (FileNotFoundError, FightTeamServiceException) as e:
            return FightTeamController.error(message=e.args)

    # post方法，从请求中读取战斗脚本
    @staticmethod
    @fight_team_bp.post('/fight_team/run_memory/<filename>')
    def run_fightteam_memory(filename):
        try:
            text_content = request.get_data(as_text=True)
            return FightTeamController.success(fightteam_service.run_teams_from_memory_text(filename, text_content))
        except (FileNotFoundError, FightTeamServiceException) as e:
            return FightTeamController.error(message=e.args)

    @staticmethod
    @fight_team_bp.get('/fight_team/stop')
    def get_stop_fightteam():
        try:
            return FightTeamController.success(fightteam_service.stop_fighting())
        except (FileNotFoundError, FightTeamServiceException) as e:
            return FightTeamController.error(message=e.args)

    @staticmethod
    @fight_team_bp.put('/fight_team/set_default/<filename>')
    def set_default_fightteam(filename):
        try:
            return FightTeamController.success(fightteam_service.set_default(filename))
        except (FileNotFoundError, FightTeamServiceException) as e:
            return FightTeamController.error(message=e.args)

