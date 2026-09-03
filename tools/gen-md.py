#!/usr/bin/env python3
"""生成每篇文章的 Markdown 版本,供 AI 代理直接消费。

构建后运行: python3 tools/gen-md.py [输出目录]   (默认 _site,与 jekyll 输出一致)
- 读取 _posts/YYYY-MM-DD-<slug>.md,提取 title/date/tags front matter,
  写出 <输出目录>/<slug>.md:正文即原始 Markdown 源文件,头部补标题和原文链接。
- slug 规则与 permalink /:title/ 一致:文件名去掉日期前缀、保留大小写
  (线上存在 /secure-spring-boot-APIs-with-JWT/ 这类含大写的 URL)。
  Cloudflare Worker 据此把 Accept: text/markdown 的 /<slug>/ 请求
  映射到 /<slug>.md,见 tools/markdown-worker.js 与 .github/workflows/deploy.yml。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "_posts")
SITE_URL = "https://springcamp.cn"


def parse_front_matter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for key in ("title", "date", "tags"):
        km = re.search(r"^%s:\s*(.*?)\s*$" % key, m.group(1), re.M)
        if km:
            fields[key] = km.group(1)
    return fields, m.group(2)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_site")
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for fn in sorted(os.listdir(POSTS)):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS, fn), encoding="utf-8") as f:
            fields, body = parse_front_matter(f.read())
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", fn[:-3])
        title = fields.get("title", slug).strip("\"'")
        date = (fields.get("date") or fn[:10])[:10]
        meta = ["原文: %s/%s/" % (SITE_URL, slug), date]
        tags = fields.get("tags", "").strip("[]")
        if tags:
            meta.append("tags: " + re.sub(r"\s*,\s*", ", ", tags))
        doc = "# %s\n\n> %s\n\n%s" % (title, " · ".join(meta), body.lstrip("\n"))
        with open(os.path.join(out_dir, slug + ".md"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(doc)
        count += 1
    print("生成 %d 篇 markdown -> %s" % (count, out_dir))


if __name__ == "__main__":
    main()
