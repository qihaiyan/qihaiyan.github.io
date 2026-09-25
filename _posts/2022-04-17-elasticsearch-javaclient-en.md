---
layout: post
title:  "Introduction to the New ElasticSearch Java Client"
date:   2022-04-17 17:50:00 +0800
lang: en
slug_zh: elasticsearch-javaclient
tags: [spring,ElasticSearch]
categories: [spring boot]
image: assets/images/elasticsearch-intro.png
description: "A quick guide to the new Elasticsearch Java API Client since 7.17, with typed sync/async calls, fluent request building, and notes on the legacy REST Client."
---

Before version 7.17, the Java client for ElasticSearch was the Java REST Client. Starting with version 7.17, the official team marked the Java REST Client as deprecated and recommended the new Java Client.
This article introduces the basic usage of the new ElasticSearch Java Client.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/elasticsearch-javaclient](https://github.com/qihaiyan/springcamp/tree/main/elasticsearch-javaclient).

## 1. Overview

The new Java API Client introduced in Elasticsearch 7.17 has the following advantages:

1. Strong typing
2. Synchronous and asynchronous calls
3. Fluent and functional calls
4. Seamless integration with Jackson
5. Built-in handling of common concerns such as connection pooling, retries, and JSON serialization

## 2. Adding Dependencies to the Project

Add the dependencies to your project's gradle or maven build.

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

The jakarta.json package is included to resolve compatibility issues with Spring Boot projects; for details see the [official documentation](https://www.elastic.co/guide/en/elasticsearch/client/java-api-client/current/installation.html#spring-jakarta-json)

## 3. Initializing the JavaClient

The Java API Client consists of three parts:

1. The client class, ElasticsearchClient
2. A JSON object mapper for serializing and deserializing data
3. The underlying transport

``` java
    RestClient restClient = RestClient.builder(new HttpHost("localhost", 9200)).build();
    ElasticsearchTransport transport = new RestClientTransport(restClient, new JacksonJsonpMapper());
    elasticsearchClient = new ElasticsearchClient(transport);
```

## 3. Basic Operations of ElasticSearch

1. Saving data: thanks to the Java Client's automatic serialization, we can pass objects directly to the Java Client without manually handling JSON serialization for ElasticSearch.

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

2. Querying all data: JSON deserialization is also handled automatically by the Java Client, and functional programming keeps the code concise.

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

3. Querying a single record: specifying the id in the query conditions retrieves exactly one record.

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

4. Deleting a single record: a DeleteRequest deletes the record with the specified id.

``` java
    DeleteRequest deleteRequest = DeleteRequest.of(s -> s
                .index(MY_INDEX)
                .id(id));
    elasticsearchClient.delete(deleteRequest);
```

5. Deleting the records found by a query: the query and delete operations are combined into one.

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
