# -*- coding: utf-8 -*-
"""
无界面自测：生成带水印图 -> inpaint -> 检查输出
运行: python tests/selftest.py
"""
import os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
wm_path = os.path.join(HERE, "test_wm.png")
out_path = os.path.join(HERE, "test_out.png")

# 1) 造一张渐变背景 + 右下角白色水印条
img = np.zeros((400, 600, 3), np.uint8)
for x in range(600):
    img[:, x] = (x % 256, 100, 200 - x % 200)
cv2.rectangle(img, (470, 360), (595, 395), (255, 255, 255), -1)
cv2.putText(img, "AI", (485, 390), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 2)
cv2.imencode(".png", img)[1].tofile(wm_path)

# 2) 框选 + 修复（与 app.py 同逻辑）
mask = np.zeros(img.shape[:2], np.uint8)
cv2.rectangle(mask, (465, 355), (600, 400), 255, -1)
m = cv2.dilate(mask, np.ones((7, 7), np.uint8), 1)
out = cv2.inpaint(img, m, 5, cv2.INPAINT_TELEA)
cv2.imencode(".png", out)[1].tofile(out_path)

# 3) 断言：水印区内不再有纯白像素（被修复成背景色）
roi = out[355:400, 465:600]
white = ((roi > 240).all(axis=2)).sum()
print(f"输入图存在: {os.path.getsize(wm_path)} bytes")
print(f"输出图存在: {os.path.getsize(out_path)} bytes")
print(f"修复后水印区纯白像素数: {white}（应接近 0）")
assert white < 50, "水印未被有效去除"
print("PASS: inpaint 管线工作正常")
