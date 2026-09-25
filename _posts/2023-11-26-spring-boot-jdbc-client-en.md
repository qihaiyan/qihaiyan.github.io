---
layout: post
title:  "Spring Boot 3.2 New Feature: JdbcClient"
date:   2023-11-26 16:20:00 +0800
lang: en
slug_zh: spring-boot-jdbc-client
tags: [spring,java]
categories: [spring boot]
image: assets/images/jdbc-client.jpg
description: "JdbcClient in Spring Boot 3.2 wraps JdbcTemplate with a fluent, chainable API for running SQL, covering queries, named params, RowMapper, inserts, and updates."
---

Spring Boot 3.2 introduces the new JdbcClient for database operations. JdbcClient wraps JdbcTemplate and adopts a fluent API style that supports chained calls.

With this, the database access options built into Spring now number four: JdbcTemplate, JdbcClient, SpringDataJdbc, and SpringDataJpa.

For scenarios where a heavyweight ORM framework is a poor fit, or where complex SQL needs to be written, you can use JdbcClient and write your own SQL to operate on the database. However, JdbcClient does not support batch operations or stored procedure calls; for those you need to use JdbcTemplate.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-data-jdbc-client](https://github.com/qihaiyan/springcamp/tree/main/spring-data-jdbc-client).

## 1. Overview

JdbcClient is a lightweight data access framework with a fluent API style — simple, flexible, easy to read and maintain, and it supports writing complex SQL.

## 2. Adding JdbcClient

First add the spring-data-jdbc dependency.

Add one line to build.gradle:

``` groovy
implementation 'org.springframework.boot:spring-boot-starter-data-jdbc'
```

Then simply inject JdbcClient into your service:

``` java
@Component
public class DbService {
    @Autowired
    private JdbcClient jdbcClient;
}
```

## 3. Query Operations

With JdbcClient you can look up data by primary key, or query it with custom conditions.

Looking up data by primary key:

``` java
public MyData findDataById(Long id) {
        return jdbcClient.sql("select * from my_data where id = ?")
                .params(id)
                .query(MyData.class)
                .single();
    }
```

Querying with custom conditions:

``` java
public List<MyData> findDataByName(String name) {
        return jdbcClient.sql("select * from my_data where name = ?")
                .params(name)
                .query(MyData.class)
                .list();
    }
```

In both queries above the variables in the conditions use placeholders. JdbcClient also supports querying with named parameters:

``` java
public Integer insertDataWithNamedParam(MyData myData) {
        Integer rowsAffected = jdbcClient.sql("insert into my_data values(:id,:name) ")
                .param("id", myData.id())
                .param("name", myData.name())
                .update();
        return rowsAffected;
    }
```

When there are many parameters, you can put them into a Map and query with the Map:

``` java
public List<MyData> findDataByParamMap(Map<String, ?> paramMap) {
        return jdbcClient.sql("select * from my_data where name = :name")
                .params(paramMap)
                .query(MyData.class)
                .list();
    }
```

When the query results cannot be mapped simply onto a class, you can write a RowMapper, which suits scenarios with more complex SQL statements:

``` java
public List<MyData> findDataWithRowMapper() {
        return jdbcClient.sql("select * from my_data")
                .query((rs, rowNum) -> new MyData(rs.getLong("id"), rs.getString("name")))
                .list();
    }
```

Counting records is also supported:

``` java
public Integer countByName(String name) {
        return jdbcClient.sql("select count(*) from my_data where name = ?")
                .params(name)
                .query(Integer.class)
                .single();
    }
```

## 4. Inserting Data

The update method of JdbcClient can be used to insert and update data.

Inserting data with placeholder parameters:

```java
public Integer insertDataWithParam(MyData myData) {
        Integer rowsAffected = jdbcClient.sql("insert into my_data values(?,?) ")
                .param(myData.id())
                .param(myData.name())
                .update();
        return rowsAffected;
    }
```

Inserting data with named parameters:

```java
public Integer insertDataWithNamedParam(MyData myData) {
        Integer rowsAffected = jdbcClient.sql("insert into my_data values(:id,:name) ")
                .param("id", myData.id())
                .param("name", myData.name())
                .update();
        return rowsAffected;
    }
```

Inserting an entire object directly:

```java
public Integer insertDataWithObject(MyData myData) {
        Integer rowsAffected = jdbcClient.sql("insert into my_data values(:id,:name) ")
                .paramSource(myData)
                .update();
        return rowsAffected;
    }
```

## 5. Summary

As the examples above show, all the basic database operations can be done with JdbcClient, avoiding a heavyweight ORM framework, and the operations are much simpler and more flexible than an ORM. The fluent API style is also easier to write and read.

A demonstration of calls to the full set of database operations:

```java
@Slf4j
@SpringBootApplication
public class Application implements CommandLineRunner {

    @Autowired
    private DbService dbService;

    @Override
    public void run(String... args) {
        MyData myData = new MyData(1L, "test");
        log.info("insert rows: {}", dbService.insertDataWithObject(myData));

        MyData myData2 = new MyData(2L, "test");
        dbService.insertDataWithParam(myData2);

        MyData myData3 = new MyData(3L, "author");
        dbService.insertDataWithNamedParam(myData3);

        log.info("findDataById: {}", dbService.findDataById(1L));
        log.info("findDataByName: {}", dbService.findDataByName("test"));
        log.info("findDataWithRowMapper: {}", dbService.findDataWithRowMapper());
        log.info("findDataByParamMap: {}", dbService.findDataByParamMap(Map.of("name", "author")));
        log.info("countByName: {}", dbService.countByName("test"));
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```
