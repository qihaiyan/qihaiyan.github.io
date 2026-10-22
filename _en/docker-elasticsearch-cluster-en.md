---
layout: post
title:  "Building an Elasticsearch Cluster with Docker"
date:   2017-09-08 21:00:00 +0800
lang: en
slug_zh: docker-elasticsearch-cluster
tags: [docker,elasticsearch]
categories: [docker]
image: assets/images/elasticsearch.png
description: "Deploying an Elasticsearch 9.x cluster (1 master + 2 data nodes) with Docker Compose v2: discovery.seed_hosts, cluster.initial_master_nodes, node.roles and the vm.max_map_count prerequisite, all self-contained."
---
## Overview

Deploying Elasticsearch with Docker is very simple, but implementing a cluster configuration requires some special handling. This article explains how to build an Elasticsearch cluster with Docker.

This article has been updated: the example repository fluentd-boot referenced by the original post has been deleted by its author, and the configuration was stuck in the Elasticsearch 2.x era (discovery.zen.* was removed after 7.x). The article has been rewritten for the current versions (Elasticsearch 9.x, Docker Compose v2) and made self-contained — the complete configuration is given inline, so there is no example repository to clone.

## Master Node Configuration

### The docker-compose.yml File

This article uses a single docker-compose.yml to start 1 master node and 2 data nodes at once. Create an es-cluster directory with the following structure:

    es-cluster/
    ├── docker-compose.yml
    ├── es-node-1/
    │   └── elasticsearch.yml
    ├── es-node-2/
    │   └── elasticsearch.yml
    └── es-node-3/
        └── elasticsearch.yml

The docker-compose.yml looks like this:

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

Three key points:

1. The images all come from the official `docker.elastic.co` repository, version 9.5.6; the old Docker Hub images are no longer used;
2. The nodes discover each other over the custom network `es-cluster` by **service name**; the deprecated `links:` are gone, and the transport port 9300 no longer needs to be published;
3. The data directories use named volumes, which automatically inherit the ownership of the directory inside the image, avoiding host directory permission problems; each node's data is independent and persisted in its own volume.

Data persistence can also be changed to a host directory mount (like the original ```./es:/usr/share/elasticsearch/data```), but the directory must have read/write permissions — the elasticsearch process inside the official image runs as uid 1000, so you must first run ```sudo chown -R 1000:0 <directory>```.

### The elasticsearch.yml File

es-node-1/elasticsearch.yml (the master node):

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

Corresponding to the old ```discovery.zen.ping.unicast.hosts```, discovery is now composed of two settings:

- ```discovery.seed_hosts```: the list of seed nodes used for discovery after the cluster is up; here the compose service names are used directly;
- ```cluster.initial_master_nodes```: the list of master-eligible nodes that take part in the master election only when the cluster is formed **for the first time**; it only needs to appear in the master node's configuration. Once the cluster has been initialized, this setting no longer has any effect on restart.

```node.roles: [ master, data ]``` replaces the old ```node.master: true``` plus ```node.data: true```, meaning the node is both a master node and a data node.

Security is disabled for the demo environment (```xpack.security.enabled: false```). Production environments must enable security, configure TLS for the transport and HTTP layers and turn on user authentication; otherwise anyone can read the cluster's data directly.

### Starting the Service

First check whether ```vm.max_map_count``` in the ```/etc/sysctl.conf``` configuration file is greater than 262144 (the official minimum required by Elasticsearch; the value 655360 used in the original post also satisfies the requirement). If it is not, or if the file does not contain this setting, use the root user to change it to ```vm.max_map_count=262144``` and run the command ```sysctl -p```; otherwise Elasticsearch will report an error at startup.

Run ```docker compose up -d``` and the service will start normally.

## Data Node Configuration

### The docker-compose.yml File

It lives in the same docker-compose.yml as the master node — the es-node-2 and es-node-3 services configured above.

### The elasticsearch.yml File

es-node-2/elasticsearch.yml:

``` yml
cluster.name: es-cluster
node.name: es-node-2
node.roles: [ data ]
http.port: 9200
network.host: 0.0.0.0
discovery.seed_hosts: ["es-node-1", "es-node-2", "es-node-3"]
xpack.security.enabled: false
```

The differences from the master node configuration are the following:

```
node.name: es-node-2
node.roles: [ data ]
```

```node.name``` is the name of the data node; ```node.roles``` keeps only the ```data``` role, corresponding to the old ```node.master: false``` plus ```node.data: true```; and data nodes do not need ```cluster.initial_master_nodes```. The es-node-3 configuration is the same as es-node-2, with only ```node.name``` changed to ```es-node-3```.

If you want to deploy the nodes on separate machines as in the original post, each node's ```discovery.seed_hosts``` must contain the master node's real IP (e.g. ```["10.0.0.1:9300"]```), the master and data nodes must each set ```network.publish_host``` to their own machine IP, and the transport port 9300 must be reachable between the nodes (each container needs to publish 9300 in a multi-machine deployment); the rest of the configuration stays the same.

### Starting the Service

The startup steps are the same as for the master node.

Once the master node and the data nodes are all up, run the command `curl http://localhost:9200/_cat/nodes?v` on the master node server (replacing localhost with the master node's IP in a multi-machine deployment) to see the status of the nodes in the cluster:

    ip         heap.percent ram.percent cpu load_1m load_5m load_15m node.role master name
    172.18.0.2           40          78   2    0.08    0.12     0.09       dim *      es-node-1
    172.18.0.3           35          80   1    0.05    0.10     0.08       d   -      es-node-2
    172.18.0.4           38          79   1    0.06    0.11     0.08       d   -      es-node-3

All three nodes have joined the cluster: in the ```node.role``` column, ```dim``` marks the master node (master + data) and ```d``` marks the pure data nodes; finally confirm the cluster status is ```green``` with ```curl http://localhost:9200/_cluster/health?pretty```.
