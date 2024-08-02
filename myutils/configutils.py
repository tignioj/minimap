import yaml, os, platform

# _cwd = os.path.dirname(__file__)
_cwd = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.join(_cwd, '../')
def _load_config():
    config_path = os.path.join(PROJECT_PATH, "config.yaml")
    with open(config_path, "r", encoding="utf8") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

cfg = _load_config()
resource_path = cfg['resource_path']

def get_bigmap_path(size=2048):
    return os.path.join(resource_path, 'map', f'combined_image_{size}.png')

def get_keypoints_des_path(size=2048):
    kp = os.path.join(resource_path, 'features', 'sift', f'sift_keypoints_large_blocksize{size}.pkl')
    des = os.path.join(resource_path, 'features', 'sift', f'sift_descriptors_large_blocksize{size}.pkl')
    return kp, des

def get_paimon_icon_path():
    return os.path.join(resource_path, 'template', 'paimeng_icon_trim.png')


if __name__ == '__main__':
    path = get_bigmap_path()
    print(path)
    kp, des = get_keypoints_des_path()
    print(des,kp)
    p = get_paimon_icon_path()
    print(p)
