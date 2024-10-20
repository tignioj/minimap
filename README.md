# minimap
- 纯视觉、基于小地图识别实现的部分原神自动化操作：采集-怪物材料-战斗委托-地脉
- 欢迎加入minimap唯一指定QQ交流群: 132608315, 分享你制作的路线

[![GitHub Star](https://img.shields.io/github/stars/tignioj/minimap?style=flat-square)](https://github.com/tignioj/minimap/stargazers)
[![Release Download](https://img.shields.io/github/downloads/tignioj/minimap/total?style=flat-square)](https://github.com/tignioj/minimap/releases/latest)
[![Release Version](https://img.shields.io/github/v/release/tignioj/minimap?style=flat-square)](https://github.com/tignioj/minimap/releases/latest)
[![Python Version](https://img.shields.io/badge/python-v3.8.0-blue?style=flat-square)](https://www.python.org/downloads/release/python-380/)
[![GitHub Repo Languages](https://img.shields.io/github/languages/top/tignioj/minimap?style=flat-square)](https://github.com/tignioj/minimap/search?l=Python)
![GitHub Repo size](https://img.shields.io/github/repo-size/tignioj/minimap?style=flat-square&color=3cb371)
[![contributors](https://img.shields.io/github/contributors/tignioj/minimap?style=flat-square)](https://github.com/tignioj/minimap/graphs/contributors)


# 关联仓库
- GUI: https://github.com/tignioj/minimap-gui
- 路线: https://github.com/tignioj/minimap-pathlist 
- 地图: https://github.com/tignioj/minimap-map

## 直接运行
- 游戏调整为1920*1080窗口分辨率(如果屏幕大小只有1080p则用1080p**无边框模式**，不要用独占全屏)
- 帧率设置为60帧
- 计算机名称不能是中文否则[报编码错误](https://github.com/tignioj/minimap/issues/4)：设置->系统->系统信息->重命名此电脑：修改为英文
- 不要把游戏窗口移动到屏幕外面, 不要最小化游戏
- 下载[release](https://github.com/tignioj/minimap/releases/latest), 解压后移动到英文路径下，双击start.bat即可(会自动弹窗申请管理员权限以用于操作键盘鼠标)

## 从源码安装
### conda
```shell
conda create -n minimap python==3.8
```

### 安装依赖
```text
pip install -r ./requirements
```

### 拉取资源
```text
git submodule update --init --recursive
```

### 生成特征点
如果你在终端运行，则需要先设置`PYTHONPATH`
```text
$env:PYTHONPATH="项目根目录"
cd myutils
python kp_gen.py
```

### 运行
```shell
cd server
python MinimapServer.py
```

### 子模块更新
一般来说在PyCharm中，直接找到`Update Project`即可(默认快捷键是`Ctrl`+`T`)。

也可以在项目根目录下执行以下命令更新指定模块,例如GUI更新
```shell
git submodule update --remote  server/web 
```

或者进入子模块目录手动拉取更新
```text
cd server/web
git pull
```

# 环境说明
## opencv环境
```
pip install opencv opencv-contrib-python
```

## ocr环境(文字识别)
https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_ch/quickstart.md
### 1. 安装PaddlePaddle
####  CPU版本: 比较占用资源，但是兼容性好一点
需要注意的是如果频繁调用ocr，cpu很容易100%
```
pip install paddlepaddle
```
#### GPU版本: 依赖CUDA平台，并且安装比较麻烦
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

# 免责声明
- 本软件开源、免费，仅供学习交流使用。开发者团队拥有本项目的最终解释权。
- 不得将本软件或其任何部分用于任何形式的商业活动、商业产品或商业服务中。
- 使用本软件产生的所有问题与本项目与开发者团队无关。

# 感谢以下项目(排名不分先后)
- https://github.com/infstellar/genshin_impact_assistant
- https://github.com/Alex-Beng/Yap
- https://github.com/babalae/better-genshin-impact
- https://github.com/GengGode/cvAutoTrack