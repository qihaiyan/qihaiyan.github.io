#!/usr/bin/env python3
"""文章封面图维护脚本:生成卡片缩略图(WebP) + 宽高数据文件。

新增文章后运行一次:  python3 tools/gen-image-meta.py
- 读取 _posts/*.md 的 image: front matter,为每张封面生成 assets/images/thumbs/<名>.webp
  (宽 640px,质量 78;已存在且比原图新的跳过)
- 重写 _data/image_dims.yml: 所有图片的宽高,封面图额外带 t: true 标记
  (模板据 t 决定卡片用缩略图还是原图)
"""
import os
import re
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "_posts")
THUMBS = os.path.join(ROOT, "assets", "images", "thumbs")
DIMS = os.path.join(ROOT, "_data", "image_dims.yml")
THUMB_W = 640
THUMB_Q = 78


def cover_images():
    covers = set()
    for fn in os.listdir(POSTS):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS, fn), encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^image:\s*(\S+)\s*$", line)
                if m and "://" not in m.group(1):
                    covers.add(m.group(1))
    return covers


def main():
    os.makedirs(THUMBS, exist_ok=True)
    covers = cover_images()

    dims = {}
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "_site", ".jekyll-cache", "thumbs")]
        for fn in files:
            if not fn.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            p = os.path.join(root, fn)
            try:
                with Image.open(p) as im:
                    dims[fn] = {"w": im.width, "h": im.height}
            except Exception as e:
                print(f"跳过无法解析的文件: {p} ({e})")

    made = skipped = 0
    for rel in sorted(covers):
        name = rel.split("/")[-1]
        if name not in dims:
            print(f"封面文件不存在: {rel}")
            continue
        src = os.path.join(ROOT, rel.replace("/", os.sep))
        stem = name.rsplit(".", 1)[0]
        dst = os.path.join(THUMBS, stem + ".webp")
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            skipped += 1
            continue
        im = Image.open(src)
        if im.width > THUMB_W:
            im = im.resize((THUMB_W, round(im.height * THUMB_W / im.width)), Image.LANCZOS)
        im.save(dst, format="WEBP", quality=THUMB_Q, method=6)
        made += 1
        print(f"{name}: {os.path.getsize(src)//1024}KB -> {os.path.getsize(dst)//1024}KB")

    lines = ["# 文件名 -> 宽高(t=有卡片缩略图),由 tools/gen-image-meta.py 生成,勿手改"]
    for fn in sorted(dims):
        d = dims[fn]
        t = ", t: true" if (fn in {c.split("/")[-1] for c in covers}) else ""
        lines.append(f"{fn}: {{w: {d['w']}, h: {d['h']}{t}}}")
    with open(DIMS, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\n缩略图: 新生成 {made}, 已存在跳过 {skipped}; 封面 {len(covers)} 张; 尺寸表 {len(dims)} 条")


if __name__ == "__main__":
    sys.exit(main())
