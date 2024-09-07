import json
import os
import re

from flask import request

import mylogger.MyLogger3
from myutils.configutils import resource_path
from myutils.fileutils import getjson_path_byname, is_valid_directory_name, FolderNameException
from server.service.TodoService import TodoService
logger = mylogger.MyLogger3.MyLogger('filemanager_service')

class FileManagerServiceException(Exception):pass
class FileManagerService:

    @staticmethod
    def removeFiles(files):
        removed_files = []
        for file in files:
            file_path = getjson_path_byname(file)
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_files.append(file)
        # 更新清单
        TodoService.removeFiles(removed_files)

        return removed_files

    @staticmethod
    def removeFolders(folders):
        removed_folders = []
        for folder in folders:
            folder_path = os.path.join(resource_path, 'pathlist', folder)
            if os.path.exists(folder_path):
                try:
                    os.rmdir(folder_path)
                    removed_folders.append(folder)
                except: pass
        return removed_folders

    @staticmethod
    def getfile(filename):
        p = getjson_path_byname(filename.strip())
        if os.path.exists(p):
            with open(p, 'r', encoding='utf8') as f:
                data = json.load(f)
                return data
        raise FileManagerServiceException('文件不存在')

    @staticmethod
    def save_json(data,old_filename, new_filename):
        # 删除旧数据，保存新数据
        old_filename_path = getjson_path_byname(old_filename)
        if data is None: raise FileManagerServiceException('空数据，无法保存')
        if not new_filename or not new_filename.strip().endswith('.json'):
            raise FileManagerServiceException('文件名称异常')

        # 尝试从文件名提取目录
        filename_split = new_filename.split('_')
        extract_folder = filename_split[0]
        # 目录名称校验，禁止使用路径分隔符号
        try:
            is_valid_directory_name(extract_folder)
        except FolderNameException as e:
            raise FileManagerServiceException(e.args)

        # 如果提取到目录, 则检查目录是否存在, 不存在则创建
        extract_folder_path = os.path.join(resource_path, 'pathlist', extract_folder)
        if not os.path.exists(extract_folder_path):
            os.mkdir(extract_folder_path)

        new_filename_path = os.path.join(extract_folder_path, new_filename)
        with open(new_filename_path, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            # f.write(data)
        # 更新清单中的名称
        TodoService.updateFileName(old_filename=old_filename, new_filename=new_filename)

        # 删除旧数据
        if old_filename != new_filename:
            if os.path.exists(old_filename_path) and old_filename_path.endswith(".json"):
                logger.debug(f'删掉旧文件{old_filename_path}')
                os.remove(old_filename_path)

        return new_filename_path

if __name__ == '__main__':
    # old_name= 'undefined_蒙德_0个_20240901_064844.json'
    # data = FileManagerService.getfile(old_name)
    # print(data)
    # FileManagerService.save_json(data=data, old_filename=old_name, new_filename='甜甜花1_测试1.json')
    result = FileManagerService.removeFolders(['undefined', 'test1'])
    print(result)
