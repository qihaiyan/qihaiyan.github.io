---
layout: post
title:  "Three Ways to Build Flexible Queries with Spring Data"
date:   2023-12-27 16:20:00 +0800
lang: en
slug_zh: spring-data-flex-query
tags: [spring,java]
categories: [spring boot]
image: assets/images/data-flex-query.jpg
description: "Three approaches to flexible queries with Spring Data JPA: the @Query annotation, Example queries, and Specification queries, with a runnable example project."
---

When displaying list data on a page, we usually need to return different query results based on the different conditions the user enters. The traditional approach is to manually write raw SQL and concatenate WHERE conditions, which is unsafe and prone to SQL injection vulnerabilities.

This post introduces how to implement flexible queries with Spring Data JPA. The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-data-flex-query](https://github.com/qihaiyan/springcamp/tree/main/spring-data-flex-query)

## 1. Overview

Spring Data JPA provides three ways to build flexible queries: 1. writing queries with the @Query annotation; 2. Example queries; 3. Specification queries. The following sections explain how to use each of them.

## 2. Writing Queries with the @Query Annotation

This approach is simple to use: write the query in a Repository method.

``` groovy
public interface MyDataRepository extends JpaRepository<MyData, Long>, JpaSpecificationExecutor<MyData> {
    @Query("select U from MyData U where (?1 is null or U.id=?1) and (?2 is null or U.name=?2)")
    List<MyData> findByQuery(Long id, String name);
}
```

To query by different conditions, the query statement needs to null-check each query parameter and combine all of the query parameters into AND conditions. When a query parameter is null, that branch is covered by is null, so that parameter does not filter the data.

## 3. Example Queries

An Example query works from a data object following conventional rules: only the non-null fields of the object are added to the filter conditions, while null fields do not filter anything.

``` java
public interface MyService {
    MyData example = new MyData();
        example.setName("two");
        log.info("find by example: {}", myDataRepository.findAll(Example.of(example)));
}
```

In the code above, since we only set the name field of the example object, the query filters by the name condition only.

For more detailed usage, refer to the [official documentation](https://docs.spring.io/spring-data/jpa/reference/repositories/query-by-example.html).

## 4. Specification Queries

Compared with the previous two approaches, Specification queries are far more flexible: query conditions can be combined arbitrarily to achieve exactly the results we want.

First, the Repository needs to extend JpaSpecificationExecutor:

```java
public interface MyDataRepository extends JpaRepository<MyData, Long>, JpaSpecificationExecutor<MyData> {
}
```

Write a query method with a Specification:

``` java
private List<MyData> findBySpec(Long id, String name, List<Long> ids) {
        return myDataRepository.findAll((root, query, builder) -> {
            List<Predicate> predicates = new ArrayList<>();
            if (id != null) {
                predicates.add(builder.equal(root.get("id"), id));
            }
            if (name != null) {
                predicates.add(builder.like(root.get("name"), name));
            }
            if (ids != null) {
                predicates.add(root.get("id").in(ids));
            }
            return builder.and(predicates.toArray(new Predicate[0]));
        }, Sort.by("id").descending());
    }
```

In the query method, we implement the three SQL clauses `=`, `like`, and `in` with builder.equal, builder.like, and root.get("id").in respectively. Beyond these, many other methods such as `greaterThan` and `lessThan` are available.

The last parameter can also specify paging and sorting conditions.

Using the query method for flexible queries:

```java
log.info("find by spec with id: {}", findBySpec(1L, null, null));
log.info("find by spec with name: {}", findBySpec(null, "%wo%", null));
log.info("find by spec with id list: {}", findBySpec(null, null, List.of(1L, 2L)));
```

After running the program, we can see in the logs that different query conditions return different results.

The complete example code:

```java
@Slf4j
@SpringBootApplication
public class Application implements CommandLineRunner {

    @Autowired
    private MyDataRepository myDataRepository;

    @Override
    public void run(String... args) {
        MyData myData1 = new MyData();
        myData1.setName("one");
        myDataRepository.save(myData1);
        MyData myData2 = new MyData();
        myData2.setName("two");
        myDataRepository.save(myData2);

        log.info("find by id with query: {}", myDataRepository.findByQuery(1L, null));
        log.info("find by id and name with query: {}", myDataRepository.findByQuery(1L, "one"));

        MyData example = new MyData();
        example.setName("two");
        log.info("find by example: {}", myDataRepository.findAll(Example.of(example)));

        log.info("find by spec with id: {}", findBySpec(1L, null, null));
        log.info("find by spec with name: {}", findBySpec(null, "%wo%", null));
        log.info("find by spec with id list: {}", findBySpec(null, null, List.of(1L, 2L)));
    }

    private List<MyData> findBySpec(Long id, String name, List<Long> ids) {
        return myDataRepository.findAll((root, query, builder) -> {
            List<Predicate> predicates = new ArrayList<>();
            if (id != null) {
                predicates.add(builder.equal(root.get("id"), id));
            }
            if (name != null) {
                predicates.add(builder.like(root.get("name"), name));
            }
            if (ids != null) {
                predicates.add(root.get("id").in(ids));
            }
            return builder.and(predicates.toArray(new Predicate[0]));
        }, Sort.by("id").descending());
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```
