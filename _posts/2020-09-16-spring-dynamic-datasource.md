---
layout: post
title:  "spring动态数据源"
date:   2020-9-16 15:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/dynamic-datasource.png
---

在实际的业务场景中，我们经常会遇到需要动态配置数据源的情况，只需要修改配置，就能增加新的数据源的接入，而不需要修改程序代码，通过动态数据源技术可以实现这个目标。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-dynamic-datasource](https://github.com/qihaiyan/springcamp/tree/master/spring-dynamic-datasource)

## 一、概述

通常在用springboot开发数据库应用时，我们会在配置文件中配置好数据源，程序中指定数据源进行数据库操作。当需要新增数据源时，就需要修改程序。通过动态数据源技术，我们可以做到只修改配置就能实现新数据源的接入，无需修改代码。这样可以很大的提升开发效率，提升系统的灵活性。

<!-- more -->

## 二、配置文件

yml格式的配置文件支持list结构，我们可以把需要访问的数据源配置到list结构中，每个数据源指定各自的url、用户名、密码、查询语句：

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

## 三、读取数据源配置

我们定义一个配置类```DatabaseConfig``` 用于读取数据源的配置：

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

其中的```DbSchema```类对应了数据源的各项配置，包括url、用户名、密码、查询语句，另外还定义了一个```JdbcTemplate```，我们可以用每个数据源自己的JdbcTemplate去访问本数据源的数据。

在```init```方法中初始化```JdbcTemplate```。数据库连接池采用HikariCP，这也是springboot默认使用的数据库连接池。配置文件中所有的数据库连接配置都生成一个对应的```DbSchema```对象，放到配置类的schemas这个list中。

通过这种方式，我们还可以实现配置文件中数据库密码的加密。配置文件中的数据库密码是加密后的密码，可以在init方法中，对```current.getDatasource().getPassword()```解密。这样能够提升系统的安全性，防止数据库密码通过配置文件泄漏。

## 四、读取各数据源的数据

当数据库连接池完成初始化后，读取数据就变的很简单，我们只需要遍历配置类中的schemas成员，针对每个schema操作```JdbcTemplate```就可以。

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

后续如果要新增数据源，只需要在配置文件中的schemas下面新增数据源定义即可。
