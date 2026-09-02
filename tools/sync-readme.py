#!/usr/bin/env python3
"""同步 springcamp 仓库的 README 到 _includes/remote/,供 About 页嵌入渲染。

springcamp 的 README 更新后手动运行一次再提交:
    python3 tools/sync-readme.py
"""
import os
import re
import urllib.request

SRC = "https://raw.githubusercontent.com/qihaiyan/springcamp/main/README.md"
REPO_TREE = "https://github.com/qihaiyan/springcamp/tree/main/"
OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "_includes", "remote", "springcamp-readme.md",
)


def fix_relative_link(m):
    url = m.group(1)
    if url.startswith(("http://", "https://", "#", "mailto:", "/")):
        return m.group(0)
    return "](" + REPO_TREE + url + ")"


def main():
    md = urllib.request.urlopen(SRC, timeout=30).read().decode("utf-8")
    # 仓库内相对链接(如模块目录)改写为GitHub绝对路径,避免在博客上404
    md = re.sub(r"\]\(([^)\s]+)\)", fix_relative_link, md)
    # 博客页不展示贡献统计图和 Supported by 段
    md = "\n".join(l for l in md.splitlines() if "repobeats.axiom.co" not in l)
    idx = md.find("### Supported by")
    if idx != -1:
        md = md[:idx]
    # 用 raw 包裹,防止 README 里将来出现 {{ }} 或 {% %} 被Liquid误解析
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("{% raw %}\n" + md.rstrip() + "\n{% endraw %}\n")
    print(f"已同步 {len(md)} 字符 -> {OUT}")


if __name__ == "__main__":
    main()
