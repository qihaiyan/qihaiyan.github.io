---
layout: post
title:  "SpringBoot框架中REST接口的异常处理方法"
date:   2017-05-21 18:28:00 +0800
tags: [spring-boot]
categories: [spring-boot]
---
## 概述

用docker进行elasticsearch的部署非常简单，如果要实现集群配置，需要进行一些特殊的处理，本文介绍如何利用docker进行elasticsearch集群的搭建。

具体的配置可以参照该 [示例](https://github.com/qihaiyan/fluentd-boot)

## 主节点配置

### docker-compose.yml配置文件

```yml
es:
  image: elasticsearch
  volumes:
    - ./es:/usr/share/elasticsearch/data
    - ./elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml
  ports:
    - 9200:9200
    - 9300:9300
```
<!-- more -->

其中的```./es:/usr/share/elasticsearch/data```是将elasticsearch的数据文件挂在到本机的一个目录上，这儿指定的本机目录是./es，可以修改为其它有权限的目录。

### elasticsearch.yml配置文件

``` yml
cluster.name: elasticsearch_cluster
node.name: node-master
node.master: true
node.data: true
http.port: 9200
network.host: 0.0.0.0
network.publish_host: master-ip
discovery.zen.ping.unicast.hosts: ["master-ip"]
```

```network.publish_host: master-ip```指定了本机ip，需要将master-ip修改为真实的机器ip。```discovery.zen.ping.unicast.hosts```中的master-ip同样需要修改为真实的机器ip。

### 启动服务

首先确认一下```/etc/sysctl.conf```配置文件中的```vm.max_map_count```是否大于655360，如果不是，或者配置文件中没有该配置，则用root用户将该配置修改为```vm.max_map_count=655360```，并执行命令```sysctl -p```否则启动时elasticsearch会报错。

执行```docker-compose up -d```，就可以正常启动了。

## 数据节点配置

### docker-compose.yml配置文件

与主节点的配置相同。

### elasticsearch.yml配置文件

``` yml
cluster.name: elasticsearch_cluster
node.name: node-data-1
node.master: false
node.data: true
http.port: 9200
network.host: 0.0.0.0
network.publish_host: data-ip
discovery.zen.ping.unicast.hosts: ["master-ip"]
```

与主节点配置的区别在于以下几点：
```
node.name: node-data-1
node.master: false
network.publish_host: data-ip
```

```node.name```是数据节点的名字，```node.master```要设置为false，```network.publish_host```设置为数据节点的机器ip。

### 启动服务

启动步骤同主节点。

主节点和数据节点都启动完成后，在主节点服务器上执行 `curl http://10.164.196.218:9200/_cat/nodes` 命令可以看到集群中节点的状态。