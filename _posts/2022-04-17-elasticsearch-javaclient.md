---
layout: post
title:  "ElasticSearch新版JavaClient使用简介"
date:   2022-04-17 17:50:00 +0800
tags: [spring,ElasticSearch]
categories: [spring boot]
image: assets/images/elasticsearch-intro.png
---

ElasticSearch在7.17版本之前使用的java客户端是Java REST Client，但是从7.17版本开始，官方将Java REST Client标记为弃用（deprecated），推荐使用新版Java Client。
本文介绍新版ElasticSearch Java Client的基本用法。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/elasticsearch-javaclient](https://github.com/qihaiyan/springcamp/tree/master/elasticsearch-javaclienth)

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
    implementation 'co.elastic.clients:elasticsearch-java:8.1.2'
    implementation 'com.fasterxml.jackson.core:jackson-databind:2.12.3'

    // Needed only if you use the spring-dependency-management
    // and spring-boot Gradle plugins
    implementation 'jakarta.json:jakarta.json-api:2.0.1' 
}
```

Maven:

``` xml
<project>
  <dependencies>

    <dependency>
      <groupId>co.elastic.clients</groupId>
      <artifactId>elasticsearch-java</artifactId>
      <version>8.1.2</version>
    </dependency>

    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.12.3</version>
    </dependency>

    <!-- Needed only if you use the spring-boot Maven plugin -->
    <dependency> 
      <groupId>jakarta.json</groupId>
      <artifactId>jakarta.json-api</artifactId>
      <version>2.0.1</version>
    </dependency>

  </dependencies>
</project>
```

jakarta.json这个包的引入是为了解决springboot项目的兼容性问题，详见[官方文档](https://www.elastic.co/guide/en/elasticsearch/client/java-api-client/current/installation.html#spring-jakarta-json)

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
