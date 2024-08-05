import time
import cv2
import numpy as np
import os
import pickle
from myutils.configutils import get_keypoints_des_path

def detect_features_in_blocks(image, block_size):
    sift = cv2.SIFT_create()
    keypoints = []
    descriptors = []
    t = time.time()
    height, width = image.shape
    for y in range(0, height, block_size):
        for x in range(0, width, block_size):
            # 确保块不超出图像范围
            block = image[y:min(y + block_size, height), x:min(x + block_size, width)]
            kps, descs = sift.detectAndCompute(block, None)
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


def kpgen(block_size=2048):
    # 读取图像
    current_path = os.getcwd()
    large_image = cv2.imread(current_path + '/../resources/map/combined_image_{}.png'.format(block_size),
                             cv2.IMREAD_GRAYSCALE)

    if large_image is None:
        print("图像加载失败，请检查路径和文件名是否正确。")
        return

    # 分块处理图像
    start_time = time.time()
    keypoints2, descriptors2 = detect_features_in_blocks(large_image, block_size)
    print("特征点检测完成，用时: {:.2f}秒".format(time.time() - start_time))

    index = [(kp.pt, kp.size, kp.angle, kp.response, kp.octave, kp.class_id) for kp in keypoints2]

    # 保存关键点和描述符
    with open('sift_keypoints_large_blocksize{}.pkl'.format(block_size), 'wb') as kp_file:
        pickle.dump(index, kp_file)
    with open('sift_descriptors_large_blocksize{}.pkl'.format(block_size), 'wb') as des_file:
        pickle.dump(descriptors2, des_file)

    print("关键点和描述符已保存到文件中。")


def load(block_size=2048):
    kpp, desp = get_keypoints_des_path(block_size)
    # 读取关键点
    with open(kpp, 'rb') as kp_file:
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

# 将关键点的数据转换为可以序列化的格式
# 只能在google lab运行，需要运行内存至少100G
def save(img):
    # 假设 'surf' 是已经初始化的cv2.xresources/features2d.SURF对象
    # 'bigmap' 是大图像的变量
    surf = cv2.SIFT.create()
    # 检测关键点和计算描述符
    keypoints_large, descriptors_large = surf.detectAndCompute(img, None)
    index = []
    for point in keypoints_large:
        temp = (point.pt, point.size, point.angle, point.response, point.octave, point.class_id)
        index.append(temp)

    # 保存关键点和描述符
    with open('sift_paimon_keypoints.pkl', 'wb') as kp_file:
        pickle.dump(index, kp_file)
    with open('sift_paimon_descriptors.pkl', 'wb') as des_file:
        pickle.dump(descriptors_large, des_file)


if __name__ == '__main__':
    # kpgen(256)
    # from myutils.configutils import get_paimon_icon_path
    # get_paimon_icon_path()
    # save(cv2.imread(get_paimon_icon_path(), cv2.IMREAD_GRAYSCALE))
    k,d = load(2048)
    print(d.shape)