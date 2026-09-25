---
layout: post
title:  "Spring Boot Log Handling with Docker and EFK"
date:   2017-06-02 22:28:00 +0800
lang: en
slug_zh: spring-boot-efk-log
tags: [spring]
categories: [spring boot]
description: "Centralize Docker logs with an EFK stack (Elasticsearch, Fluentd, Kibana): docker-compose deployment and logback configuration for a Spring Boot application."
---

1. Overview

In a distributed cluster environment, the logs of a single node are usually stored on that node itself, and this independent, scattered way of storing logs causes many problems. We need a unified log processing center to collect and centrally store logs, and to view and analyze them. [The Twelve-Factor App](https://12factor.net/zh_cn/logs) contains recommendations on log handling.

The corresponding technologies are mature now; the usual choice is the Elastic Search + Logstash + Kibana stack (ELK). In this article we adopt an approach that is easier to deploy: the Elastic Search + Fluentd + Kibana stack (EFK), deployed with docker.

There is a corresponding example project on GitHub: [fluentd-boot](https://github.com/qihaiyan/fluentd-boot).

<!-- more -->

2. Install docker

2.1. Configure the yum mirror

Installing from overseas mirrors is very slow, so we use the Tsinghua University TUNA mirror source.

As the root user, create the /etc/yum.repos.d/docker.repo file with the following content:

    [dockerrepo]
    name=Docker Repository
    baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker/yum/repo/centos7
    enabled=1
    gpgcheck=1
    gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker/yum/gpg

2.2. Installation

Run the commands:

    sudo yum makecache
    sudo yum install docker-engine

2.3. Start the docker service

Run the command:

    systemctl start docker.service

2.4. Test the docker service

Run the command:

    docker run hello-world

If the screen shows output similar to the following, docker is installed correctly.

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

2.5. Install docker-compose

Run the commands:

    sudo curl -L https://github.com/docker/compose/releases/download/1.8.1/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose

    chmod +x /usr/local/bin/docker-compose

3. Start the containers

Download the example project and enter the project directory with the following commands:

    git clone https://github.com/qihaiyan/fluentd-boot.git;
    cd fluentd-boot

Run the following command in the project directory to start the docker containers:

    docker-compose up -d

The container configuration is in the project's docker-compose.yml file, and it is very simple:

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

The configuration starts three containers: elasticsearch, kibana, and fluentd. elasticsearch and kibana are downloaded directly from the repository, while fluentd is a container we build ourselves. Note

    - ./es:/usr/share/elasticsearch/data

this line persists the elasticsearch data in the es directory where docker-compose.yml is located. You can change ./es to any other path, but the corresponding directory must have read/write permissions.

The build file for the fluentd container is the Dockerfile in the project's fluent-es directory, with the following content:

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

As the configuration shows, our self-built fluentd container is based on the official image, with two main changes:

1. Install the fluent-plugin-elasticsearch plugin;
2. Copy the fluent.conf configuration file into the container;

These two steps allow fluentd to send log content to elasticsearch.

4. Configure the Spring Boot application to send logs to fluentd

The project's build.gradle file contains these two lines:

    compile 'org.fluentd:fluent-logger:0.3.2'
    compile 'com.sndyuk:logback-more-appenders:1.1.1'

The project uses logback-more-appenders to forward logback logs to fluentd.

The logback configuration file is logback.xml:

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

The configuration uses the FLUENTD_HOST and FLUENTD_PORT environment variables to specify the address and port of fluentd. If these two entries are not set in the environment variables, logs are sent to the local machine by default.

5. Run the program and check the results

Enter the fluent-es directory and run ./gradlew bootRun

This step starts the Spring Boot application, which generates log messages at random and sends them to Elastic Search.
 
Open `http://localhost:5601` in a browser to see the Kibana dashboard page.

By configuring FLUENTD_HOST and FLUENTD_PORT in the environment variables, you can specify the address and port of the docker container. If they are not specified, logs are sent to localhost by default; in that case, the Spring Boot application and the docker container should be running on the same machine.

6. Summary

Modern system architectures increasingly emphasize cloud computing, microservices, and cluster deployment, and centralized log processing is a key aspect to consider. For ease of demonstration, only a single node was deployed; cluster deployment can be achieved with Kubernetes or with docker swarm, which ships with docker.
