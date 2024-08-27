import cv2
import numpy as np
from capture.capture_factory import capture
def find_all_icon_from_screen(template_image, show_result=False):
    from myutils.configutils import resource_path
    # 传送锚点流程
    # 加载地图位置检测器
    # template_image = cv2.imread(os.path.join(resource_path, "template", "icon_mission.jpg"))
    gray_template = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)

    original_image = capture.get_screenshot().copy()
    gray_original = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    # 获取模板图像的宽度和高度
    w, h = gray_template.shape[::-1]

    # 将小图作为模板，在大图上进行匹配
    result = cv2.matchTemplate(gray_original, gray_template, cv2.TM_CCOEFF_NORMED)

    # 设定阈值
    threshold = 0.85
    # 获取匹配位置
    locations = np.where(result >= threshold)

    mission_screen_points = []
    prev_point = None
    # 绘制匹配结果
    from myutils.executor_utils import euclidean_distance
    for pt in zip(*locations[::-1]):
        center_x = pt[0] + w // 2
        center_y = pt[1] + h // 2
        if prev_point is None:
            prev_point = pt
            mission_screen_points.append((center_x, center_y))

        elif euclidean_distance(prev_point, pt) > 10:
            mission_screen_points.append((center_x, center_y))
            prev_point = pt

        cv2.rectangle(original_image, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)

    # 显示结果
    if show_result:
        original_image = cv2.resize(original_image, None, fx=0.5, fy=0.5)
        cv2.imshow('Matched Image', original_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return mission_screen_points

if __name__ == '__main__':
    import os
    from myutils.configutils import resource_path
    # template_image = cv2.imread(os.path.join(resource_path, "template", "icon_dimai_money.jpg"))
    template_image = cv2.imread(os.path.join(resource_path, "template", "icon_waypoint.jpg"))
    print(find_all_icon_from_screen(template_image, show_result=True))
