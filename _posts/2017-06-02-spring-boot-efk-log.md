---
layout: post
title:  "SpringBoot应用基于docker和EFK的日志处理"
date:   2017-06-02 22:28:00 +0800
tags: [spring]
categories: [spring boot]
---

1.概述
在分布式集群环境下，单个节点的日志内容往往都是存放在自己的节点上，这种独立分散的日志存储方式会有很多问题。我们需要一个统一的日志处理中心，对日志进行收集和集中存储，并进行查看和分析。[The Twelve-Factor App](https://12factor.net/zh_cn/logs)中有关于日志处理的建议。

相应的处理技术现在也很成熟，通常会采用Elastic Search + Logstash + Kibana的技术栈（ELK）。在这篇文章中我们会采用一种更便于部署的方式，采用Elastic Search +Fluentd + Kibana的技术栈（EFK），并且通过docker进行部署。

本文已更新：原文所附的示例仓库 [fluentd-boot](https://github.com/qihaiyan/fluentd-boot) 已被作者删除，且内容停留在 Elasticsearch 2.x 时代。本文已按当前版本（Docker Compose v2、Elasticsearch 8.x、Fluentd 1.19）重写，并改为自包含的形式，无需克隆示例仓库即可完成整个演示。

<!-- more -->

2.安装docker

2.1.安装Docker Engine

Docker官方提供了一键安装脚本，支持Ubuntu、Debian、CentOS等主流发行版，会自动安装Docker Engine和Docker Compose插件：

    curl -fsSL https://get.docker.com | sudo sh

也可以使用发行版官方软件源安装，以Ubuntu为例：

    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

安装完成后启动docker服务，并设置开机自动启动：

    sudo systemctl enable --now docker

2.2.测试docker服务

执行命令：

    sudo docker run hello-world

屏幕上如果输出`Hello from Docker!`的提示信息，说明docker安装正常。

2.3.确认docker compose

Docker Compose v2已经以插件的形式随Docker一起安装，不再需要像旧版本那样单独下载docker-compose二进制文件。执行以下命令确认版本：

    docker compose version

3.启动容器

不再依赖示例项目，我们在本地新建一个efk目录，目录结构如下：

    efk/
    ├── docker-compose.yml
    ├── fluentd/
    │   ├── Dockerfile
    │   └── fluent.conf
    └── es/                 # elasticsearch数据目录，先创建空目录

在efk目录中创建docker-compose.yml，内容如下：

    services:
      es:
        image: docker.elastic.co/elasticsearch/elasticsearch:8.19.24
        environment:
          - discovery.type=single-node
          - xpack.security.enabled=false
          - ES_JAVA_OPTS=-Xms512m -Xmx512m
        volumes:
          - ./es:/usr/share/elasticsearch/data
        ports:
          - "9200:9200"
        networks:
          - efk

      kibana:
        image: docker.elastic.co/kibana/kibana:8.19.24
        environment:
          - ELASTICSEARCH_HOSTS=http://es:9200
        ports:
          - "5601:5601"
        depends_on:
          - es
        networks:
          - efk

      fluentd:
        build: ./fluentd
        volumes:
          - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
        ports:
          - "24224:24224"
        depends_on:
          - es
        networks:
          - efk

    networks:
      efk:
        driver: bridge

配置文件中启用了3个服务，分别是elasticsearch、kibana、fluentd。几个与旧版写法不同的要点：

1. 使用docker compose v2语法，服务之间通过自定义网络`efk`和**服务名**互相访问（如`http://es:9200`），不再需要已废弃的`links:`配置；
2. 镜像来自`docker.elastic.co`官方仓库，elasticsearch和kibana的版本保持一致（8.19.24）；
3. 演示环境关闭了安全配置（`xpack.security.enabled=false`）。生产环境必须启用安全配置，包括用户认证和TLS加密传输；
4. 只暴露了9200端口，旧版需要的9300传输端口不需要再对外映射。

注意

    - ./es:/usr/share/elasticsearch/data

这一行内容，会将elasticsearch的数据持久化保存在docker-compose.yml所在目录的es目录中。可以将./es修改为其它任何路径，但是对应的目录要有读写权限。官方镜像内的elasticsearch进程以uid 1000运行，宿主机目录需要先授权：

    mkdir -p es
    sudo chown -R 1000:0 es

fluentd容器的构建文件是fluentd目录里的Dockerfile，内容如下：

    FROM fluent/fluentd:v1.19-debian-1

    USER root
    RUN fluent-gem install fluent-plugin-elasticsearch -v 5.4.4

    USER fluent

从配置内容中可以看出，我们自建的fluentd容器是在官方的镜像基础上建的，主要的改动是安装fluent-plugin-elasticsearch这个插件，并锁定了插件版本。5.4.x系列适配Elasticsearch 8.x；如果使用Elasticsearch 9.x，需要将插件升级到6.x（6.0.0起适配ES 9）。这一步的作用是让fluentd能够将日志内容发送到elasticsearch。

fluentd的配置文件fluent.conf也在fluentd目录中，内容如下：

    <source>
      @type forward
      port 24224
      bind 0.0.0.0
    </source>

    <match **>
      @type elasticsearch
      host es
      port 9200
      logstash_format true
      logstash_prefix springboot
      flush_interval 5s
      request_timeout 30s

      <buffer>
        flush_thread_count 2
        retry_max_interval 30
      </buffer>
    </match>

配置文件中启用了2部分内容：

1. `forward`类型的source，监听24224端口，接收应用通过fluent forward协议推送过来的日志；
2. `elasticsearch`类型的match，将日志写入elasticsearch。`logstash_format true`会按日期生成形如`springboot-2026.10.22`的索引，便于在kibana中按时间查看。

文件准备好后，在efk目录中执行以下命令来启动docker容器：

    docker compose up -d

4.配置SpringBoot应用，将日志发送到fluentd

在项目的build.gradle文件中包含以下内容：

    implementation 'com.sndyuk:logback-more-appenders:1.8.9'
    implementation 'org.komamitsu:fluency-core:2.7.4'
    implementation 'org.komamitsu:fluency-fluentd:2.7.4'

logback-more-appenders为logback提供了fluentd的appender。这里使用它提供的`FluencyLogbackAppender`，底层基于fluency这个高性能的fluentd客户端（老的`DataFluentAppender`基于fluent-logger，仍在维护但更新较少）。

logback的配置文件为logback.xml：

    <?xml version="1.0" encoding="UTF-8"?>
    <configuration>
        <include resource="org/springframework/boot/logging/logback/base.xml"/>
        <appender name="FLUENT" class="ch.qos.logback.more.appenders.FluencyLogbackAppender">
            <tag>springboot</tag>
            <label>normal</label>
            <remoteHost>${FLUENTD_HOST:-localhost}</remoteHost>
            <port>${FLUENTD_PORT:-24224}</port>
        </appender>

        <root level="INFO">
            <appender-ref ref="CONSOLE" />
            <appender-ref ref="FLUENT" />
        </root>
    </configuration>

配置文件中通过FLUENTD_HOST和FLUENTD_PORT两个环境变量来指定fluentd的地址和端口。如果环境变量中没有这两项配置，会默认发送到本机地址。level、logger、thread等信息会作为独立的字段发送，写入elasticsearch后可以直接作为维度进行检索和聚合。

除了在应用内配置appender，还有一种更简单的替代方案：使用Docker的fluentd日志驱动，将容器的stdout日志直接转发给fluentd：

    app:
      image: your-spring-boot-app:latest
      logging:
        driver: fluentd
        options:
          fluentd-address: localhost:24224
          tag: springboot.app

两种方式的取舍：

1. appender方式需要在应用中加入依赖和logback配置，但日志字段是结构化的（level、logger、traceId等独立字段），并且发送失败时可以在应用侧缓冲重试，适合Java应用作为首选方案；
2. fluentd日志驱动对应用零侵入，任何容器的stdout日志都能收集，但拿到的是文本内容，堆栈等多行日志需要在fluentd侧再次解析，适合作为存量容器统一接入的手段。

5.执行程序，查看效果

任意一个SpringBoot应用，只要加入上面的依赖和logback.xml配置，就可以将日志发送到fluentd。用IDE启动应用，或者执行`./gradlew bootRun`。

这步会启动SpringBoot的应用，应用打印日志时会将日志发送到fluentd，fluentd再将日志写入Elastic Search。可以通过以下命令观察各容器的运行情况：

    docker compose ps
    docker compose logs -f fluentd
    curl http://localhost:9200/_cat/indices?v

如果能看到`springboot-`开头的索引，说明日志已经成功写入。

在浏览器中打开 `http://localhost:5601` 可以看到Kibana页面。首次使用需要在Stack Management中创建Data View（索引模式），填入`springboot-*`并选择@timestamp作为时间字段，之后在Discover中就可以看到收集到的日志了。

通过在环境变量中配置FLUENTD_HOST 和 FLUENTD_PORT，可以指定docker容器的地址和端口，如果没有指定，日志会默认发送到localhost，在此种情况下，SpringBoot应用和docker容器应该是运行在同一台机器上。

6.总结

在现代化的系统架构中，越来越强调云计算、微服务、集群部署，日志的集中处理是需要重点考虑的环节。为了便于演示，只是部署了单节点，可以通过kubernetes来实现集群部署。另外再次提醒，演示环境为了方便关闭了elasticsearch的安全配置，生产环境中需要启用用户认证并配置TLS。
