import json
import os

from flask import Blueprint, jsonify, request, render_template

from myutils.configutils import resource_path, get_config
from myutils.jsonutils import getjson_path_byname

filemanager_bp = Blueprint('filemanager', __name__)

class FileManagerController:
    @filemanager_bp.route('/pathlist/edit/<filename>')
    def edit(filename):
        return render_template('edit.html', filename=filename)

    @staticmethod
    @filemanager_bp.route('/pathlist/get/<filename>')
    def getfile(filename: str):
        p = getjson_path_byname(filename.strip())
        if os.path.exists(p):
            with open(p, 'r', encoding='utf8') as f:
                data = json.load(f)
                return jsonify({'success': True, 'data': data})
        else:
            return jsonify({'success': False, 'data': '文件不存在'})

    @staticmethod
    @filemanager_bp.post('/pathlist/save/<filename>')
    def savejson(filename):
        p = getjson_path_byname(filename)
        data = request.get_data(as_text=True)
        old_json_name = request.args.get('old_json_name')

        if data is None:
            return jsonify({'success': False, 'data': None})
        if os.path.exists(p):
            with open(p, 'w', encoding='utf8') as f:
                f.write(data)
            # 如果旧的文件名称和新的文件名称不同，则替换旧的文件名称
            if old_json_name != filename:
                op = getjson_path_byname(old_json_name)
                if os.path.exists(op): os.rename(op, filename)
                # 更新清单中的名称

            return jsonify({'success': True})

        # 如果文件不存在，则保存到默认目录
        else:
            p = os.path.join(resource_path, 'pathlist', 'default', filename)
            with open(p, 'w', encoding='utf8') as f:
                f.write(data)
        return jsonify({'success': False, 'data': f'已保存到{p}'})

    @staticmethod
    @filemanager_bp.route('/pathlist/list')
    def pathlist():
        p = get_config('points_path', os.path.join(resource_path, 'pathlist'))
        folders = []
        try:
            dirs = os.listdir(p)
            for d in dirs:
                subdir = os.path.join(p, d)
                files = os.listdir(subdir)
                folders.append({
                    'name': d,
                    'files': files
                })
            return jsonify({'success': True, 'data': folders})
        except FileNotFoundError as e:
            return jsonify({'success': False, 'data': '目录不存在'})


