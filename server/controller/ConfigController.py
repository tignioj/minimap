import os

from flask import Blueprint, jsonify, request
from server.controller.ServerBaseController import ServerBaseController
config_bp = Blueprint('config_bp', __name__)
from myutils.configutils import AccountConfig, BaseConfig, application_path, reload_config

class ConfigController(ServerBaseController):
    @staticmethod
    @config_bp.route('/config/get')
    def config_get():
        config_path = os.path.join(application_path, BaseConfig.get_yaml_file())
        with open(config_path, "r", encoding="utf8") as f:
            # return jsonify({'success': True, 'data': f.read()})
            return ConfigController.success(data=f.read())

    @staticmethod
    @config_bp.post('/config/save')
    def config_save():
        config_name = BaseConfig.get_yaml_file()
        config_path = os.path.join(application_path, config_name)
        with open(config_path, "w", encoding="utf8") as f:
            f.write(request.get_data(as_text=True))
        reload_config()
        return ConfigController.success(message='保存配置成功')
    @staticmethod
    @config_bp.put('/config/set/<name>')
    def config_set_instance(name):
        AccountConfig.set_instance(name)
        return ConfigController.success(message=f'成功切换实例:{name}')

    @staticmethod
    @config_bp.route('/config/instances', methods=['GET'])
    def get_instances():
        instances = AccountConfig.get_account_obj()
        for instance in instances['instances']:
            instance['password'] = ''
        return ConfigController.success(data=instances)

    @staticmethod
    @config_bp.route('/config/create_instance', methods=['POST'])
    def create_instance():
        data = request.get_json()
        try:
            AccountConfig.create_instance(data)
            return ConfigController.success("成功创建实例")
        except Exception as e:
            return ConfigController.error(f"创建实例失败：{e.args}")

    @staticmethod
    @config_bp.route('/config/delete/<instance_name>', methods=['GET'])
    def delete_config(instance_name):
        try:
            AccountConfig.delete_instance(instance_name)
            return ConfigController.success(f'成功删除"{instance_name}"')
        except Exception as e:
            return ConfigController.error(e.args)
