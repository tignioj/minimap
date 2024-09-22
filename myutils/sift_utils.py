from mylogger.MyLogger3 import MyLogger
import cv2
import numpy as np
logger = MyLogger('sift_utils')

class MatchException(Exception): pass

def get_good_matches(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                     matcher):
    if small_image is None or keypoints_small is None or descriptors_large is None or descriptors_small is None or len(
            keypoints_large) == 0 or len(descriptors_large) == 0:
        raise MatchException("请传入有效特征点")
    try:
        matches = matcher.knnMatch(descriptors_small, descriptors_large, k=2)
    except Exception as e:
        msg = f'进行匹配的时候出错了，报错信息{e}'
        raise MatchException(msg)
    # 应用比例测试来过滤匹配点
    good_matches = []
    # gms = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
            # gms.append([m])

    return good_matches

def get_match_pts_and_dts(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                     matcher):
    good_matches = get_good_matches(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large, matcher)
    if len(good_matches) < 10: raise MatchException("低质量匹配")
    # 获取匹配点的坐标
    src_pts = np.float32([keypoints_small[m.queryIdx].pt for m in good_matches]).reshape(-1, 2)
    dst_pts = np.float32([keypoints_large[m.trainIdx].pt for m in good_matches]).reshape(-1, 2)
    return src_pts, dst_pts, len(good_matches)

def get_match_position(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                     matcher):
    try:
        # 获取匹配点的坐标
        src_pts, dst_pts, good_match_count = get_match_pts_and_dts(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                         matcher)
        # 使用RANSAC找到变换矩阵
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
        if M is None:
            logger.debug("透视变换失败！！")
            return None

        # 计算小地图的中心点
        h, w = small_image.shape[:2]
        center_point = np.array([[w / 2, h / 2]], dtype='float32')
        center_point = np.array([center_point])
        transformed_center = cv2.perspectiveTransform(center_point, M)
        # 打印小地图在大地图中的中心坐标
        # print("Center of the small map in the large map: ", transformed_center)
        return transformed_center[0][0]
    except MatchException as e:
        logger.error(e)

def get_match_position_with_good_match_count(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                     matcher):
    try:
        # 获取匹配点的坐标
        src_pts, dst_pts, good_match_count = get_match_pts_and_dts(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                         matcher)
        # 使用RANSAC找到变换矩阵
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
        if M is None:
            logger.debug("透视变换失败！！")
            return None, None

        # 计算小地图的中心点
        h, w = small_image.shape[:2]
        center_point = np.array([[w / 2, h / 2]], dtype='float32')
        center_point = np.array([center_point])
        transformed_center = cv2.perspectiveTransform(center_point, M)
        # 打印小地图在大地图中的中心坐标
        # print("Center of the small map in the large map: ", transformed_center)
        return transformed_center[0][0], good_match_count
    except MatchException as e:
        logger.error(e)
    return None,None

def get_match_corner(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                     matcher):
    # 获取匹配点的坐标
    try:
        src_pts, dst_pts, good_match_count = get_match_pts_and_dts(small_image, keypoints_small, descriptors_small, keypoints_large, descriptors_large,
                         matcher)

        h, w = small_image.shape[:2]
        small_img_corners = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]).reshape(-1, 1, 2)

        # 计算单应性矩阵
        H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC)

        # 将角点变换到大地图中
        large_img_corners = cv2.perspectiveTransform(small_img_corners, H)
        return large_img_corners
    except MatchException as e:
        logger.error(e)

