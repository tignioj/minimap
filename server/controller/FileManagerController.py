import json
import os

from flask import Blueprint, jsonify, request, render_template

from myutils.configutils import resource_path
from server.controller.ServerBaseController import ServerBaseController
from server.service.FileManagerService import FileManagerService, FileManagerServiceException

filemanager_bp = Blueprint('filemanager', __name__)


class FileManagerController(ServerBaseController):

    @staticmethod
    @filemanager_bp.route('/pathlist/get/<filename>')
    def getfile(filename: str):
        try:
            data = FileManagerService.getfile(filename)
            return FileManagerController.success(data=data)
        except FileManagerServiceException as e:
            return FileManagerController.error(message=e.args)
    @staticmethod
    @filemanager_bp.post('/pathlist/save/<old_filename>')
    def savejson(old_filename:str):
        new_filename = request.args.get('new_filename', '').strip()
        old_filename = old_filename.strip()
        data = request.json
        if data is None:
            return FileManagerController.error('空数据，无法保存！')
        try:
            new_file_path = FileManagerService.save_json(data=data,old_filename=old_filename, new_filename=new_filename)
            data = {'new_filename': new_filename, 'full_path': new_file_path}
            return FileManagerController.success(data=data)
        except FileManagerServiceException as e:
            return FileManagerController.error(message=e.args)

    @staticmethod
    @filemanager_bp.post('/pathlist/delete')
    def deletefiles():
        data = request.json

        files = data.get('files', [])
        files_removed = FileManagerService.removeFiles(files)

        folders = data.get('folders', [])
        folders_removed = FileManagerService.removeFolders(folders)

        return FileManagerController.success(data={'files_removed': files_removed , 'folders_removed': folders_removed},
                                             message=f'移除了{len(files_removed)}个文件, {len(folders_removed)}个文件夹')

    @staticmethod
    @filemanager_bp.route('/pathlist/list')
    def pathlist():
        p = os.path.join(resource_path, 'pathlist')
        folders = []
        try:
            dirs = os.listdir(p)
            for d in dirs:
                if d.startswith("."):  # 跳过隐藏目录
                    continue
                subdir = os.path.join(p, d)
                files = os.listdir(subdir)
                folders.append({
                    'name': d,
                    'files': files
                })
            return FileManagerController.success(data=folders)
        except FileNotFoundError as e:
            return FileManagerController.error(message='目录不存在')


