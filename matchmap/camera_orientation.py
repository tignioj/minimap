#  2024.12.1 来自群友Tim的视角代码
import time
import numpy as np
import cv2
from capture.capture_factory import capture

def apply_mask(img, mask, bkg):
    return (img.astype(np.float32) - bkg) / mask * 255 + bkg

def bgr2h(bgr):
    cmax = np.max(bgr, axis=-1)
    cmin = np.min(bgr, axis=-1)
    mask = cmax > cmin
    hue = np.zeros_like(cmax,dtype=np.float32)
    hue[mask] = ((cmax[mask] - 2 * cmin[mask] - bgr[...,2][mask] + bgr[...,1][mask] + bgr[...,0][mask]) / (cmax[mask] - cmin[mask])) * 60
    hue[~mask] = -1
    hue = np.where(bgr[..., 1] >= bgr[..., 0], hue, 360 - hue)
    return hue

class CameraOrientation:
    def __init__(self, debug_enable=False):
        self.debug_enable = debug_enable
        self.gc = capture
        
        self.tpl_size = 216
        self.tpl_out_rad = 78
        self.tpl_inn_rad = 19
        self.alpha_params_1 = [18.632,20.157,24.093,34.617,38.566,41.94,47.654,51.087,58.561,63.925,67.759,71.77,75.214]
        
        self.r_length = 60
        self.theta_length = 360
        self.peak_width = self.theta_length // 4
        self.rotation_remap_data_x, self.rotation_remap_data_y  = self.generate_points(self.tpl_size/2.0, self.tpl_size/2.0,
                                                                                     self.tpl_inn_rad, self.tpl_out_rad , self.r_length, self.theta_length)
        self.width = self.tpl_size
        self.height = self.tpl_size
        
        self.alpha_mask_1, self.alpha_mask_2 = self.creat_alpha_mask()

    def RotationRemapData(self):
        if (self.width != self.gc.mini_map_width):
            self.rotation_remap_data_x = self.rotation_remap_data_x / self.width * self.gc.mini_map_width
            self.width = self.gc.mini_map_width
        if (self.height != self.gc.mini_map_height):
            self.rotation_remap_data_y = self.rotation_remap_data_y / self.height * self.gc.mini_map_height
            self.height = self.gc.mini_map_height
        return self.rotation_remap_data_x, self.rotation_remap_data_y
    
    def generate_points(self, x, y, d1, d2, n, m):
        r = np.linspace(d1, d2, n)
        theta = np.linspace(0, 360, m, endpoint=False)
        theta_rad = np.radians(theta)
        r_grid, theta_grid = np.meshgrid(r, theta_rad)
        x_cartesian = r_grid * np.cos(theta_grid) + x
        y_cartesian = r_grid * np.sin(theta_grid) + y
        return x_cartesian.astype(np.float32), y_cartesian.astype(np.float32)
    
    def creat_alpha_mask(self):
        values = np.linspace(self.tpl_inn_rad, self.tpl_out_rad, self.r_length)
        alpha_mask_1 = (229 + np.searchsorted(self.alpha_params_1, values)).astype(np.float32)
        alpha_mask_2 = (111.7 + 1.836 * values).astype(np.float32)
        return alpha_mask_1, alpha_mask_2
    
    def predict_rotation(self, image, confidence=0.3):
        remap = cv2.remap(image.astype(np.float32), *self.RotationRemapData(), cv2.INTER_LANCZOS4)
        bgr_img = apply_mask(remap, self.alpha_mask_1[:,np.newaxis], 0)
        h_img = bgr2h(bgr_img)
        fa_img = np.mean(bgr_img,axis = 2)
        fb_img = apply_mask(fa_img, self.alpha_mask_2, 255)

        hist_a = cv2.calcHist([h_img, fa_img], [0, 1], None, [360, 256],[0, 360, 0, 256])
        hist_b = cv2.calcHist([h_img, fb_img], [0, 1], None, [360, 256],[0, 360, 0, 256])

        result = np.zeros((self.theta_length, self.r_length), dtype=np.uint8)
        h = np.floor(h_img).astype(int)
        fa = np.floor(fa_img).astype(int)
        fb = np.floor(fb_img).astype(int)
        flag = (h >= 0) & (h < 360) & (fa >= 0) & (fa < 256) & (fb >= 0) & (fb <256)
        result[flag] = np.select(
            [
                hist_a[h[flag], fa[flag]] > hist_b[h[flag], fb[flag]],
                hist_a[h[flag], fa[flag]] == hist_b[h[flag], fb[flag]],
                hist_a[h[flag], fa[flag]] < hist_b[h[flag], fb[flag]]
            ],
            [
                0,
                128,
                255
            ],
            default=0
        ).astype(np.uint8)
        #plt.imshow(result)
        result_mean = np.mean(result,axis = 1)
        result_conv = np.cumsum(result_mean-np.roll(result_mean,self.peak_width))+ np.sum(result_mean[-self.peak_width:])
        #plt.plot(result_conv)
        max_ind = np.argmax(result_conv)
        degree = (max_ind+0.5) / self.theta_length * 360 + 45
        degree = int(degree % 360)
        if degree > 180: degree = 360 - degree
        else: degree = -degree

        self.rotation_confidence = result_conv[max_ind] / (self.peak_width * 255)
        if self.rotation_confidence < confidence:
            print(f'置信度{self.rotation_confidence}<{confidence}, 不可靠视角', degree)
            return None
        return degree


if __name__ == '__main__':
    rot = CameraOrientation()
    while True:
        img = capture.get_mini_map()
        t = time.time()
        deg = rot.predict_rotation(img)
        print(deg, time.time() - t)
