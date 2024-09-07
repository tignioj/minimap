import json,os
import re
from typing import List
from myexecutor.BasePathExecutor2 import Point, PointEncoder
from datetime import datetime
from myutils.configutils import resource_path
class FolderNameException(Exception):pass

def generate_temp_file(file_name, file_content):
    from myutils.configutils import resource_path
    tmp_folder = os.path.join(resource_path, 'temp')
    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)
    temp_file_path = os.path.join(tmp_folder, file_name)
    with open(temp_file_path, 'w', encoding="utf8") as f:
        f.write(file_content)
    return temp_file_path


def is_valid_directory_name(name: str) -> bool:
    # 检查目录名称是否为空或长度过长
    if not name or len(name) > 255:
        raise FolderNameException('目录长度不能过长(>255)或者为空！')

    # 定义不允许使用的非法字符
    invalid_chars = r'[<>:"/\\|?*\']'

    # 检查是否包含非法字符
    if re.search(invalid_chars, name):
        raise FolderNameException('包含非法字符')

    # 检查是否以空格或点结尾
    if name.startswith(' ') or name.endswith((' ', '.')):
        raise FolderNameException('禁止空白结尾或者英文句号结尾')

    # Windows 系统中的保留字
    reserved_names = {"CON", "PRN", "AUX", "NUL",
                      "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                      "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}

    # 检查是否为保留字
    if name.upper() in reserved_names:
        raise FolderNameException('禁止使用windows保留字')

    return True


def getjson_path_byname(filename):
    # 获取当前脚本所在的目录
    folder_name = filename.split("_")[0]
    from myutils.configutils import resource_path

    is_valid_directory_name(folder_name)
    is_valid_directory_name(filename)

    # 拼接资源目录的路径
    file = os.path.join(resource_path,'pathlist',folder_name, filename)
    return file
