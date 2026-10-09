# -*- coding: utf-8 -*-
"""
AI 生成图片水印去除小工具
- 打开图片，鼠标框选水印区域（可多次框选，支持撤销）
- OpenCV inpainting 修复（TELEA / NS 两种算法）
- 单张另存，或对整个文件夹批量应用同一框选位置
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

MASK_DILATE_PX = 3          # 选区外扩像素，盖住水印边缘
MAX_DISPLAY = 1000          # 画布最长边限制
VALID_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")


class App:
    def __init__(self, root):
        self.root = root
        root.title("AI 图片去水印工具")
        root.geometry("1080x760")

        self.src_path = None
        self.cv_img = None          # BGR 原图
        self.mask = None            # 与原图同尺寸
        self.tk_img = None
        self.scale = 1.0
        self.disp_w = self.disp_h = 0
        self.start = None
        self.rect_id = None
        self.history = []           # 已确认选区 (x0,y0,x1,y1) 原图坐标

        # 顶部工具栏
        bar = ttk.Frame(root, padding=6)
        bar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(bar, text="打开图片", command=self.open_image).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="撤销选区", command=self.undo_rect).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="清空选区", command=self.clear_rects).pack(side=tk.LEFT, padx=3)

        ttk.Label(bar, text="算法:").pack(side=tk.LEFT, padx=(12, 2))
        self.algo = tk.StringVar(value="TELEA")
        ttk.Combobox(bar, textvariable=self.algo, values=["TELEA", "NS"],
                     width=6, state="readonly").pack(side=tk.LEFT)

        ttk.Label(bar, text="修复半径:").pack(side=tk.LEFT, padx=(12, 2))
        self.radius = tk.IntVar(value=5)
        ttk.Spinbox(bar, from_=1, to=30, width=4, textvariable=self.radius).pack(side=tk.LEFT)

        ttk.Button(bar, text="预览修复", command=self.preview).pack(side=tk.LEFT, padx=12)
        ttk.Button(bar, text="另存为...", command=self.save_as).pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="批量处理文件夹(同位置)", command=self.batch).pack(side=tk.RIGHT, padx=3)

        # 画布
        self.canvas = tk.Canvas(root, bg="#2b2b2b", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # 状态栏
        self.status = tk.StringVar(value="请先打开图片：鼠标拖拽框选水印区域，可框多处")
        ttk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W,
                  padding=4).pack(side=tk.BOTTOM, fill=tk.X)

    # ---------- 坐标换算 ----------
    def to_orig(self, x, y):
        return int(x / self.scale), int(y / self.scale)

    # ---------- 文件 ----------
    def open_image(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("所有文件", "*.*")])
        if not path:
            return
        # imdecode 支持中文路径
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            messagebox.showerror("错误", "无法读取该图片")
            return
        self.src_path = path
        self.cv_img = img
        self.mask = np.zeros(img.shape[:2], np.uint8)
        self.history.clear()
        self.render(img)
        self.status.set(f"{os.path.basename(path)}  尺寸 {img.shape[1]}x{img.shape[0]} —— 拖拽框选水印")

    def render(self, img_bgr):
        h, w = img_bgr.shape[:2]
        self.scale = min(MAX_DISPLAY / w, MAX_DISPLAY / h, 1.0)
        self.disp_w, self.disp_h = int(w * self.scale), int(h * self.scale)
        disp = cv2.resize(img_bgr, (self.disp_w, self.disp_h), interpolation=cv2.INTER_AREA)
        self.tk_img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)))
        self.canvas.config(width=self.disp_w, height=self.disp_h)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        self.draw_history()

    def draw_history(self):
        for i, (x0, y0, x1, y1) in enumerate(self.history):
            self.canvas.create_rectangle(x0 * self.scale, y0 * self.scale,
                                         x1 * self.scale, y1 * self.scale,
                                         outline="#ffdd33", width=2)

    # ---------- 框选 ----------
    def on_press(self, e):
        if self.cv_img is None:
            return
        self.start = (e.x, e.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#33ddff", width=2)

    def on_drag(self, e):
        if self.start and self.rect_id:
            self.canvas.coords(self.rect_id, self.start[0], self.start[1], e.x, e.y)

    def on_release(self, e):
        if not self.start or self.cv_img is None:
            return
        x0, y0 = self.to_orig(*self.start)
        x1, y1 = self.to_orig(e.x, e.y)
        self.start = None
        self.rect_id = None
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        h, w = self.mask.shape
        x0, x1 = max(0, x0), min(w, x1)
        y0, y1 = max(0, y0), min(h, y1)
        if x1 - x0 < 3 or y1 - y0 < 3:
            return
        self.history.append((x0, y0, x1, y1))
        cv2.rectangle(self.mask, (x0, y0), (x1, y1), 255, -1)
        self.status.set(f"已选 {len(self.history)} 处区域 —— 继续框选，或点「预览修复」")

    def undo_rect(self):
        if not self.history:
            return
        self.history.pop()
        self.mask[:] = 0
        for x0, y0, x1, y1 in self.history:
            cv2.rectangle(self.mask, (x0, y0), (x1, y1), 255, -1)
        self.render(self.cv_img)

    def clear_rects(self):
        self.history.clear()
        if self.mask is not None:
            self.mask[:] = 0
        if self.cv_img is not None:
            self.render(self.cv_img)

    # ---------- 修复 ----------
    def inpaint(self, img, mask):
        if mask is None or mask.sum() == 0:
            return None
        kernel = np.ones((MASK_DILATE_PX * 2 + 1,) * 2, np.uint8)
        m = cv2.dilate(mask, kernel, iterations=1)
        flag = cv2.INPAINT_TELEA if self.algo.get() == "TELEA" else cv2.INPAINT_NS
        return cv2.inpaint(img, m, self.radius.get(), flag)

    def preview(self):
        if self.cv_img is None:
            return
        out = self.inpaint(self.cv_img, self.mask)
        if out is None:
            messagebox.showinfo("提示", "请先框选水印区域")
            return
        self._preview_img = out
        self.render(out)
        self.status.set("预览结果（仍可撤销/重选后再次预览）—— 满意后点「另存为」")

    def save_as(self):
        out = getattr(self, "_preview_img", None)
        if out is None:
            out = self.inpaint(self.cv_img, self.mask) if self.cv_img is not None else None
        if out is None:
            messagebox.showinfo("提示", "请先打开图片并框选水印区域")
            return
        base, ext = os.path.splitext(self.src_path)
        path = filedialog.asksaveasfilename(
            defaultextension=ext or ".png",
            initialfile=os.path.basename(base) + "_nowm" + (ext or ".png"),
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp"), ("所有文件", "*.*")])
        if not path:
            return
        ok, buf = cv2.imencode(os.path.splitext(path)[1] or ".png", out)
        if ok:
            buf.tofile(path)  # 中文路径安全
            self.status.set(f"已保存: {path}")
        else:
            messagebox.showerror("错误", "保存失败")

    # ---------- 批量 ----------
    def batch(self):
        if self.cv_img is None or not self.history:
            messagebox.showinfo("提示", "请先打开一张样例图并框好水印位置")
            return
        folder = filedialog.askdirectory(title="选择要批量处理的图片文件夹")
        if not folder:
            return
        files = [f for f in os.listdir(folder) if f.lower().endswith(VALID_EXT)]
        if not files:
            messagebox.showinfo("提示", "文件夹里没有支持的图片")
            return
        if not messagebox.askyesno("确认", f"将对 {len(files)} 张图片按当前框选位置去水印，输出到子文件夹 nowm_output，继续？"):
            return
        out_dir = os.path.join(folder, "nowm_output")
        os.makedirs(out_dir, exist_ok=True)
        ok_n = fail_n = 0
        h0, w0 = self.mask.shape
        for name in files:
            fp = os.path.join(folder, name)
            try:
                data = np.fromfile(fp, dtype=np.uint8)
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("decode fail")
                # 按尺寸比例换算 mask（同尺寸直接复用）
                h, w = img.shape[:2]
                if (h, w) == (h0, w0):
                    m = self.mask
                else:
                    m = np.zeros((h, w), np.uint8)
                    sx, sy = w / w0, h / h0
                    for x0, y0, x1, y1 in self.history:
                        cv2.rectangle(m, (int(x0 * sx), int(y0 * sy)),
                                      (int(x1 * sx), int(y1 * sy)), 255, -1)
                out = self.inpaint(img, m)
                ext = os.path.splitext(name)[1]
                okb, buf = cv2.imencode(ext, out)
                buf.tofile(os.path.join(out_dir, name))
                ok_n += 1
            except Exception:
                fail_n += 1
        self.status.set(f"批量完成：成功 {ok_n}，失败 {fail_n}，输出目录 {out_dir}")
        messagebox.showinfo("完成", f"成功 {ok_n} 张，失败 {fail_n} 张\n输出：{out_dir}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
