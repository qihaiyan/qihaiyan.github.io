---
layout: post
title:  "Spring Dynamic Datasource: Add a New Datasource by Configuration Only"
date:   2020-9-16 15:30:00 +0800
lang: en
slug_zh: spring-dynamic-datasource
tags: [spring,java]
categories: [spring boot]
image: assets/images/dynamic-datasource.png
description: "How to implement dynamic datasources in Spring Boot: add a new datasource just by editing the configuration file, with no code changes. Full example included."
---

In real-world business scenarios, we often run into situations where datasources need to be configured dynamically: adding a new datasource should only require a configuration change, without modifying the program code. The dynamic datasource technique makes this possible.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-datasource](https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-datasource).

## 1. Overview

When developing database applications with Spring Boot, we usually configure the datasource in the configuration file and then use that datasource in the code to perform database operations. Whenever a new datasource is needed, the program has to be modified. With the dynamic datasource technique, a new datasource can be plugged in by only changing the configuration, with no code changes. This greatly improves development efficiency and system flexibility.

<!-- more -->

## 2. Configuration File

The yml configuration format supports list structures. We can put the datasources we need to access into a list, where each datasource specifies its own url, username, password, and query:

``` yml
spring:
  application:
    name: dynamicDatasource
dynamic-data:
  schemas:
    -
      code: dbsource1
      datasource:
        url: jdbc:h2:mem:db1;MODE=MySQL;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
        username: sa
        password:
      query: |
        select 'datasource1 data'
    -
      code: dbsource2
      datasource:
        url: jdbc:h2:mem:db2;MODE=MySQL;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
        username: sa
        password:
      query: |
        select 'datasource2 data'

```

## 3. Reading the Datasource Configuration

We define a configuration class ```DatabaseConfig``` to read the datasource configuration:

```java
@Slf4j
@Data
@Component
@ConfigurationProperties(prefix = "dynamic-data")
public class DatabaseConfig {
    private List<DbSchema> schemas = new ArrayList<>();

    @PostConstruct
    public void init() {
        for (DbSchema current : this.getShemas()) {
            HikariConfig jdbcConfig = new HikariConfig();
            jdbcConfig.setJdbcUrl(current.getDatasource().getUrl());
            jdbcConfig.setUsername(current.getDatasource().getUsername());
            String password = current.getDatasource().getPassword();
            jdbcConfig.setPassword(password);
            try {
                HikariDataSource hikariDataSource = new HikariDataSource(jdbcConfig);
                current.setJdbcTemplate(new JdbcTemplate(hikariDataSource));
            } catch (Exception e) {
                log.error("connect to " + current.getDatasource().getUrl() + "  failed.");
                throw e;
            }
        }
    }

    @Data
    @NoArgsConstructor
    public static class DbSchema {
        private String code;
        private DataSourceProperties datasource;
        private String query;
        private JdbcTemplate jdbcTemplate;
    }
}
```

The ```DbSchema``` class corresponds to the individual configuration items of a datasource, including url, username, password, and query. It also defines a ```JdbcTemplate```: we can use each datasource's own JdbcTemplate to access the data of that datasource.

The ```JdbcTemplate``` is initialized in the ```init``` method. The database connection pool is HikariCP, which is also the default connection pool used by Spring Boot. Every database connection configuration in the configuration file produces a corresponding ```DbSchema``` object, which is placed in the schemas list of the configuration class.

This approach also allows us to encrypt the database passwords in the configuration file. The password stored in the configuration file is the encrypted one, and in the init method we can decrypt ```current.getDatasource().getPassword()```. This improves system security and prevents database passwords from leaking through the configuration file.

## 4. Reading Data from Each Datasource

Once the connection pools are initialized, reading data becomes simple: we only need to iterate over the schemas member of the configuration class and use each schema's ```JdbcTemplate```.

```java
@SpringBootApplication
public class DemoApplication implements CommandLineRunner {

    @Autowired
    private DatabaseConfig databaseConfig;

    @Override
    public void run(String... args) {
        databaseConfig.getSchemas().stream().filter(r -> !r.getQuery().isEmpty()).forEach(current -> {
            String result = current.getJdbcTemplate().queryForObject(
                    current.getQuery(), String.class);
            System.out.println(current.getCode() + " content: " + result);
        });
    }

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
```

Later on, to add a new datasource, we only need to add a new datasource definition under schemas in the configuration file.
