---
layout: post
title:  "Multiple Data Sources in a Spring Boot Project"
date:   2017-10-20 10:00:00 +0800
lang: en
slug_zh: spring-jpa-multi-datasource
tags: [spring]
categories: [spring boot]
image: assets/images/datasource.jpg
description: "How to support multiple data sources in a Spring Boot 4.x project with Spring Data JPA, configuring an EntityManagerFactory and transaction manager per package."
---
## 1. Overview

It is quite common for an application to need to access multiple data sources. This post describes how to support multiple database data sources in a Spring Boot project using Spring Data JPA.

This post has been updated: the example code now targets Spring Boot 4.x (the example project is based on Spring Boot 4.1.1 and Java 17+). Compared with the old style, there are three main changes: entity annotation imports moved from javax.persistence to jakarta.persistence; DataSourceBuilder and its companions DataSourceProperties, JpaProperties and EntityManagerFactoryBuilder moved to new packages; and Hibernate 6 removed the naming-strategy and dialect configuration system, so those settings can simply be deleted.

The complete code is available in the example project [spring-data-jpa-multisource](https://github.com/qihaiyan/springcamp/tree/main/spring-data-jpa-multisource).

The Gradle dependencies used in this example:

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-jpa'
    implementation 'com.mysql:mysql-connector-j'
    implementation 'com.h2database:h2'
}
```

## 2. Creating Entity Classes (Entity)

First, we create two simple entity classes, each belonging to a different data source, to demonstrate saving and querying data across multiple data sources.

PrimaryTable entity class (belonging to the primary data source):

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

Other entity class:

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

Note that these two entity classes belong to different packages, which is critically important: Spring decides which data source to use based on the package each entity class belongs to.

<!-- more -->

## 3. Creating Repositories

Create the repositories corresponding to the two entity classes respectively, used for performing data operations.

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

Thanks to the excellent encapsulation of spring-data-jpa, we only need to create an interface to gain the ability to operate on the entity classes.

## 4. Configuring the Multiple Data Sources

Configure a corresponding data source for each of the PrimaryTable and Other entity classes. The configuration mainly consists of three elements:

1. dataSource, the data source connection information
2. entityManagerFactory, data processing
3. transactionManager, transaction management

The data source configuration for the primary data source, PrimaryDataConfig:

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

The @Primary annotation in the code indicates that this is the default data source. The primary data source connection information is bound by primaryDataSourceProperties from the spring.datasource properties and built into a HikariDataSource via initializeDataSourceBuilder, while the connection pool settings are bound from spring.datasource.hikari. Note that in Spring Boot 4, DataSourceProperties lives in the org.springframework.boot.jdbc.autoconfigure package, JpaProperties in the org.springframework.boot.jpa.autoconfigure package, and EntityManagerFactoryBuilder in the org.springframework.boot.jpa package.

The data source configuration for the Other entity class, OtherDataConfig:

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

The second data source cannot reuse the auto-configured JpaProperties directly (it is bound to the spring.jpa prefix). Instead, a custom OtherJpaProperties class is bound to the other.jpa prefix, keeping the JPA configuration of the two data sources independent:

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

## 5. Data Operations

We create a service class DbService to perform data operations on the two data sources respectively.

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

Data is inserted into and read from PrimaryTable and Other respectively; after the program runs, it prints the data from each of the two data sources. The primary data source uses an H2 in-memory database (MySQL compatibility mode) in the example, so no preparation is needed; the second data source uses MySQL, with the connection information configured in application.yml.

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

The PrimaryTable entity maps to the primary data source and reads the spring.datasource and spring.datasource.hikari sections, while the Other entity has its own data source connection configuration. Which section of configuration is read is specified by this line of code in the OtherDataConfig configuration class.

```java
@ConfigurationProperties(prefix = "other.datasource")
```

The MySQL database used by the second data source needs to be created in advance (the example uses root/root as the credentials; adjust them to your environment):

```shell
create database demo;
```

## 6. Summary

spring-data-jpa greatly simplifies database operations, and supporting multiple data sources merely requires adding some configuration files and configuration classes. There are three key points:

1. The data source configuration in the configuration file

2. Writing the configuration classes

3. The package of the entity classes must match the package specified in the configuration class, e.g. the basePackages = {"cn.springcamp.springdatajpa.multisource.other.data"} specified in OtherDataConfig
