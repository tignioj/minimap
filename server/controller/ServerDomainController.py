import os
from flask import Blueprint, jsonify, request, current_app
from server.controller.ServerBaseController import ServerBaseController
from myutils.configutils import resource_path
from server.service.DomainService import DomainService

domain_bp = Blueprint('config_bp', __name__)
from controller.DomainController import DomainController

class ServerDomainController(ServerBaseController):
    @staticmethod
    @domain_bp.route('/domain/list', methods=['GET'])
    def get_domain_list():
        try:
            data = DomainService.get_domain_list()
            return ServerBaseController.success(data=data)
        except Exception as e:
            return ServerBaseController.error(str(e.args))

    @staticmethod
    @domain_bp.route('/domain/run', methods=['GET'])
    def run_domain():
        domain_name = request.args.get('domain_name')
        fight_team = request.args.get('fight_team')
        timeout = request.args.get('timeout')
        socketio_instance = current_app.extensions['socketio']
        try:
            if domain_name is None: return ServerBaseController.error("必须指定秘境名称")
            DomainService.run_domain(domain_name, fight_team, timeout, emit=socketio_instance.emit)
            return ServerBaseController.success(f"已发送执行秘境请求：{domain_name}, {fight_team}, {timeout}")
        except Exception as e:
            return ServerBaseController.error(f"执行秘境{domain_name}出现错误:{e.args}")


    @staticmethod
    @domain_bp.route('/domain/stop', methods=['GET'])
    def stop_domain():
        try:
            socketio_instance = current_app.extensions['socketio']
            DomainService.stop_domain()
            return ServerBaseController.success("成功停止秘境")
        except Exception as e:
            return ServerBaseController.error(f"无法停止秘境{e.args}")



