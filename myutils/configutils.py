import os
# 创建 YAML 对象，保留注释
from ruamel.yaml import YAML
yaml = YAML()
yaml.preserve_quotes = True

import sys
config_name = 'config.dev.yaml'
application_path = '.'
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    application_path = os.path.join(application_path, '_internal')
    config_name = 'config.yaml'
elif __file__:
    application_path = os.path.dirname(os.path.dirname(__file__))

PROJECT_PATH = application_path

YAML_KEY_DEFAULT_FIGHT_TEAM = 'default_fight_team'
YAML_KEY_DEFAULT_FIGHT_DURATION = 'fight_duration'


def load_config():
    config_path = get_config_file_path()
    with open(config_path, "r", encoding="utf8") as stream:
        return yaml.load(stream)

def get_config_file_path():
    return os.path.join(application_path, config_name)

def reload_config():
    global cfg,resource_path
    cfg = load_config()
    if cfg.get('resources_path') is not None: resource_path = cfg['resource_path']
    else: resource_path = os.path.join(PROJECT_PATH, 'resources')

def get_config(key, default=None):
    return cfg.get(key, default)

cfg = load_config()

if cfg.get('resources_path') is not None:
    resource_path = cfg['resource_path']
else:
    resource_path = os.path.join(PROJECT_PATH, 'resources')

def set_config(key, value=None):
    reload_config()
    old_val = cfg[key]
    try:
        cfg[key] = value
        config_path = get_config_file_path()
        with open(config_path, "w", encoding="utf8") as f:
            yaml.dump(cfg, f)
    except Exception as e:
        # 失败回滚
        cfg[key] = old_val
        raise e


def get_bigmap_path(size=2048,version=5.0):
    # return os.path.join(resource_path, 'map', f'combined_image_{size}.png')
    return os.path.join(resource_path, 'map',f'version{version}', f'map{version}_{size}.png')

def get_keypoints_des_path(size=2048, version=5.0):
    kp = os.path.join(resource_path, 'features', 'sift', f'version{version}', f'sift_keypoints_version{version}_blocksize{size}.pkl')
    des = os.path.join(resource_path, 'features', 'sift', f'version{version}', f'sift_descriptors_version{version}_blocksize{size}.pkl')
    # kp = os.path.join(resource_path, 'features', 'sift', f'sift_keypoints_large_blocksize{size}.pkl')
    # des = os.path.join(resource_path, 'features', 'sift', f'sift_descriptors_large_blocksize{size}.pkl')
    return kp, des

def get_paimon_icon_path():
    return os.path.join(resource_path, 'template', 'paimeng_icon_trim.png')

def get_user_folder():
    user_folder = os.path.join(resource_path, 'user')
    if not os.path.exists(user_folder): os.mkdir(user_folder)
    return user_folder

if __name__ == '__main__':
    df = get_config('default_fight_team')
    print(df)
    set_config('default_fight_team', '1.txt')
    print(get_config('default_fight_team'))
