---
layout: post
title:  "用docker搭建elasticsearch集群"
description: "使用 Docker Compose v2 部署 Elasticsearch 9.x 集群（1 主节点 + 2 数据节点）：discovery.seed_hosts、cluster.initial_master_nodes、node.roles 等现行配置与 vm.max_map_count 注意事项，配置自包含，无需示例仓库。"
date:   2017-09-08 21:00:00 +0800
tags: [docker,elasticsearch]
categories: [docker]
image: assets/images/elasticsearch.png
---
## 概述

用docker进行elasticsearch的部署非常简单，如果要实现集群配置，需要进行一些特殊的处理，本文介绍如何利用docker进行elasticsearch集群的搭建。

本文已更新：原文所附的示例仓库 fluentd-boot 已被作者删除，且配置停留在 Elasticsearch 2.x 时代（discovery.zen.* 已在 7.x 之后被移除）。本文已按当前版本（Elasticsearch 9.x、Docker Compose v2）重写为自包含的形式，全部配置直接在文中给出，无需克隆示例仓库。

## 主节点配置

### docker-compose.yml配置文件

本文使用一份docker-compose.yml同时启动1个主节点和2个数据节点。新建一个es-cluster目录，结构如下：

    es-cluster/
    ├── docker-compose.yml
    ├── es-node-1/
    │   └── elasticsearch.yml
    ├── es-node-2/
    │   └── elasticsearch.yml
    └── es-node-3/
        └── elasticsearch.yml

docker-compose.yml的内容如下：

```yml
services:
  es-node-1:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.5.6
    volumes:
      - ./es-node-1/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml
      - es-data-1:/usr/share/elasticsearch/data
    ports:
      - 9200:9200
    environment:
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    networks:
      - es-cluster

  es-node-2:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.5.6
    volumes:
      - ./es-node-2/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml
      - es-data-2:/usr/share/elasticsearch/data
    environment:
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    networks:
      - es-cluster

  es-node-3:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.5.6
    volumes:
      - ./es-node-3/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml
      - es-data-3:/usr/share/elasticsearch/data
    environment:
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    networks:
      - es-cluster

networks:
  es-cluster:
    driver: bridge

volumes:
  es-data-1:
  es-data-2:
  es-data-3:
```
<!-- more -->

三个要点：

1. 镜像统一使用`docker.elastic.co`官方仓库的9.5.6，不再使用Docker Hub上的旧镜像；
2. 节点之间通过自定义网络`es-cluster`和**服务名**互相发现，不再需要已废弃的`links:`，9300传输端口也不需要对外映射；
3. 数据目录使用named volume，卷会自动继承镜像内目录的属主，避免了宿主机目录的权限问题；每个节点的数据相互独立，持久化保存在各自的卷中。

数据持久化也可以改为挂载宿主机目录（如原文的```./es:/usr/share/elasticsearch/data```），但对应的目录要有读写权限——官方镜像内的elasticsearch进程以uid 1000运行，需要先执行```sudo chown -R 1000:0 <目录>```。

### elasticsearch.yml配置文件

es-node-1/elasticsearch.yml（主节点）：

``` yml
cluster.name: es-cluster
node.name: es-node-1
node.roles: [ master, data ]
http.port: 9200
network.host: 0.0.0.0
discovery.seed_hosts: ["es-node-1", "es-node-2", "es-node-3"]
cluster.initial_master_nodes: ["es-node-1"]
xpack.security.enabled: false
```

与旧版的```discovery.zen.ping.unicast.hosts```对应，现在的发现机制由两项配置组成：

- ```discovery.seed_hosts```：集群启动后用于互相发现种子的节点列表，这里直接写compose的服务名；
- ```cluster.initial_master_nodes```：只在**首次**组建集群时参与master选举的节点列表，仅需出现在主节点的配置中。集群初始化完成后再次重启时，该配置不再起作用。

```node.roles: [ master, data ]```取代了旧版的```node.master: true```加```node.data: true```，表示该节点既是主节点也是数据节点。

演示环境关闭了安全配置（```xpack.security.enabled: false```）。生产环境必须启用安全配置，为传输层和HTTP层配置TLS并开启用户认证，否则任何人都可以直接访问集群数据。

### 启动服务

首先确认一下```/etc/sysctl.conf```配置文件中的```vm.max_map_count```是否大于262144（Elasticsearch官方要求的最低值，原文中设置的655360同样满足要求），如果不是，或者配置文件中没有该配置，则用root用户将该配置修改为```vm.max_map_count=262144```，并执行命令```sysctl -p```否则启动时elasticsearch会报错。

执行```docker compose up -d```，就可以正常启动了。

## 数据节点配置

### docker-compose.yml配置文件

与主节点在同一份docker-compose.yml中，即上面配置的es-node-2和es-node-3。

### elasticsearch.yml配置文件

es-node-2/elasticsearch.yml：

``` yml
cluster.name: es-cluster
node.name: es-node-2
node.roles: [ data ]
http.port: 9200
network.host: 0.0.0.0
discovery.seed_hosts: ["es-node-1", "es-node-2", "es-node-3"]
xpack.security.enabled: false
```

与主节点配置的区别在于以下几点：

```
node.name: es-node-2
node.roles: [ data ]
```

```node.name```是数据节点的名字；```node.roles```只保留```data```角色，对应旧版的```node.master: false```加```node.data: true```；数据节点不需要配置```cluster.initial_master_nodes```。es-node-3的配置与es-node-2相同，仅```node.name```改为```es-node-3```。

如果要按原文的方式在多台机器上分别部署，每个节点的```discovery.seed_hosts```需要写成主节点的真实IP（如```["10.0.0.1:9300"]```），主节点和数据节点还要分别设置```network.publish_host```为本机IP，并且节点之间的9300传输端口要互相可达（多机部署时每个容器需要映射9300端口），其余配置不变。

### 启动服务

启动步骤同主节点。

主节点和数据节点都启动完成后，在主节点服务器上执行 `curl http://localhost:9200/_cat/nodes?v` 命令（多机部署时将localhost替换为主节点的IP）可以看到集群中节点的状态：

    ip         heap.percent ram.percent cpu load_1m load_5m load_15m node.role master name
    172.18.0.2           40          78   2    0.08    0.12     0.09       dim *      es-node-1
    172.18.0.3           35          80   1    0.05    0.10     0.08       d   -      es-node-2
    172.18.0.4           38          79   1    0.06    0.11     0.08       d   -      es-node-3

三个节点都已加入集群：```node.role```列中的```dim```表示主节点（master + data），```d```表示纯数据节点；再通过```curl http://localhost:9200/_cluster/health?pretty```确认集群状态为```green```即可。
