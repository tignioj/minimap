import base64

import cv2
def crop_img(large_image, center_x, center_y, crop_size=500, scale=None):
    if large_image is None: return None
    # 假设已经获取到了center_x 和 center_y
    # 1. 计算裁剪区域的左上角坐标
    left = int(center_x - crop_size / 2)
    top = int(center_y - crop_size / 2)

    # 3. 裁剪图片
    # 确保裁剪区域在大图范围内
    cropped_image = large_image[top:top + crop_size, left:left + crop_size]
    if cropped_image.shape[0] < 1 or cropped_image.shape[1] < 1:
        print('Cropped image too small')
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