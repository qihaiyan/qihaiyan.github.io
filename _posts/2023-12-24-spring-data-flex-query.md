---
layout: post
title:  "Spring Data 灵活查询的三种方式"
date:   2023-12-27 16:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/data-flex-query.jpg
---

在页面中展示列表数据时，通常需要根据用户输入的不同的查询条件返回不同的查询结果，传统的方式往往采用手动编写原始sql拼接where条件的方式，这种方式并不安全，容易存在sql注入漏洞。

本文介绍用SpringDataJpa实现灵活查询的方式，具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-data-flex-query](https://github.com/qihaiyan/springcamp/tree/main/spring-data-flex-query)

## 一、概述

SpringDataJpa提供了三种灵活查询的方式，分别是：1、通过@Query注解编写查询语句；2、Example查询；3、Specification查询。下面分别介绍这三种方式的使用方法。

## 二、通过@Query注解编写查询语句

这种方式使用比较简单，在 Repository 方法中编写查询语句。

``` groovy
public interface MyDataRepository extends JpaRepository<MyData, Long>, JpaSpecificationExecutor<MyData> {
    @Query("select U from MyData U where (?1 is null or U.id=?1) and (?2 is null or U.name=?2)")
    List<MyData> findByQuery(Long id, String name);
}
```

为了能够按照不同的查询条件进行查询，需要在查询语句中对查询参数进行判空，将所有的查询参数组合成and查询条件。当某个查询参数为空时，查询路径会被is null覆盖，该查询参数不会对数据进行过滤。

## 三、Example查询

Example查询是通过一个数据对象按照约定的规则进行查询，只有对象中的非空字段或加入过滤条件，为空的字段不会进行过滤。

``` java
public interface MyService {
    MyData example = new MyData();
        example.setName("two");
        log.info("find by example: {}", myDataRepository.findAll(Example.of(example)));
}
```

在上述代码中，由于我们只对example对象的name字段赋值，因此只会按照name条件进行过滤。

更加详细的使用方式，可以参照[官方文档(https://docs.spring.io/spring-data/jpa/reference/repositories/query-by-example.html)]

## 四、Specification查询

相比于前两种方式，Specification查询要灵活的多，可以任意组合查询条件，实现我们想要的查询结果。

首先 Repository 要扩展 JpaSpecificationExecutor ：

```java
public interface MyDataRepository extends JpaRepository<MyData, Long>, JpaSpecificationExecutor<MyData> {
}
```

用Specification编写一个查询方法：

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

在查询方法中，我们分别通过 builder.equal、builder.like、 root.get("id").in 实现了 `=` `like` `in` 三个sql子句，除此之外，还有 `greaterThan` `lessThan` 等其它很多方法可以使用。

最后一个参数还可以指定分页和排序条件。

使用查询方法进行灵活查询：

```java
log.info("find by spec with id: {}", findBySpec(1L, null, null));
log.info("find by spec with name: {}", findBySpec(null, "%wo%", null));
log.info("find by spec with id list: {}", findBySpec(null, null, List.of(1L, 2L)));
```

执行程序后，我们可以在日志中看到，不同的查询条件返回了不同的查询结果。

完整的实例代码：

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
