import yaml, os

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
def load_config():
    config_path = os.path.join(application_path, config_name)
    with open(config_path, "r", encoding="utf8") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
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
    path = get_bigmap_path()
    print(path)
    kp, des = get_keypoints_des_path()
    print(kp, des)
    p = get_paimon_icon_path()
    print(p)
    port = cfg.get('minimap').get('port')
    print(port)
