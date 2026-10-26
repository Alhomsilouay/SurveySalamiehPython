[app]
title = Salamieh Survey
package.name = salamiehsurvey
package.domain = org.salamieh

source.dir = .
source.include_exts = py,ttf,json

version = 1.0

requirements = python3,kivy,plyer,arabic-reshaper,python-bidi

# Fonts / assets bundled into the APK - keep your Arabic .ttf next to main.py
# and it will be picked up automatically (see main.py FONT_CANDIDATES).

orientation = portrait
fullscreen = 0

android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 34
android.minapi = 23
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
