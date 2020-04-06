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

对应的有一个示例项目在github上，地址：[fluentd-boot](https://github.com/qihaiyan/fluentd-boot)。

<!-- more -->

2.安装docker

2.1.设置yum镜像

国外的镜像安装速度很慢，采用清华大学 TUNA 镜像源。

用root用户新建 /etc/yum.repos.d/docker.repo 文件，内容如下：

    [dockerrepo]
    name=Docker Repository
    baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker/yum/repo/centos7
    enabled=1
    gpgcheck=1
    gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker/yum/gpg

2.2.安装

执行命令：

    sudo yum makecache
    sudo yum install docker-engine

2.3.启动docker服务

执行命令：

    systemctl start docker.service

2.4.测试docker服务

执行命令：

    docker run hello-world

屏幕上如果输出以下类似信息，说明docker安装正常。

    Unable to find image 'hello-world:latest' locally
    latest: Pulling from library/hello-world
    c04b14da8d14: Pull complete 
    Digest: sha256:0256e8a36e2070f7bf2d0b0763dbabdd67798512411de4cdcf9431a1feb60fd9
    Status: Downloaded newer image for hello-world:latest
    
    Hello from Docker!
    This message shows that your installation appears to be working correctly.
    
    To generate this message, Docker took the following steps:
     1. The Docker client contacted the Docker daemon.
     2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
     3. The Docker daemon created a new container from that image which runs the
        executable that produces the output you are currently reading.
     4. The Docker daemon streamed that output to the Docker client, which sent it
        to your terminal.
    
    To try something more ambitious, you can run an Ubuntu container with:
     $ docker run -it ubuntu bash
    
    Share images, automate workflows, and more with a free Docker Hub account:
     https://hub.docker.com
    
    For more examples and ideas, visit:
     https://docs.docker.com/engine/userguide/

2.5.安装docker-compose

执行命令：

    sudo curl -L https://github.com/docker/compose/releases/download/1.8.1/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose

    chmod +x /usr/local/bin/docker-compose

3.启动容器

通过以下命令来下载示例项目，并进入项目目录:

    git clone https://github.com/qihaiyan/fluentd-boot.git;
    cd fluentd-boot

在项目目录中执行以下命令来启动docker容器：

    docker-compose up -d

容器的配置是在项目的docker-compose.yml文件中，配置内容非常简单：

    es:
      image: elasticsearch
      volumes:
        - ./es:/usr/share/elasticsearch/data
      ports:
        - 9200:9200
        - 9300:9300
    
    kibana:
      image: kibana
      ports:
        - 5601:5601
      links:
        - es:elasticsearch
    
    fluentd:
      build: fluent-es/
      ports:
        - 24224:24224
      links:
    - es:es

配置文件中启用了3个容器，分别是elasticsearch、kibana、fluentd。其中elasticsearch、kibana直接从仓库中下载，fluentd是自己建立的容器。注意

    - ./es:/usr/share/elasticsearch/data

这一行内容，会将elasticsearch的数据持久化保存在docker-compose.yml所在目录的es目录中。可以将./es修改为其它任何路径，但是对应的目录要有读写权限。

fluentd容器的构建文件是项目的fluent-es目录里的Dockerfile，内容如下：

    FROM fluent/fluentd:latest
    
    WORKDIR /home/fluent
    ENV PATH /home/fluent/.gem/ruby/2.2.0/bin:$PATH
    RUN gem install fluent-plugin-elasticsearch
    
    USER root
    COPY fluent.conf /fluentd/etc
    
    EXPOSE 24284
    
    USER fluent
    VOLUME /fluentd/log
    CMD fluentd -c /fluentd/etc/$FLUENTD_CONF -p /fluentd/plugins $FLUENTD_OPT

从配置内容中可以看出，我们自建的fluentd容器是在官方的镜像基础上建的，主要的改动有2点：

1. 安装fluent-plugin-elasticsearch这个plugin;
2. 将配置文件fluent.conf拷贝到容器中;

这两个步骤的作用是让fluentd能够将日志内容发送到elasticsearch。

4.配置SpringBoot应用，将日志发送到fluentd

在项目的build.gradle文件中包含这2行内容：

    compile 'org.fluentd:fluent-logger:0.3.2'
    compile 'com.sndyuk:logback-more-appenders:1.1.1'

项目会用logback-more-appenders将logback的日志转到fluentd。

logback的配置文件为logback.xml：

    <?xml version="1.0" encoding="UTF-8"?>
    <configuration>
        <include resource="org/springframework/boot/logging/logback/base.xml"/>
        <property name="FLUENTD_HOST" value="${FLUENTD_HOST:-${DOCKER_HOST:-localhost}}"/>
        <property name="FLUENTD_PORT" value="${FLUENTD_PORT:-24224}"/>
        <appender name="FLUENT" class="ch.qos.logback.more.appenders.DataFluentAppender">
            <tag>dab</tag>
            <label>normal</label>
            <remoteHost>${FLUENTD_HOST}</remoteHost>
            <port>${FLUENTD_PORT}</port>
            <maxQueueSize>20</maxQueueSize>
        </appender>
    
        <logger name="fluentd" level="debug" additivity="false">
            <appender-ref ref="CONSOLE" />
            <appender-ref ref="FILE" />
            <appender-ref ref="FLUENT" />
        </logger>
    </configuration>

配置文件中通过FLUENTD_HOST和FLUENTD_PORT两个环境变量来指定fluentd的地址和端口。如果环境变量中没有这两项配置，会默认发送到本机地址。

5.执行程序，查看效果
进入fluent-es目录，执行 ./gradlew bootRun

这步会启动SpringBoot的应用，该应用会随机的产生日志信息，并将日志发送到Elastic Search。
 
在浏览器中打开 `http://localhost:5601`  可以看到Kibana dashboard的页面。

通过在环境变量中配置FLUENTD_HOST 和 FLUENTD_PORT，可以指定docker容器的地址和端口，如果没有指定，日志会默认发送到localhost，在此种情况下，SpringBoot应用和docker容器应该是运行在同一台机器上。

6.总结

在现代化的系统架构中，越来越强调云计算、微服务、集群部署，日志的集中处理是需要重点考虑的环节。为了便于演示，只是部署了单节点，可以通过kubernetes或是docker自带的docker swarm来实现集群部署。
