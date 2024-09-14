
## 安装方式
下载release, 解压后双击start.bat即可(需要管理员权限操作键盘鼠标)

## 从源码安装
conda
```shell
conda create -n minimap python==3.8
```

## 安装依赖
```text
pip install -r ./requirements
```

## 准备项目资源
- 把release中的`_internal/resources`复制到项目根目录

## 准备web资源
- 把release中的`_internal/static`和`_internal/templates`复制到项目根目录
- 或者在这里下载 https://github.com/tignioj/minimap-gui

## 运行
```shell
cd server
python MinimapServer.py
```

# 环境说明
# opencv环境
```
pip install opencv opencv-contrib-python
```

## ocr环境(文字识别)
https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_ch/quickstart.md
### 1. 安装PaddlePaddle
####  CPU版本, 卡到爆，cpu随便100%占用
```
pip install paddlepaddle
```
#### GPU版本, 完爆CPU，但是安装可能会遇到很多麻烦
不要用高版本，很多坑。另外，本人尝试通过pip安装的也无效！
```text
conda install paddlepaddle-gpu==2.6.1 cudatoolkit=11.7 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle/ -c conda-forge
```

### 2. 安装PaddleOCR whl包
```
pip install paddleocr
```

## 其他依赖
- flask, requests: http服务
- pywin32: 截图
- paddleocr：图像文本识别
- cached_property:  GIA需要的依赖
- scipy
- numpy

# 问题排查
## ImportError: DLL load failed while importing win32api: 找不到指定的模块。

通常是python3.9引起的问题
### 解决方法1
进入python环境目录，使用管理员权限执行
- https://stackoverflow.com/questions/58612306/how-to-fix-importerror-dll-load-failed-while-importing-win32api
```
python Scripts\pywin32_postinstall.py -install
```
### 解决方法2： 切换python版本为非3.9版本
创建一个新的python环境
```
conda create -n myenv_py310 python==3.10
```

### 解决方法3：切换pywin32版本为301或者306
```text
pip install pywin32==301
```
或者
```text
pip install pywin32==306
```



# 感谢
- https://github.com/infstellar/genshin_impact_assistant: 抄了小地图方向识别
- https://github.com/Alex-Beng/Yap 速度不错的拾取

# 推荐项目
- 更多实用更具 https://github.com/babalae/better-genshin-impact
- 定位 https://github.com/GengGode/cvAutoTrack