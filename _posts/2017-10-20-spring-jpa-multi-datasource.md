---
layout: post
title:  "SpringBoot项目中的多数据源支持"
description: "介绍在 Spring Boot 4.x 项目中利用 Spring Data JPA 支持多数据源的方法，通过分包配置各自的 EntityManagerFactory 与事务管理器，实现多个数据库的访问与查询，附示例项目。"
date:   2017-10-20 10:00:00 +0800
tags: [spring]
categories: [spring boot]
image: assets/images/datasource.jpg
---
## 1.概述

项目中经常会遇到一个应用需要访问多个数据源的情况，本文介绍在SpringBoot项目中利用SpringDataJpa技术如何支持多个数据库的数据源。

本文已更新：示例代码已适配 Spring Boot 4.x（示例项目基于 Spring Boot 4.1.1 和 Java 17+）。相比旧版写法，主要变化有三处：实体注解的包名由 javax.persistence 迁移到了 jakarta.persistence；DataSourceBuilder 及配套的 DataSourceProperties、JpaProperties、EntityManagerFactoryBuilder 都换到了新的包名；Hibernate 6 移除了 naming-strategy 和 dialect 配置体系，相关配置项可以直接删除。

具体的代码参照该 [示例项目](https://github.com/qihaiyan/springcamp/tree/main/spring-data-jpa-multisource)

本文示例使用的 Gradle 依赖如下：

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-jpa'
    implementation 'com.mysql:mysql-connector-j'
    implementation 'com.h2database:h2'
}
```

## 2.建立实体类（Entity）

首先，我们创建两个简单的实体类，分别属于两个不同的数据源，用于演示多数据源数据的保存和查询。

PrimaryTable实体类（属于主数据源）：

```java
package cn.springcamp.springdatajpa.multisource.primary.data;

import jakarta.persistence.*;

@Entity
@Table(name = "demo")
public class PrimaryTable {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    public PrimaryTable() {

    }

    public Long getId() {
        return this.id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
```

Other实体类：

```java
package cn.springcamp.springdatajpa.multisource.other.data;

import jakarta.persistence.*;

@Entity
@Table(name = "other")
public class Other {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    public Other() {

    }

    public Long getId() {
        return this.id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
```

需要注意的是，这两个实体类分属于不同的package，这一点极为重要，spring会根据实体类所属的package来决定用那一个数据源进行操作。

<!-- more -->

## 3.建立Repository

分别建立两个实体类对应的Repository，用于进行数据操作。

PrimaryTableRepository:

```java
package cn.springcamp.springdatajpa.multisource.primary.data;

import org.springframework.data.jpa.repository.JpaRepository;

public interface PrimaryTableRepository extends JpaRepository<PrimaryTable, Long> {
}
```

OtherRepository:

```java
package cn.springcamp.springdatajpa.multisource.other.data;

import org.springframework.data.jpa.repository.JpaRepository;

public interface OtherRepository extends JpaRepository<Other, Long> {
}
```

得益于spring-data-jpa优秀的封装，我们只需创建一个接口，就拥有了对实体类的操作能力。

## 4.对多数据源进行配置

分别对PrimaryTable和Other两个实体类配置对应的数据源。配置的内容主要包含三个要素：

1. dataSource，数据源的连接信息
2. entityManagerFactory，数据处理
3. transactionManager，事务管理

主数据源的配置 PrimaryDataConfig：

```java
package cn.springcamp.springdatajpa.multisource.config;

import com.zaxxer.hikari.HikariDataSource;
import jakarta.persistence.EntityManagerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.autoconfigure.DataSourceProperties;
import org.springframework.boot.jpa.EntityManagerFactoryBuilder;
import org.springframework.boot.jpa.autoconfigure.JpaProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
        entityManagerFactoryRef = "primaryEntityManagerFactory",
        transactionManagerRef = "primaryTransactionManager",
        basePackages = {"cn.springcamp.springdatajpa.multisource.primary.data"}
)
public class PrimaryDataConfig {

    @Autowired
    private JpaProperties jpaProperties;

    @Bean
    @Primary
    @ConfigurationProperties(prefix = "spring.datasource")
    public DataSourceProperties primaryDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Primary
    @Bean(name = "primaryDataSource")
    @ConfigurationProperties(prefix = "spring.datasource.hikari")
    public HikariDataSource primaryDataSource() {
        return primaryDataSourceProperties().initializeDataSourceBuilder().type(HikariDataSource.class).build();
    }

    @Primary
    @Bean(name = "primaryEntityManagerFactory")
    public LocalContainerEntityManagerFactoryBean primaryEntityManagerFactory(
            EntityManagerFactoryBuilder builder) {
        return builder
                .dataSource(primaryDataSource())
                .packages("cn.springcamp.springdatajpa.multisource.primary.data")
                .properties(jpaProperties.getProperties())
                .persistenceUnit("primary")
                .build();
    }

    @Primary
    @Bean(name = "primaryTransactionManager")
    public PlatformTransactionManager primaryTransactionManager(
            @Qualifier("primaryEntityManagerFactory") EntityManagerFactory primaryEntityManagerFactory) {
        return new JpaTransactionManager(primaryEntityManagerFactory);
    }

}
```

代码中的Primary注解表示这是默认数据源。主数据源的连接信息由 primaryDataSourceProperties 绑定 spring.datasource 配置项，并通过 initializeDataSourceBuilder 构建出 HikariDataSource，连接池参数则绑定 spring.datasource.hikari 配置项。注意在 Spring Boot 4 中，DataSourceProperties 位于 org.springframework.boot.jdbc.autoconfigure 包，JpaProperties 位于 org.springframework.boot.jpa.autoconfigure 包，EntityManagerFactoryBuilder 位于 org.springframework.boot.jpa 包。

Other实体类的数据源配置 OtherDataConfig：

```java
package cn.springcamp.springdatajpa.multisource.config;

import com.zaxxer.hikari.HikariDataSource;
import jakarta.persistence.EntityManagerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.autoconfigure.DataSourceProperties;
import org.springframework.boot.jpa.EntityManagerFactoryBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
        entityManagerFactoryRef = "otherEntityManagerFactory",
        transactionManagerRef = "otherTransactionManager",
        basePackages = {"cn.springcamp.springdatajpa.multisource.other.data"}
)
public class OtherDataConfig {

    @Autowired
    private OtherJpaProperties jpaProperties;

    @Bean
    @ConfigurationProperties(prefix = "other.datasource")
    public DataSourceProperties otherDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean(name = "otherDataSource")
    @ConfigurationProperties(prefix = "other.datasource.hikari")
    public HikariDataSource otherDataSource() {
        return otherDataSourceProperties().initializeDataSourceBuilder().type(HikariDataSource.class).build();
    }

    @Bean(name = "otherEntityManagerFactory")
    public LocalContainerEntityManagerFactoryBean otherEntityManagerFactory(
            EntityManagerFactoryBuilder builder) {
        return builder
                .dataSource(otherDataSource())
                .packages("cn.springcamp.springdatajpa.multisource.other.data")
                .properties(jpaProperties.getProperties())
                .persistenceUnit("other")
                .build();
    }

    @Bean(name = "otherTransactionManager")
    public PlatformTransactionManager otherTransactionManager(
            @Qualifier("otherEntityManagerFactory") EntityManagerFactory otherEntityManagerFactory) {
        return new JpaTransactionManager(otherEntityManagerFactory);
    }

}
```

第二个数据源不能直接复用 Spring Boot 自动配置的 JpaProperties（它绑定的是 spring.jpa 前缀），这里通过自定义的 OtherJpaProperties 类绑定 other.jpa 前缀，使两个数据源的JPA配置相互独立：

```java
package cn.springcamp.springdatajpa.multisource.config;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.orm.jpa.vendor.Database;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "other.jpa")
public class OtherJpaProperties {

    private Map<String, String> properties = new HashMap<>();

    /**
     * Mapping resources (equivalent to "mapping-file" entries in persistence.xml).
     */
    private final List<String> mappingResources = new ArrayList<>();

    /**
     * Name of the target database to operate on, auto-detected by default. Can be
     * alternatively set using the "Database" enum.
     */
    private String databasePlatform;

    /**
     * Target database to operate on, auto-detected by default. Can be alternatively set
     * using the "databasePlatform" property.
     */
    private Database database;

    /**
     * Whether to initialize the schema on startup.
     */
    private boolean generateDdl = false;

    /**
     * Whether to enable logging of SQL statements.
     */
    private boolean showSql = false;

    public Map<String, String> getProperties() {
        return this.properties;
    }

    public void setProperties(Map<String, String> properties) {
        this.properties = properties;
    }

    public List<String> getMappingResources() {
        return this.mappingResources;
    }

    public String getDatabasePlatform() {
        return this.databasePlatform;
    }

    public void setDatabasePlatform(String databasePlatform) {
        this.databasePlatform = databasePlatform;
    }

    public Database getDatabase() {
        return this.database;
    }

    public void setDatabase(Database database) {
        this.database = database;
    }

    public boolean isGenerateDdl() {
        return this.generateDdl;
    }

    public void setGenerateDdl(boolean generateDdl) {
        this.generateDdl = generateDdl;
    }

    public boolean isShowSql() {
        return this.showSql;
    }

    public void setShowSql(boolean showSql) {
        this.showSql = showSql;
    }

}
```

## 5.数据操作

我们创建一个Service类DbService来分别对两个数据源进行数据的操作。

```java
package cn.springcamp.springdatajpa.multisource.service;

import cn.springcamp.springdatajpa.multisource.other.data.Other;
import cn.springcamp.springdatajpa.multisource.other.data.OtherRepository;
import cn.springcamp.springdatajpa.multisource.primary.data.PrimaryTable;
import cn.springcamp.springdatajpa.multisource.primary.data.PrimaryTableRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class DbService {

    @Autowired
    private PrimaryTableRepository primaryTableRepository;

    @Autowired
    private OtherRepository otherRepository;

    @Value("${name:World}")
    private String name;

    public String getHelloMessage() {
        PrimaryTable primaryTable = new PrimaryTable();
        primaryTable.setName("primary");
        primaryTableRepository.save(primaryTable);

        Other other = new Other();
        other.setName("other");
        otherRepository.save(other);

        primaryTable = primaryTableRepository.findById(1L).orElse(new PrimaryTable());
        other = otherRepository.findById(1L).orElse(new Other());
        return "Hello " + this.name + " : primary's value = " + primaryTable.getName() + " , other's value = " + other.getName();
    }

}
```

对PrimaryTable和Other分别进行数据插入和读取操作，程序运行后会打印出两个数据源各自的数据。主数据源在示例中使用了H2内存数据库（MySQL兼容模式），无需提前准备；第二个数据源采用的是mysql，连接信息在application.yml进行配置。

```yml
spring:
  datasource:
    url: jdbc:h2:mem:test;MODE=MySQL;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
    username: sa
    password:
    driverClassName: org.h2.Driver
    hikari:
      maximum-pool-size: 30
      pool-name: Hikari-primary
  jpa:
    show-sql: true
    open-in-view: false
    # do not use this in production environment
    generate-ddl: true
    properties:
      hibernate:
        id.new_generator_mappings: true
        # do not use this in production environment
        hbm2ddl.auto: create-drop
        physical_naming_strategy: org.springframework.boot.orm.jpa.hibernate.SpringPhysicalNamingStrategy
        implicit_naming_strategy: org.springframework.boot.orm.jpa.hibernate.SpringImplicitNamingStrategy

other:
  datasource:
    url: jdbc:mysql://localhost:3306/demo?characterEncoding=utf-8&useSSL=false
    username: root
    password: root
    driverClassName: com.mysql.cj.jdbc.Driver
    hikari:
      maximum-pool-size: 30
      pool-name: Hikari-other
  jpa:
    show-sql: true
    # do not use this in production environment
    generate-ddl: true
    properties:
      hibernate:
        id.new_generator_mappings: true
        # do not use this in production environment
        hbm2ddl.auto: create-drop
        physical_naming_strategy: org.springframework.boot.orm.jpa.hibernate.SpringPhysicalNamingStrategy
        implicit_naming_strategy: org.springframework.boot.orm.jpa.hibernate.SpringImplicitNamingStrategy
```

PrimaryTable实体对应的是主数据源，读取的是spring.datasource和spring.datasource.hikari配置段，Other实体单独配置数据源连接。具体应该读取哪一段配置内容，是在配置类OtherDataConfig中这行代码指定的。

```java
@ConfigurationProperties(prefix = "other.datasource")
```

第二个数据源使用的MySQL数据库需要预先创建（示例中使用的用户名密码为root/root，请按实际环境修改）：

```shell
create database demo;
```

## 6.总结

spring-data-jpa极大的简化了数据库操作，对于多数据源的支持，也只是需要增加一下配置文件和配置类而已。其中的关键内容有3点：

1. 配置文件中数据源的配置

2. 配置类的编写

3. 实体类所在的package必须与配置类中指定的package一致，如OtherDataConfig中指定的basePackages = {"cn.springcamp.springdatajpa.multisource.other.data"}
