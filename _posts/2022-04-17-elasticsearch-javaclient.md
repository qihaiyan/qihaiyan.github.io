---
layout: post
title:  "ElasticSearch新版JavaClient使用简介"
description: "介绍 Elasticsearch 7.17 后推荐的新版 Java API Client 的基本用法，包括强类型的同步与异步调用、流式构建请求等特性，并给出与旧版 Java REST Client 迁移对比的示例。"
date:   2022-04-17 17:50:00 +0800
tags: [spring,ElasticSearch]
categories: [spring boot]
image: assets/images/elasticsearch-intro.png
---

ElasticSearch在7.17版本之前使用的java客户端是Java REST Client，但是从7.17版本开始，官方将Java REST Client标记为弃用（deprecated），推荐使用新版Java Client。
本文介绍新版ElasticSearch Java Client的基本用法。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/elasticsearch-javaclient](https://github.com/qihaiyan/springcamp/tree/main/elasticsearch-javaclient)

## 一、概述

Elasticsearch 7.17 版本新增的Java API Client具有以下优点：

1. 强类型
2. 同步和异步调用
3. 流式和函数式调用
4. 与Jackson无缝集成
5. 封装了连接池、重试、json序列化等通用能力

## 二、项目中加入依赖

在项目的gradle或maven中增加依赖关系。

Gradle:

``` gradle
dependencies {
    implementation 'co.elastic.clients:elasticsearch-java:8.19.22'
}
```

Maven:

``` xml
<project>
  <dependencies>

    <dependency>
      <groupId>co.elastic.clients</groupId>
      <artifactId>elasticsearch-java</artifactId>
      <version>8.19.22</version>
    </dependency>

  </dependencies>
</project>
```

上面的依赖中没有手动指定 jackson-databind 的版本号，Jackson 由 Spring Boot 的 BOM 统一管理即可。目前 8.19.x 是 8.x 的维护版本，9.x 也已正式发布（9.x 的 transport 有变化，见下文初始化部分）。

早期的官方文档建议在 Spring Boot 项目中手动引入 jakarta.json 这个包以解决兼容性问题（详见[官方文档](https://www.elastic.co/guide/en/elasticsearch/client/java-api-client/current/installation.html#spring-jakarta-json)）。从 Spring Boot 3.x 开始，Boot 的 BOM 已经管理了 jakarta.json-api，无需再手动引入，只有旧版本的 Boot 项目才需要这样做，示例项目中该依赖已注释掉。

## 三、JavaClient的初始化

Java API Client包含三部分：

1. java客户端对应的类是ElasticsearchClient
2. 一个JSON object mapper用于数据的序列化和反序列化
3. 底层Transport通信

``` java
    RestClient restClient = RestClient.builder(new HttpHost("localhost", 9200)).build();
    ElasticsearchTransport transport = new RestClientTransport(restClient, new JacksonJsonpMapper());
    elasticsearchClient = new ElasticsearchClient(transport);
```

上面是 8.x 的写法，在 8.x 中仍然可用。在 9.x 中，底层 transport 换成了基于 Apache HttpClient 5 的 Rest5Client（对应坐标 co.elastic.clients:elasticsearch-rest5-client），初始化代码相应调整为：

``` java
    Rest5Client rest5Client = Rest5Client.builder(new HttpHost("localhost", 9200)).build();
    ElasticsearchTransport transport = new Rest5ClientTransport(rest5Client, new JacksonJsonpMapper());
    elasticsearchClient = new ElasticsearchClient(transport);
```

## 三、ElasticSearch的基本操作

1.保存数据，通过Java Client的自动序列化能力，我们可以直接把对象传递给Java Client，无需再手动处理ElasticSearch中json数据的序列化。

``` java
    DemoDomain record = new DemoDomain();
    record.setId("1");
    record.setName("test");

    IndexRequest<DemoDomain> indexRequest = IndexRequest.of(b -> b
            .index(MY_INDEX)
            .id(record.getId())
            .document(record)
            .refresh(Refresh.True));  // Make it visible for search

    elasticsearchClient.index(indexRequest);
```

2.查询所有数据，同样json数据的反序列化也有Java Client自动处理，同时函数式编程使得代码很简洁。

``` java
    SearchRequest searchRequest = SearchRequest.of(s -> s
                .index(MY_INDEX)
                .query(q -> q
                        .bool(b -> b
                                .must(m -> m.term(t -> t.field("name").value(FieldValue.of("test"))))
                        )
                ));
    SearchResponse<DemoDomain> search = elasticsearchClient.search(searchRequest, DemoDomain.class);
    return search.hits().hits().stream().map(Hit::source).toList();
```

3.查询单个数据，在查询条件中指定id条件可以精确查询单条记录。

``` java
    SearchRequest searchRequest = SearchRequest.of(s -> s
                .index(MY_INDEX)
                .query(q -> q
                        .bool(b -> b
                                .must(m -> m.term(
                                        t -> t.field("id").value(FieldValue.of("1"))))
                                .must(m -> m.term(
                                        t -> t.field("name").value(FieldValue.of("test"))))
                        )
                ));
    SearchResponse<DemoDomain> search = elasticsearchClient.search(searchRequest, DemoDomain.class);
    return search.hits().hits().get(0).source();
```

4.删除单个数据，通过DeleteRequest可以删除指定的id的记录。

``` java
    DeleteRequest deleteRequest = DeleteRequest.of(s -> s
                .index(MY_INDEX)
                .id(id));
    elasticsearchClient.delete(deleteRequest);
```

5.删除查找到的数据，将查询操作和删除操作合并到一起。

``` java
    SearchRequest searchRequest = SearchRequest.of(s -> s
                .index(MY_INDEX)
                .query(q -> q
                        .bool(b -> b
                                .must(m -> m.term(
                                        t -> t.field("name").value(FieldValue.of("test"))))
                        )
                ));
    SearchResponse<DemoDomain> search = elasticsearchClient.search(searchRequest, DemoDomain.class);
    elasticsearchClient.search(searchRequest, DemoDomain.class).hits().hits().forEach(record -> {
            DeleteRequest deleteRequest = DeleteRequest.of(s -> s
                    .index(MY_INDEX)
                    .id(record.source().getId()));
            try {
                elasticsearchClient.delete(deleteRequest);
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
    });
```
