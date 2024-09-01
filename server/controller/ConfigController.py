import os

from flask import Blueprint, jsonify, request
from server.controller.ServerBaseController import ServerBaseController
config_bp = Blueprint('config_bp', __name__)

class ConfigController(ServerBaseController):
    @staticmethod
    @config_bp.route('/config/get')
    def config_get():
        from myutils.configutils import application_path, config_name
        config_path = os.path.join(application_path, config_name)
        with open(config_path, "r", encoding="utf8") as f:
            # return jsonify({'success': True, 'data': f.read()})
            return ConfigController.success(data=f.read())

    # @app.route('/config/edit')
    # def config_editor():
    #     from myutils.configutils import application_path, config_name
    #     config_path = os.path.join(application_path, config_name)
    #     with open(config_path, "r", encoding="utf8") as f:
    #         txt = f.read()
    #     return render_template('config_editor.html', config_text=txt)

    # ##############################################

    @staticmethod
    @config_bp.post('/config/save')
    def config_save():
        from myutils.configutils import application_path, config_name, reload_config
        config_path = os.path.join(application_path, config_name)
        with open(config_path, "w", encoding="utf8") as f:
            f.write(request.get_data(as_text=True))
        reload_config()
        return ConfigController.success(message='保存配置成功')

