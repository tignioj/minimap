from io import BytesIO

import cv2
from flask import Blueprint, request, jsonify, send_file
from server.controller.ServerBaseController import ServerBaseController
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('minimap_controller')
from server.service.MinimapService import MinimapService
minimap_bp = Blueprint('minimap', __name__)

class MiniMapController(ServerBaseController):
    @staticmethod
    @minimap_bp.route('/usermap/get_position', methods=['GET'])
    def get_user_map_position():
        try:
            pos = MinimapService.get_user_map_position()
            if pos is not None:
                return MiniMapController.success(data=pos)
            else:
                return MiniMapController.error('无法获取大地图位置')
        except Exception as e:
            return MiniMapController.error(e.args)

    @staticmethod
    @minimap_bp.route('/usermap/get_scale', methods=['GET'])
    def get_user_map_scale():  # 抛出异常：jsondecode error
        scale = MinimapService.get_user_map_scale()
        if scale is not None:
            return MiniMapController.success(data=scale)
        else: return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/usermap/create_cache', methods=['POST'])
    def create_cached_local_map():
        data = request.json  # 获取JSON数据
        center_pos = data.get('center_pos')
        use_middle_map = data.get('use_middle_map')
        result = MinimapService.create_cached_local_map(center_pos, use_middle_map)
        if result: return MiniMapController.success()
        else: return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/minimap/get_position', methods=['GET'])
    def get_position():
        absolute_position = request.args.get('absolute_position', 0) == '1'
        pos = MinimapService.get_position(absolute_position=absolute_position)
        if pos:
            return MiniMapController.success(data=pos)
        else: return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/minimap/get_position_rotation', methods=['GET'])
    def get_position_and_rotation():
        absolute_position = request.args.get('absolute_position', 0) == '1'
        pos, rot = MinimapService.get_position_and_rotation(absolute_position=absolute_position)
        data = {'position': pos, 'rotation': rot}
        if pos:
            return MiniMapController.success(data=data)
        else:
            return MiniMapController.error()

    @staticmethod
    @minimap_bp.route('/minimap/choose_map', methods=['GET'])
    def choose_map():
        map_name = request.args.get('map_name')
        MinimapService.choose_map(map_name)
        return MiniMapController.success()

    @staticmethod
    @minimap_bp.route('/minimap/get_insert_node', methods=['GET'])
    def get_insert_node():
        data = MinimapService.get_insert_node()
        if data is None:
            return MiniMapController.error()
        return MiniMapController.success(data=data)

    @staticmethod
    @minimap_bp.route('/minimap/get_rotation', methods=['GET'])
    def get_rotation():
        rot = MinimapService.get_rotation(use_alpha=False)
        if rot is not None:
            return ServerBaseController.success(data=rot)
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
        try:
            region_map = MinimapService.get_region_map(x=x,y=y, width=width, scale=scale,country=country)
        except Exception as e:
            return ServerBaseController.error(e.args)

        _, img_encoded = cv2.imencode('.jpg', region_map)
        return send_file(BytesIO(img_encoded), mimetype='image/jpeg')


    @staticmethod
    @minimap_bp.route('/minimap/get_local_map', methods=['GET'])
    def get_local_map():
        pass
        # local_map_pos = minimap.local_map_pos
        # if local_map_pos is None:
        #     # return jsonify({'result': False})
        #     return MiniMapController.error()
        #
        # pix_pos = minimap.local_map_pos
        # width = minimap.local_map_size
        # tem_local_map = crop_img(large_map, pix_pos[0], pix_pos[1], width)
        # img_base64 = cvimg_to_base64(tem_local_map)
        # data = {
        #     'position': pix_pos,
        #     'xywh': None,
        #     'img_base64': img_base64
        # }
        # return MiniMapController.success(data=data)

