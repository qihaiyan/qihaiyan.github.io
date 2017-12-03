---
layout: post
title:  "SpringBoot项目中的多数据源支持"
date:   2017-10-20 10:00:00 +0800
tags: [spring,JPA]
categories: [spring]
---
## 1.概述

项目中经常会遇到一个应用需要访问多个数据源的情况，本文介绍在SpringBoot项目中利用SpringDataJpa技术如何支持多个数据库的数据源。

具体的代码参照该 [示例项目](https://github.com/qihaiyan/boot-multi-datasource)

## 2.建立实体类（Entity）

首先，我们创建两个简单的实体类，分别属于两个不同的数据源，用于演示多数据源数据的保存和查询。

Test实体类：

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

Other实体类：

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

需要注意的是，这两个实体类分属于不同的package，这一点极为重要，spring会根据实体类所属的package来决定用那一个数据源进行操作。

<!-- more -->

## 3.建立Repository

分别建立两个实体类对应的Repository，用于进行数据操作。

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

得益于spring-data-jpa优秀的封装，我们只需创建一个接口，就拥有了对实体类的操作能力。

## 3.对多数据源进行配置

分别对Test和Other两个实体类配置对应的数据源。配置的内容主要包含三个要素：

1. dataSource，数据源的连接信息
2. entityManagerFactory，数据处理
3. transactionManager，事务管理

Test实体类的数据源配置 TestDataConfig：

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

代码中的Primary注解表示这是默认数据源。

Other实体类的数据源配置 OtherDataConfig：

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

## 3.数据操作

我们创建一个Service类TestService来分别对两个数据源进行数据的操作。

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

对Test和Other分别进行数据插入和读取操作，程序运行后会打印出两个数据源各自的数据。
数据库采用的mysql，连接信息在application.yml进行配置。

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

Test实体对应的是主数据源，采用了spring-boot的默认数据源配置项，Other实体单独配置数据源连接。具体应该读取哪一段配置内容，是在配置类OtherDataConfig中这行代码指定的。

```java
@ConfigurationProperties(prefix = "other.datasource")
```

本示例需要建立的数据库用户和库可以通过以下命令处理：

```shell
CREATE USER 'test'@'localhost' IDENTIFIED BY '11111111';
GRANT ALL PRIVILEGES ON *.* TO 'test'@'localhost';
CREATE USER 'other'@'localhost' IDENTIFIED BY '11111111';
GRANT ALL PRIVILEGES ON *.* TO 'other'@'localhost';
create database test;
create database other;
```

## 4.总结

spring-data-jpa极大的简化了数据库操作，对于多数据源的支持，也只是需要增加一下配置文件和配置类而已。其中的关键内容有3点：

1. 配置文件中数据源的配置

2. 配置类的编写

3. 实体类所在的package必须与配置类中指定的package一致，如OtherDataConfig中指定的basePackages = {"com.example.demo.other.data"}