---
title: "About"
layout: page
permalink: "/about.html"
comments: true
---
{% capture readme %}{% include remote/springcamp-readme.md %}{% endcapture %}{{ readme | strip | markdownify }}
