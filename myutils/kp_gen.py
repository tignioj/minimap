
import pickle, cv2,os
import time

from myutils.configutils import MapConfig, resource_path
import numpy as np

def get_bigmap_path(block_size=2048,map_name='daoqi', version=0):
    # return os.path.join(resource_path, 'map', 'segments', map_file_name)
    return os.path.join(resource_path, 'map', 'segments', f'{map_name}_{block_size}_v{version}.png')

def get_keypoints_des_path(block_size,map_name,version=0):
    kp = os.path.join(resource_path, 'features', 'sift', f'segments', f'sift_keypoints_{block_size}_{map_name}_v{version}.pkl')
    des = os.path.join(resource_path, 'features', 'sift', f'segments', f'sift_descriptors_{block_size}_{map_name}_v{version}.pkl')
    return kp, des


def detect_features_in_blocks(image, process_block_size):
    sift = cv2.SIFT.create()
    keypoints = []
    descriptors = []
    t = time.time()
    height, width = image.shape
    for y in range(0, height, process_block_size):
        for x in range(0, width, process_block_size):
            # 确保块不超出图像范围
            block = image[y:min(y + process_block_size, height), x:min(x + process_block_size, width)]
            kps, descs = sift.detectAndCompute(block, None)
            print('y进度%3.2f' % ((y / height)*100), 'x进度{%3.2f}' % ((x / width)*100), '用时%.3f' % (time.time()-t))
            if kps:
                # 调整块中的关键点位置到整个图像坐标
                for kp in kps:
                    kp.pt = (kp.pt[0] + x, kp.pt[1] + y)
                keypoints.extend(kps)
                if descs is not None:
                    descriptors.append(descs)

    if descriptors:
        descriptors = np.vstack(descriptors)
    else:
        descriptors = None

    print('用时', time.time() - t)
    return keypoints, descriptors


# 分割生成(小内存推荐)
def __generate2(block_size=2048, map_name=None):
    # 读取图像
    large_image = cv2.imread(get_bigmap_path(block_size=block_size,map_name=map_name), 0)

    if large_image is None:
        print("图像加载失败，请检查路径和文件名是否正确。")
        return

    # 分块处理图像
    start_time = time.time()
    keypoints2, descriptors2 = detect_features_in_blocks(
        # 注意此block_size不同于参数的block_size
        # 参数的block_size是图片合成时的大小
        # 这里的process_block_size是指切割成多大的图片来生成特征点
        large_image, 2048)
    print("特征点检测完成，用时: {:.2f}秒".format(time.time() - start_time))

    index = [(kp.pt, kp.size, kp.angle, kp.response, kp.octave, kp.class_id) for kp in keypoints2]

    # 保存关键点和描述符
    kpp, desp = get_keypoints_des_path(block_size,map_name)
    with open(kpp, 'wb') as kp_file:
        pickle.dump(index, kp_file)
    with open(desp, 'wb') as des_file:
        pickle.dump(descriptors2, des_file)

    print("关键点和描述符已保存到文件中。")


# 不分割直接生成特征点：需要运行内存至少16G
def __generate(block_size, map_name):
    sift = cv2.SIFT.create()
    bigmap = cv2.imread(get_bigmap_path(block_size=block_size,map_name=map_name), 0)
    # 检测关键点和计算描述符
    keypoints_large, descriptors_large = sift.detectAndCompute(bigmap, None)
    index = []
    for point in keypoints_large:
        temp = (point.pt, point.size, point.angle, point.response, point.octave, point.class_id)
        index.append(temp)

    # 保存关键点和描述符
    kpp, desp = get_keypoints_des_path(block_size,map_name)
    with open(kpp, 'wb') as kp_file:
        pickle.dump(index, kp_file)
    with open(desp, 'wb') as des_file:
        pickle.dump(descriptors_large, des_file)

# 加载特征点
def load(block_size, map_name, map_version=0):
    kpp, desp = get_keypoints_des_path(block_size, map_name, version=map_version)
    # 读取关键点
    with open( kpp, 'rb') as kp_file:
        index = pickle.load(kp_file)
    keypoints_large = []
    for point in index:
        temp = cv2.KeyPoint(x=point[0][0], y=point[0][1], size=point[1], angle=point[2], response=point[3],
                            octave=point[4], class_id=point[5])
        keypoints_large.append(temp)
    # 读取描述符
    with open(desp, 'rb') as des_file:
        descriptors_large = pickle.load(des_file)
    return keypoints_large, descriptors_large

def __compress(kpp,desp, map_name, block_size, map_version):
    import zipfile
    # 使用 zipfile 模块压缩文件
    output_zip = f"{map_name}_block_{block_size}_v{map_version}.zip"
    with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(kpp, os.path.basename(kpp))  # 使用 os.path.basename 以只存储文件名
        zipf.write(desp, os.path.basename(desp))
    print(f"压缩包已生成：{output_zip}")
def __sift_kp_des_generator():
    feat_folder = os.path.join(resource_path, 'features', 'sift', 'segments')
    if not os.path.exists(feat_folder): os.makedirs(feat_folder)


    """
    生成特征点并保存, 需要较大的内存才能运行
    :return:
    """
    import time
    from myutils.configutils import MapConfig
    start = time.time()
    obj = MapConfig.get_all_map()
    for key in obj.keys():
        map_obj = obj.get(key)
        map_name = map_obj.get('img_name')
        map_version = map_obj.get('version')
        block_size = 2048
        kp, des = get_keypoints_des_path(block_size=block_size, map_name=map_name, version=map_version)
        if not os.path.exists(kp):
            gen_time = time.time()
            print(f'正在生成{block_size}, {map_name}')
            __generate2(block_size=block_size, map_name=map_name)
            print(f'生成{block_size}, {map_name} 用时{time.time() - gen_time}')
        # __compress(kp,des, map_name=map_name,block_size=block_size, map_version=map_version)

        block_size = 256
        kp, des = get_keypoints_des_path(block_size=block_size, map_name=map_name, version=map_version)
        gen_time = time.time()
        if not os.path.exists(kp):
            print(f'正在生成{block_size}, {map_name}')
            __generate2(block_size=block_size, map_name=map_name)
            print(f'生成{block_size}, {map_name} 用时{time.time() - gen_time}')
        # __compress(kp,des, map_name=map_name,block_size=block_size, map_version=map_version)

    print('总计用时', time.time() - start)

if __name__ == '__main__':
    __sift_kp_des_generator()