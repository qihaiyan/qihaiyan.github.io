---
title: "关于海思博客与 SpringCamp 开源示例项目"
layout: page
permalink: "/about.html"
comments: true
description: "关于海思技术博客：本站与 GitHub 开源项目 SpringCamp 配套，提供 30+ 个可独立运行的 Spring Boot 实战示例，覆盖 Spring AI、Security、OAuth2、Cloud、消息、缓存、并发等方向，代码与原理文章一一对应。"
---
{% capture readme %}{% include remote/springcamp-readme.md %}{% endcapture %}{{ readme | strip | markdownify }}
