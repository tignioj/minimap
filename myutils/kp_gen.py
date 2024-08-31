import time
import cv2
import numpy as np
import os
import pickle
from myutils.configutils import get_keypoints_des_path

def save_sigma(x,y,block,sigma):
    kps, descs = cv2.SIFT.create(sigma=sigma).detectAndCompute(block, None)
    block_kp = cv2.drawKeypoints(block, kps, None, color=(0, 0, 255))
    cv2.imwrite(f'img/{x}_{y}_sigma{sigma}.jpg', block_kp)

def save_contrast(x,y,block,contrast):
    kps, descs = cv2.SIFT.create(contrastThreshold=contrast).detectAndCompute(block, None)
    block_kp = cv2.drawKeypoints(block, kps, None, color=(0, 0, 255))
    __putText(block_kp, text=str(len(descs)))
    cv2.imwrite(f'contrast/{x}_{y}_contrast{contrast}.jpg', block_kp)

def __putText(img, text, org=(0,20), font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=0.5, color=(0,0,255), thickness=2):
    # 在图像上添加文字
    cv2.putText(img, text, org, font, font_scale, color, thickness)
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
                # print(len(descs))
                # if len(descs) < 1000 and len(descs>200):
                #     block_kp = cv2.drawKeypoints(block, kps, None, color=(0, 0, 255))
                #     __putText(block_kp, text=str(len(descs)))
                #     cv2.imwrite(f'contrast/{x}_{y}.jpg', block_kp)
                #     contrast = sift.getContrastThreshold()
                #     save_contrast(x,y,block,contrast-0.01)
                #     save_contrast(x,y,block,contrast-0.02)
                #     save_contrast(x,y,block,contrast-0.03)

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


def get_big_map_path(version=5.0, block_size=2048):
    from myutils.configutils import resource_path
    return os.path.join(resource_path,'map', f'version{version}', f'map{version}_{block_size}.png')

def kpgen(block_size=2048, version=5.0):
    # 读取图像
    current_path = os.getcwd()
    # large_image = cv2.imread(current_path + '/../resources/map/combined_image_{}.png'.format(block_size), cv2.IMREAD_GRAYSCALE)
    large_image = cv2.imread(get_big_map_path(version=version,block_size=block_size), cv2.IMREAD_GRAYSCALE)

    if large_image is None:
        print("图像加载失败，请检查路径和文件名是否正确。")
        return

    # 分块处理图像
    start_time = time.time()
    keypoints2, descriptors2 = detect_features_in_blocks(large_image, 2048)
    print("特征点检测完成，用时: {:.2f}秒".format(time.time() - start_time))

    index = [(kp.pt, kp.size, kp.angle, kp.response, kp.octave, kp.class_id) for kp in keypoints2]

    # 保存关键点和描述符
    with open(f'sift_keypoints_version{version}_blocksize{block_size}.pkl', 'wb') as kp_file:
        pickle.dump(index, kp_file)
    with open(f'sift_descriptors_version{version}_blocksize{block_size}.pkl', 'wb') as des_file:
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


if __name__ == '__main__':
    kpgen(2048)
    k,d = load(2048)
    print(d.shape)