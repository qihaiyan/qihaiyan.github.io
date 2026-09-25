---
layout: post
title:  "Multiple Data Sources in a Spring Boot Project"
date:   2017-10-20 10:00:00 +0800
lang: en
slug_zh: spring-jpa-multi-datasource
tags: [spring]
categories: [spring boot]
image: assets/images/datasource.jpg
description: "How to support multiple data sources in Spring Boot with Spring Data JPA, configuring an EntityManagerFactory and transaction manager per package."
---
## 1. Overview

It is quite common for an application to need to access multiple data sources. This post describes how to support multiple database data sources in a Spring Boot project using Spring Data JPA.

The complete code is available in the example project [https://github.com/qihaiyan/boot-multi-datasource](https://github.com/qihaiyan/boot-multi-datasource).

## 2. Creating Entity Classes (Entity)

First, we create two simple entity classes, each belonging to a different data source, to demonstrate saving and querying data across multiple data sources.

Test entity class:

```java
package com.example.demo.test.data;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

@Entity
@Table(name = "test")
public class Test {

    @Id
    private Integer id;

    public Test(){

    }

    public Integer getId() {
        return this.id;
    }

    public void setId(Integer id){
        this.id = id;
    }
}
```

Other entity class:

```java
package com.example.demo.other.data;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

@Entity
@Table(name = "other")
public class Other {

    @Id
    private Integer id;

    public Integer getId() {
        return this.id;
    }

    public void setId(Integer id){
        this.id = id;
    }
}
```

Note that these two entity classes belong to different packages, which is critically important: Spring decides which data source to use based on the package each entity class belongs to.

<!-- more -->

## 3. Creating Repositories

Create the repositories corresponding to the two entity classes respectively, used for performing data operations.

TestRepository:

```java
package com.example.demo.test.data;

import org.springframework.data.jpa.repository.JpaRepository;

public interface TestRepository extends JpaRepository<Test, Integer> {
}
```

OtherRepository:

```java
package com.example.demo.other.data;

import org.springframework.data.jpa.repository.JpaRepository;

public interface OtherRepository extends JpaRepository<Other, Integer> {
}
```

Thanks to the excellent encapsulation of spring-data-jpa, we only need to create an interface to gain the ability to operate on the entity classes.

## 3. Configuring the Multiple Data Sources

Configure a corresponding data source for each of the Test and Other entity classes. The configuration mainly consists of three elements:

1. dataSource, the data source connection information
2. entityManagerFactory, data processing
3. transactionManager, transaction management

The data source configuration for the Test entity class, TestDataConfig:

``` java
package com.example.demo.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.jdbc.DataSourceBuilder;
import org.springframework.boot.autoconfigure.orm.jpa.JpaProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.orm.jpa.EntityManagerFactoryBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.persistence.EntityManagerFactory;
import javax.sql.DataSource;

@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
        entityManagerFactoryRef = "entityManagerFactory",
        basePackages = {"com.example.demo.test.data"}
)
public class TestDataConfig {

    @Autowired
    private JpaProperties jpaProperties;

    @Primary
    @Bean(name = "dataSource")
    @ConfigurationProperties(prefix = "spring.datasource")
    public DataSource dataSource() {
        return DataSourceBuilder.create().build();
    }

    @Primary
    @Bean(name = "entityManagerFactory")
    public LocalContainerEntityManagerFactoryBean entityManagerFactory(
            EntityManagerFactoryBuilder builder,
            @Qualifier("dataSource") DataSource dataSource) {
        return builder
                .dataSource(dataSource)
                .packages("com.example.demo.test.data")
                .properties(jpaProperties.getHibernateProperties(dataSource))
                .persistenceUnit("test")
                .build();
    }

    @Primary
    @Bean(name = "transactionManager")
    public PlatformTransactionManager transactionManager(
            @Qualifier("entityManagerFactory") EntityManagerFactory entityManagerFactory) {
        return new JpaTransactionManager(entityManagerFactory);
    }

}

```

The @Primary annotation in the code indicates that this is the default data source.

The data source configuration for the Other entity class, OtherDataConfig:

```java
package com.example.demo.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.jdbc.DataSourceBuilder;
import org.springframework.boot.autoconfigure.orm.jpa.JpaProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.orm.jpa.EntityManagerFactoryBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.persistence.EntityManagerFactory;
import javax.sql.DataSource;

@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(
        entityManagerFactoryRef = "otherEntityManagerFactory",
        transactionManagerRef = "otherTransactionManager",
        basePackages = {"com.example.demo.other.data"}
)
public class OtherDataConfig {

    @Autowired
    private JpaProperties jpaProperties;

    @Bean(name = "otherDataSource")
    @ConfigurationProperties(prefix = "other.datasource")
    public DataSource otherDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean(name = "otherEntityManagerFactory")
    public LocalContainerEntityManagerFactoryBean otherEntityManagerFactory(
            EntityManagerFactoryBuilder builder,
            @Qualifier("otherDataSource") DataSource otherDataSource) {
        return builder
                .dataSource(otherDataSource)
                .packages("com.example.demo.other.data")
                .properties(jpaProperties.getHibernateProperties(otherDataSource))
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

## 3. Data Operations

We create a service class TestService to perform data operations on the two data sources respectively.

```java
package com.example.demo.service;

import com.example.demo.other.data.Other;
import com.example.demo.other.data.OtherRepository;
import com.example.demo.test.data.Test;
import com.example.demo.test.data.TestRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class TestService {

    @Autowired
    private TestRepository testRepository;

    @Autowired
    private OtherRepository otherRepository;

    @Value("${name:World}")
    private String name;

    public String getHelloMessage() {
        Test test = new Test();
        test.setId(1);
        test = testRepository.save(test);

        Other other = new Other();
        other.setId(2);
        other = otherRepository.save(other);

        return "Hello " + this.name + " : test's value = " + test.getId() + " , other's value = " + other.getId();

    }

}

```

Data is inserted into and read from Test and Other respectively; after the program runs, it prints the data from each of the two data sources.
MySQL is used as the database, with the connection information configured in application.yml.

```yml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/test?characterEncoding=utf-8&useSSL=false
    testWhileIdle: true
    validationQuery: SELECT 1 from dual
    username: test
    password: 11111111
    driverClassName: com.mysql.jdbc.Driver
  jpa:
    database: MYSQL
    show-sql: true
    hibernate:
      show-sql: true
      ddl-auto: create
      naming-strategy: org.hibernate.cfg.ImprovedNamingStrategy
    properties:
      hibernate.dialect: org.hibernate.dialect.MySQL5Dialect
other:
  datasource:
    url: jdbc:mysql://localhost:3306/other?characterEncoding=utf-8&useSSL=false
    testWhileIdle: true
    validationQuery: SELECT 1
    username: other
    password: 11111111
    driverClassName: com.mysql.jdbc.Driver
  jpa:
    database: MYSQL
    show-sql: true
    hibernate:
      show-sql: true
      ddl-auto: create
      naming-strategy: org.hibernate.cfg.ImprovedNamingStrategy
    properties:
      hibernate.dialect: org.hibernate.dialect.MySQL5Dialect
```

The Test entity maps to the primary data source and uses spring-boot's default data source configuration properties, while the Other entity has its own data source connection configuration. Which section of configuration is read is specified by this line of code in the OtherDataConfig configuration class.

```java
@ConfigurationProperties(prefix = "other.datasource")
```

The database users and databases needed for this example can be created with the following commands:

```shell
CREATE USER 'test'@'localhost' IDENTIFIED BY '11111111';
GRANT ALL PRIVILEGES ON *.* TO 'test'@'localhost';
CREATE USER 'other'@'localhost' IDENTIFIED BY '11111111';
GRANT ALL PRIVILEGES ON *.* TO 'other'@'localhost';
create database test;
create database other;
```

## 4. Summary

spring-data-jpa greatly simplifies database operations, and supporting multiple data sources merely requires adding some configuration files and configuration classes. There are three key points:

1. The data source configuration in the configuration file

2. Writing the configuration classes

3. The package of the entity classes must match the package specified in the configuration class, e.g. the basePackages = {"com.example.demo.other.data"} specified in OtherDataConfig
