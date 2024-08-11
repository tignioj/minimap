import cv2
import numpy as np
from scipy import signal
from scipy.signal import find_peaks
from cached_property import cached_property

from capture.capture_factory import capture

def rgb2luma(image):
    """
    Convert RGB to the Y channel (Luminance) in YUV color space.

    Args:
        image (np.ndarray): Shape (height, width, channel)

    Returns:
        np.ndarray: Shape (height, width)
    """
    image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
    luma, _, _ = cv2.split(image)
    return luma


def peak_confidence(arr, **kwargs):
    """
    Evaluate the prominence of the highest peak

    Args:
        arr (np.ndarray): Shape (N,)
        **kwargs: Additional kwargs for signal.find_peaks

    Returns:
        float: 0-1
    """
    para = {
        'height': 0,
        'prominence': 10,
    }
    para.update(kwargs)
    length = len(arr)
    peaks, properties = signal.find_peaks(np.concatenate((arr, arr, arr)), **para)
    peaks = [h for p, h in zip(peaks, properties['peak_heights']) if length <= p < length * 2]
    peaks = sorted(peaks, reverse=True)

    count = len(peaks)
    if count > 1:
        highest, second = peaks[0], peaks[1]
    elif count == 1:
        highest, second = 1, 0
    else:
        highest, second = 1, 0
    confidence = (highest - second) / highest
    return confidence


def convolve(arr, kernel=3):
    """
    Args:
        arr (np.ndarray): Shape (N,)
        kernel (int):

    Returns:
        np.ndarray:
    """
    return sum(np.roll(arr, i) * (kernel - abs(i)) // kernel for i in range(-kernel + 1, kernel))

class RotationGIA:
    def __init__(self, debug_enable=False):
        self.debug_enable = debug_enable
        self.gc = capture
        # self.MINIMAP_RADIUS = GenShinCapture.mini_map_width //2

    #     self.degree = 0
    #     self.rotation = 0
    #     self.rotation_confidence = 0
    def cv_show(self, name, img):
        pass
        if self.debug_enable:
            cv2.imshow(name, img)

    def get_minimap_subtract(self, minimap, matched_map=None, update_position=True):
        minimap = rgb2luma(minimap)
        # current - background
        image = cv2.cvtColor(matched_map, cv2.COLOR_BGR2GRAY)
        minimap = minimap.astype(float)
        image = image.astype(float)
        image = (255 - image) / (255 - minimap + 0.1) * 128
        image = cv2.min(cv2.max(image, 0), 255)
        image = image.astype(np.uint8)
        # cv2.imshow('image after substract', image)
        return image

    def update(self, width, height):
        print(f"Observer notified with width: {width}, height: {height}")
        # 删除缓存，使其在下次访问时重新计算
        if 'RotationRemapData' in self.__dict__:
            del self.__dict__['RotationRemapData']
    @cached_property
    def RotationRemapData(self):
        d = self.gc.mini_map_width
        mx = np.zeros((d, d), dtype=np.float32)
        my = np.zeros((d, d), dtype=np.float32)
        for i in range(d):
            for j in range(d):
                mx[i, j] = d / 2 + i / 2 * np.cos(2 * np.pi * j / d)
                my[i, j] = d / 2 + i / 2 * np.sin(2 * np.pi * j / d)
        return mx, my

    def predict_rotation(self, image):
        # image = get_diff(image, matched_image)
        # image = self.get_minimap_subtract(image, matched_map)
        d = self.gc.mini_map_width
        # Upscale image and apply Gaussian filter for smoother results
        scale = 2
        image = cv2.GaussianBlur(image, (3, 3), 0)
        cv2.imshow('image', image)
        # Expand circle into rectangle
        remap = cv2.remap(image, *self.RotationRemapData, cv2.INTER_LINEAR)[d * 1 // 10:d * 5 // 10].astype(
            np.float32)
        remap = cv2.resize(remap, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        # cv2.imshow('remap', remap)
        # Find derivative
        gradx = cv2.Scharr(remap, cv2.CV_32F, 1, 0)
        self.cv_show('gradx', gradx)

        # Magic parameters for scipy.find_peaks
        para = {'height': 50, 'wlen': d * scale}
        # `l` for the left of sight area, derivative is positive
        # `r` for the right of sight area, derivative is negative
        l = np.bincount(find_peaks(gradx.ravel(), **para)[0] % (d * scale), minlength=d * scale)
        r = np.bincount(find_peaks(-gradx.ravel(), **para)[0] % (d * scale), minlength=d * scale)
        l, r = np.maximum(l - r, 0), np.maximum(r - l, 0)

        conv0 = []
        kernel = 2 * scale
        for offset in range(-kernel + 1, kernel):
            result = l * convolve(np.roll(r, -d * scale // 4 + offset), kernel=3 * scale)
            minus = l * convolve(np.roll(r, offset), kernel=10 * scale) // 5
            result -= minus
            result = convolve(result, kernel=3 * scale)
            conv0.append(result)

        conv0 = np.array(conv0)
        conv0[conv0 < 1] = 1
        maximum = np.max(conv0, axis=0)
        if peak_confidence(maximum) > 0.3:
            result = maximum
        else:
            average = np.mean(conv0, axis=0)
            minimum = np.min(conv0, axis=0)
            result = convolve(maximum * average * minimum, 2 * scale)

        # Convert match point to degree
        self.degree = np.argmax(result) / (d * scale) * 2 * np.pi + np.pi / 4
        degree = np.argmax(result) / (d * scale) * 360 + 135
        degree = int(degree % 360)
        self.rotation = degree

        # Calculate confidence
        self.rotation_confidence = round(peak_confidence(result), 3)

        # Convert
        if degree > 180:
            degree = 360 - degree
        else:
            degree = -degree
        self.rotation = degree

        # Calculate confidence
        self.rotation_confidence = round(peak_confidence(result), 3)
        return degree


if __name__ == '__main__':
    yc = RotationGIA(debug_enable=True)
    from capture.capture_factory import capture
    gc = capture
    gc.add_observer(yc)

    while True:
        key = cv2.waitKey(20)
        if key & 0xFF == ord('q'):
            break
        query_image = gc.get_mini_map(use_alpha=True)
        # 根据alpha获取实际的角度
        deg3_gray = yc.predict_rotation(cv2.cvtColor(query_image, cv2.COLOR_BGR2GRAY))
        print(deg3_gray)
