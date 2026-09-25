---
layout: post
title:  "Building an Elasticsearch Cluster with Docker"
date:   2017-09-08 21:00:00 +0800
lang: en
slug_zh: docker-elasticsearch-cluster
tags: [docker,elasticsearch]
categories: [docker]
image: assets/images/elasticsearch.png
description: "Deploying an Elasticsearch cluster with Docker and docker-compose: elasticsearch.yml settings for master and data nodes and unicast discovery."
---
## Overview

Deploying Elasticsearch with Docker is very simple, but implementing a cluster configuration requires some special handling. This article explains how to build an Elasticsearch cluster with Docker.

The complete code is available in the example project [https://github.com/qihaiyan/fluentd-boot](https://github.com/qihaiyan/fluentd-boot)

## Master Node Configuration

### The docker-compose.yml File

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

The ```./es:/usr/share/elasticsearch/data``` entry mounts the Elasticsearch data files to a directory on the local machine; here the local directory is ./es, which you can change to any other directory you have permission to write to.

### The elasticsearch.yml File

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

```network.publish_host: master-ip``` specifies the local machine's IP; replace master-ip with the real machine IP. The master-ip in ```discovery.zen.ping.unicast.hosts``` must likewise be replaced with the real machine IP.

### Starting the Service

First check whether ```vm.max_map_count``` in the ```/etc/sysctl.conf``` configuration file is greater than 655360. If it is not, or if the file does not contain this setting, use the root user to change it to ```vm.max_map_count=655360``` and run the command ```sysctl -p```; otherwise Elasticsearch will report an error at startup.

Run ```docker-compose up -d``` and the service will start normally.

## Data Node Configuration

### The docker-compose.yml File

The same as the master node.

### The elasticsearch.yml File

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

The differences from the master node configuration are the following:
```
node.name: node-data-1
node.master: false
network.publish_host: data-ip
```

```node.name``` is the name of the data node, ```node.master``` must be set to false, and ```network.publish_host``` is set to the data node's machine IP.

### Starting the Service

The startup steps are the same as for the master node.

Once the master node and the data nodes are all up, run the command `curl http://master-ip:9200/_cat/nodes` on the master node server (replacing master-ip in the command with the master node's machine IP) to see the status of the nodes in the cluster.
