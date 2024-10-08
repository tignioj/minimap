import os

from flask import Blueprint, jsonify, request
from server.controller.ServerBaseController import ServerBaseController
config_bp = Blueprint('config_bp', __name__)

class ConfigController(ServerBaseController):
    @staticmethod
    @config_bp.route('/config/get')
    def config_get():
        from myutils.configutils import application_path, BaseConfig
        config_path = os.path.join(application_path, BaseConfig.get_yaml_file())
        with open(config_path, "r", encoding="utf8") as f:
            # return jsonify({'success': True, 'data': f.read()})
            return ConfigController.success(data=f.read())

    @staticmethod
    @config_bp.post('/config/save')
    def config_save():
        from myutils.configutils import BaseConfig, application_path, reload_config
        config_name = BaseConfig.get_yaml_file()
        config_path = os.path.join(application_path, config_name)
        with open(config_path, "w", encoding="utf8") as f:
            f.write(request.get_data(as_text=True))
        reload_config()
        return ConfigController.success(message='保存配置成功')
    @staticmethod
    @config_bp.put('/config/set/<name>')
    def config_set_instance(name):
        from myutils.configutils import BaseConfig
        BaseConfig.set_instance(name)
        return ConfigController.success(message=f'成功切换实例:{name}')

    @staticmethod
    @config_bp.route('/config/instances', methods=['GET'])
    def get_instances():
        from myutils.configutils import BaseConfig
        instances = BaseConfig.get_instances()
        for instance in instances['instances']:
            instance['password'] = ''
        return ConfigController.success(data=instances)
