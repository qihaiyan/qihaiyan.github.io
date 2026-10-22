---
layout: post
title:  "Spring Boot Log Handling with Docker and EFK"
date:   2017-06-02 22:28:00 +0800
lang: en
slug_zh: spring-boot-efk-log
tags: [spring]
categories: [spring boot]
description: "Centralize Spring Boot logs with an EFK stack (Elasticsearch 8.x, Fluentd, Kibana): a self-contained Docker Compose v2 deployment plus logback (fluency) configuration, with the Docker fluentd logging driver as a zero-intrusion alternative."
---

1. Overview

In a distributed cluster environment, the logs of a single node are usually stored on that node itself, and this independent, scattered way of storing logs causes many problems. We need a unified log processing center to collect and centrally store logs, and to view and analyze them. [The Twelve-Factor App](https://12factor.net/zh_cn/logs) contains recommendations on log handling.

The corresponding technologies are mature now; the usual choice is the Elastic Search + Logstash + Kibana stack (ELK). In this article we adopt an approach that is easier to deploy: the Elastic Search + Fluentd + Kibana stack (EFK), deployed with docker.

This article has been updated: the example repository [fluentd-boot](https://github.com/qihaiyan/fluentd-boot) referenced by the original post has been deleted by its author, and the original content was stuck in the Elasticsearch 2.x era. The article has been rewritten for the current versions (Docker Compose v2, Elasticsearch 8.x, Fluentd 1.19) and made self-contained, so the whole demo can be completed without cloning an example repository.

<!-- more -->

2. Install docker

2.1. Install Docker Engine

Docker provides an official one-click installation script that supports mainstream distributions such as Ubuntu, Debian and CentOS, and automatically installs Docker Engine and the Docker Compose plugin:

    curl -fsSL https://get.docker.com | sudo sh

You can also install from the official distribution repositories; for Ubuntu, for example:

    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

After installation, start the docker service and enable it at boot:

    sudo systemctl enable --now docker

2.2. Test the docker service

Run the command:

    sudo docker run hello-world

If the screen shows the `Hello from Docker!` message, docker is installed correctly.

2.3. Verify docker compose

Docker Compose v2 ships as a plugin installed together with Docker; there is no longer any need to download the docker-compose binary separately as with old versions. Confirm the version with the following command:

    docker compose version

3. Start the containers

Instead of depending on an example project, create a local efk directory with the following structure:

    efk/
    ├── docker-compose.yml
    ├── fluentd/
    │   ├── Dockerfile
    │   └── fluent.conf
    └── es/                 # elasticsearch data directory, create it empty first

Create a docker-compose.yml in the efk directory with the following content:

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

The configuration starts three services: elasticsearch, kibana, and fluentd. Several points that differ from the old-style configuration:

1. Docker Compose v2 syntax is used; the services talk to each other over the custom network `efk` by **service name** (e.g. `http://es:9200`), so the deprecated `links:` configuration is no longer needed;
2. The images come from the official `docker.elastic.co` repository, and elasticsearch and kibana keep matching versions (8.19.24);
3. Security is disabled for the demo environment (`xpack.security.enabled=false`). Production environments must enable security, including user authentication and TLS encrypted transport;
4. Only port 9200 is exposed; the old transport port 9300 no longer needs to be published.

Note

    - ./es:/usr/share/elasticsearch/data

this line persists the elasticsearch data in the es directory where docker-compose.yml is located. You can change ./es to any other path, but the corresponding directory must have read/write permissions. The elasticsearch process inside the official image runs as uid 1000, so the host directory must be prepared first:

    mkdir -p es
    sudo chown -R 1000:0 es

The build file for the fluentd container is the Dockerfile in the fluentd directory, with the following content:

    FROM fluent/fluentd:v1.19-debian-1

    USER root
    RUN fluent-gem install fluent-plugin-elasticsearch -v 5.4.4

    USER fluent

As the configuration shows, our self-built fluentd container is based on the official image, with one main change: installing the fluent-plugin-elasticsearch plugin with the plugin version pinned. The 5.4.x series targets Elasticsearch 8.x; if you use Elasticsearch 9.x, upgrade the plugin to 6.x (compatible with ES 9 since 6.0.0). This step allows fluentd to send log content to elasticsearch.

The fluentd configuration file fluent.conf also lives in the fluentd directory, with the following content:

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

The configuration contains two parts:

1. A `forward` source listening on port 24224, receiving logs pushed by applications over the fluent forward protocol;
2. An `elasticsearch` match that writes the logs into elasticsearch. `logstash_format true` generates a daily index named like `springboot-2026.10.22`, which is convenient for time-based viewing in kibana.

Once the files are ready, run the following command in the efk directory to start the docker containers:

    docker compose up -d

4. Configure the Spring Boot application to send logs to fluentd

The project's build.gradle file contains the following lines:

    implementation 'com.sndyuk:logback-more-appenders:1.8.9'
    implementation 'org.komamitsu:fluency-core:2.7.4'
    implementation 'org.komamitsu:fluency-fluentd:2.7.4'

logback-more-appenders provides a fluentd appender for logback. Here we use its `FluencyLogbackAppender`, which is built on fluency, a high-performance fluentd client (the older `DataFluentAppender` is based on fluent-logger and is still maintained, but updated less frequently).

The logback configuration file is logback.xml:

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

The configuration uses the FLUENTD_HOST and FLUENTD_PORT environment variables to specify the address and port of fluentd. If these two entries are not set in the environment variables, logs are sent to the local machine by default. Fields such as level, logger and thread are sent as independent fields, so once written into elasticsearch they can be used directly as dimensions for search and aggregation.

Besides configuring an appender inside the application, there is a simpler alternative: use the Docker fluentd logging driver to forward a container's stdout logs straight to fluentd:

    app:
      image: your-spring-boot-app:latest
      logging:
        driver: fluentd
        options:
          fluentd-address: localhost:24224
          tag: springboot.app

The trade-offs between the two approaches:

1. The appender approach requires adding a dependency and logback configuration to the application, but the log fields are structured (level, logger, traceId, etc. as separate fields), and on send failure the application side can buffer and retry — it is the preferred option for Java applications;
2. The fluentd logging driver requires zero intrusion into the application and can collect the stdout logs of any container, but what it receives is plain text, so multi-line logs such as stack traces must be parsed again on the fluentd side — it suits uniformly onboarding existing containers.

5. Run the program and check the results

Any Spring Boot application, once it includes the dependencies above and the logback.xml configuration, can send its logs to fluentd. Start the application from your IDE, or run `./gradlew bootRun`.

This step starts the Spring Boot application; when the application prints logs they are sent to fluentd, and fluentd writes them into Elastic Search. You can watch the containers with the following commands:

    docker compose ps
    docker compose logs -f fluentd
    curl http://localhost:9200/_cat/indices?v

If you see an index starting with `springboot-`, the logs have been written successfully.

Open `http://localhost:5601` in a browser to see the Kibana page. On first use you need to create a Data View (index pattern) under Stack Management, enter `springboot-*` and pick @timestamp as the time field; after that you can see the collected logs in Discover.

By configuring FLUENTD_HOST and FLUENTD_PORT in the environment variables, you can specify the address and port of the docker container. If they are not specified, logs are sent to localhost by default; in that case, the Spring Boot application and the docker container should be running on the same machine.

6. Summary

Modern system architectures increasingly emphasize cloud computing, microservices, and cluster deployment, and centralized log processing is a key aspect to consider. For ease of demonstration, only a single node was deployed; cluster deployment can be achieved with Kubernetes. One more reminder: security was disabled in elasticsearch for the convenience of the demo; production environments need to enable user authentication and configure TLS.
