import base64
import os.path
import cv2
from mylogger.MyLogger3 import MyLogger
logger = MyLogger(__name__)
import numpy as np


def crop_square_with_padding(image, x, y, square_size):
    """
    裁剪图片，超出边界部分用白色背景填充
    :param image:
    :param x:
    :param y:
    :param square_size:
    :return:
    """
    # 读取图像

    # 获取图像的高度和宽度
    height, width = image.shape[:2]

    # 计算裁剪的左上角和右下角坐标
    half_size = square_size // 2
    x1 = int(x - half_size)
    y1 = int(y - half_size)
    x2 = int(x + half_size)
    y2 = int(y + half_size)

    # 创建一个白色背景的正方形图像
    # white_background = np.ones((square_size, square_size, 3), dtype=np.uint8) * 255
    white_background = np.ones((square_size, square_size), dtype=np.uint8) * 255

    # 计算需要从原图中裁剪的区域（确保不会超出边界）
    crop_x1 = max(0, x1)
    crop_y1 = max(0, y1)
    crop_x2 = min(width, x2)
    crop_y2 = min(height, y2)

    # 计算裁剪区域的宽高，确保裁剪区域是正数
    crop_width = crop_x2 - crop_x1
    crop_height = crop_y2 - crop_y1

    if crop_width <= 0 or crop_height <= 0:
        raise ValueError("裁剪区域无效，可能中心点超出图片范围")

    # 计算裁剪区域相对于背景的位置，并将结果转换为整数
    background_x1 = max(0, -x1)
    background_y1 = max(0, -y1)
    background_x2 = int(background_x1 + crop_width)
    background_y2 = int(background_y1 + crop_height)

    # 确保所有切片索引是整数
    crop_x1 = int(crop_x1)
    crop_x2 = int(crop_x2)
    crop_y1 = int(crop_y1)
    crop_y2 = int(crop_y2)

    # 将裁剪区域复制到白色背景
    white_background[background_y1:background_y2, background_x1:background_x2] = image[crop_y1:crop_y2, crop_x1:crop_x2]

    return white_background

def crop_square(img, d):
    """
    从输入图像中裁剪出一个以图像中心为中心的正方形区域，边长为 2*d。
    :param img:
    :param d:
    :return:
    """
    height, width = img.shape[:2]
    center = (height // 2, width // 2)
    return img[center[0] - d:center[0] + d, center[1] - d:center[1] + d]

def crop_img(large_image, center_x, center_y, crop_size=500, scale=None):
    if large_image is None: return None
    # 假设已经获取到了center_x 和 center_y
    # 1. 计算裁剪区域的左上角坐标
    # 3. 裁剪图片
    # 确保裁剪区域在大图范围内
    try:
        cropped_image = crop_square_with_padding(large_image, center_x, center_y, crop_size)
        if cropped_image.shape[0] < 1 or cropped_image.shape[1] < 1:
            print('Cropped image too small')
            return None
    except ValueError as e:
        logger.error(e.args)
        return None

    if scale:
        if scale < 0.1: scale = 0.1
        elif scale > 10: scale = 10
        height, width = cropped_image.shape[:2]
        center = (width // 2, height // 2)

        # 定义放大倍数
        scale_factor = scale

        # 创建仿射变换矩阵
        matrix = cv2.getRotationMatrix2D(center, 0, scale_factor)

        # 应用缩放（放大）
        cropped_image = cv2.warpAffine(cropped_image, matrix, (width, height))

    # 4. 保存裁剪后的图片（可选）
    # cv2.imwrite('cropped_image.jpg', cropped_image)

    # 可选：显示裁剪后的图片
    # cv2.imshow('Cropped Image', cropped_image)
    # key = cv2.waitKey(1)
    # if key == ord('q'):
    #     cv2.destroyAllWindows()
    return cropped_image

def cvimg_to_base64(cvimg):
    _, img_encoded = cv2.imencode('.jpg', cvimg)
    return base64.b64encode(img_encoded).decode("utf-8")

if __name__ == '__main__':
    from myutils.configutils import resource_path
    png = os.path.join(resource_path,  'map', 'segments', 'shachongsuidao-shangfangtonglu_2048.png' )
    img = cv2.imread(png)
    square = crop_square_with_padding(img, 0,100, 300)
    cv2.imshow('img',square)
    cv2.waitKey(0)
    cv2.destroyAllWindows()