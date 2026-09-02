---
title: "About"
layout: page-sidebar
permalink: "/about.html"
comments: true
---
{% capture readme %}{% include remote/springcamp-readme.md %}{% endcapture %}{{ readme | strip | markdownify }}
