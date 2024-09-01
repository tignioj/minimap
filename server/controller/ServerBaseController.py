from flask import jsonify


class ServerBaseController:
    @staticmethod
    def success(message=None, data=None, status=None):
        return jsonify({'success': True, 'status': status, 'message': message, 'data': data})

    @staticmethod
    def error(message=None, status=None):
        return jsonify({'success': False, 'status': status, 'message': message})
