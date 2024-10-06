from io import BytesIO

import cv2
from flask import Blueprint, request, jsonify, send_file

from controller.BaseController import BaseController
from matchmap.gia_rotation import RotationGIA
from matchmap.sifttest.sifttest6 import MiniMap
from capture.capture_factory import capture
from myutils.imgutils import crop_img, cvimg_to_base64
from server.controller.ServerBaseController import ServerBaseController
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('minimap_controller')

minimap_bp = Blueprint('minimap', __name__)
minimap = MiniMap()
# minimap.get_position()
rotate = RotationGIA(False)
capture.add_observer(rotate)
capture.add_observer(minimap)

class MiniMapController(ServerBaseController):
    @staticmethod
    @minimap_bp.route('/usermap/get_position', methods=['GET'])
    def get_user_map_position():
        pos =  minimap.get_user_map_position()
        if pos: return MiniMapController.success(data=pos)
        else: return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/usermap/get_scale', methods=['GET'])
    def get_user_map_scale():  # 抛出异常：jsondecode error
        # return jsonify(minimap.get_user_map_scale())
        scale = minimap.get_user_map_scale()
        if scale: return MiniMapController.success(data=scale)
        else: return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/usermap/create_cache', methods=['POST'])
    def create_cached_local_map():
        data = request.json  # 获取JSON数据
        center_pos = data.get('center_pos')
        use_middle_map = data.get('use_middle_map')
        result = False
        if center_pos:
            # 用户传过来的是相对位置，要转换成绝对位置
            pix_pos = minimap.relative_axis_to_pix_axis(center_pos)
            result = minimap.global_match_cache(pix_pos)
        elif use_middle_map:
            # 现在传送移动地图不是移动到中心点，传送的时候禁止用此方法创建缓存
            pos = minimap.get_user_map_position()
            if pos:
                pos = minimap.relative_axis_to_pix_axis(pos)
                result = minimap.global_match_cache(pos)
        else:
            result = minimap.create_local_map_cache_thread()

        if result: return MiniMapController.success()
        else: return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/minimap/get_position', methods=['GET'])
    def get_position():
        absolute_position = request.args.get('absolute_position', 0) == '1'
        pos = minimap.get_position(absolute_position=absolute_position)
        if pos:
            return MiniMapController.success(data=pos)
        else: return MiniMapController.error()
    @staticmethod
    @minimap_bp.route('/minimap/choose_map', methods=['GET'])
    def choose_map():
        map_name = request.args.get('map_name')
        minimap.choose_map(map_name)
        return MiniMapController.success()

    @staticmethod
    @minimap_bp.route('/minimap/get_insert_node', methods=['GET'])
    def get_insert_node():
        pos = minimap.get_position()
        if pos is None or minimap.map_2048 is None:
            return MiniMapController.error()

        from myexecutor.BasePathExecutor2 import Point
        if capture.is_flying(): move_mode = Point.MOVE_MODE_FLY
        elif capture.is_swimming(): move_mode = Point.MOVE_MODE_SWIM
        else: move_mode = Point.MOVE_MODE_NORMAL
        map_name = minimap.map_2048.map_name

        data = {
            'position': pos,
            'move_mode': move_mode,
            'map_name': map_name
        }
        return MiniMapController.success(data=data)

    @staticmethod
    @minimap_bp.route('/minimap/get_rotation', methods=['GET'])
    def get_rotation():
        img = capture.get_mini_map()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rot = rotate.predict_rotation(img)
        if rot is not None: return ServerBaseController.success(data=rot)
        else: return ServerBaseController.error()

    from io import BytesIO

    @staticmethod
    @minimap_bp.route('/minimap/get_region_map', methods=['GET'])
    def get_region_map():
        x = request.args.get('x')
        y = request.args.get('y')
        width = request.args.get('width')
        scale = request.args.get('scale')
        country = request.args.get('region')
        # from myutils.load_save_sift_keypoint import get_sift_map, SiftMap, cn_text_map

        # if cn_text_map.get(country) is None:
        #     return ServerBaseController.error(f'{country}区域信息无法识别'), 400

        sift_map = MiniMap.get_sift_map(block_size=2048, map_name=country)
        try:
            x = int(float(x))
            y = int(float(y))
            width = int(width)
            if scale: scale = float(scale)
            else: scale = 1
        except ValueError as e:
            logger.error(e)
            return MiniMapController.error(message='解析坐标失败'), 500

        pix_pos = (sift_map.center[0] + x, sift_map.center[1] + y)
        tem_local_map = crop_img(sift_map.img, pix_pos[0], pix_pos[1], crop_size=width, scale=scale)
        if tem_local_map is None:
            logger.error('无法裁剪地图')
            return MiniMapController.error(message='无法裁剪地图'), 500

        _, img_encoded = cv2.imencode('.jpg', tem_local_map)
        return send_file(BytesIO(img_encoded), mimetype='image/jpeg')


    @staticmethod
    @minimap_bp.route('/minimap/get_local_map', methods=['GET'])
    def get_local_map():
        local_map_pos = minimap.local_map_pos
        if local_map_pos is None:
            # return jsonify({'result': False})
            return MiniMapController.error()

        pix_pos = minimap.local_map_pos
        width = minimap.local_map_size
        tem_local_map = crop_img(large_map, pix_pos[0], pix_pos[1], width)
        img_base64 = cvimg_to_base64(tem_local_map)
        data = {
            'position': pix_pos,
            'xywh': None,
            'img_base64': img_base64
        }
        return MiniMapController.success(data=data)

