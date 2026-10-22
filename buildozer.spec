[app]

# 应用名 / 包名
title = 看见余额
package.name = kanjianyue
package.domain = org.kanjian

# 源码目录：main.py 所在的地方
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,ttc,md
source.include_patterns = app/**/*.py
source.exclude_exts = spec
source.exclude_dirs = .venv,__pycache__,.buildozer,bin,.git,.github,.workbuddy
source.exclude_patterns = _*.py,_*.txt,_*.log,_*.png

# 依赖：实际代码只用到了 Kivy（没有 KivyMD），保持最小
requirements = python3,kivy

# 界面方向
orientation = portrait
fullscreen = 0

# 安卓权限：读图片（选背景图）、写图片（月报保存到相册）
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# 版本
version.regex = __version__ = ['"](.*)['"]
version.filename = %(source.dir)s/main.py
version = 0.1

# 图标 / 启动图（放了同名文件就会自动用上）
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# 只打 arm64：主流安卓机都是 arm64，包体也小一半
android.archs = arm64-v8a
android.api = 34
android.minapi = 23
android.ndk = 25b

# 自动接受 SDK 许可，不然 CI 会卡在交互输入上
android.accept_sdk_license = True

# 不启用 AndroidX 之外的多余服务
android.enable_androidx = True
# 不钉 p4a 分支：让 buildozer 用自己默认匹配的那份 python-for-android。
# 强行拉 master 可能和 buildozer 版本对不上，CI 上表现为莫名其妙的构建失败。

[buildozer]
log_level = 2
warn_on_root = 1
build_dir = ./.buildozer
bin_dir = ./bin

# ---------------------------------------------------------------- 桌面调试
# 本地 Python 预览不需要打包，下面这些只在 buildozer 桌面目标用得到，保持默认即可。
