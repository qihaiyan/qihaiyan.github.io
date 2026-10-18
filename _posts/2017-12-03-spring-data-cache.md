---
layout: post
title:  "SpringBoot项目中使用redis缓存"
description: "介绍在 Spring Boot 中通过 Spring Data Redis 与 @Cacheable 等注解启用 Redis 缓存的方法，有效减少数据库压力、提升查询性能，并讲解可读的缓存 Key、JSON 序列化、过期时间等配置细节。本文已针对 Spring Boot 3.x / 4.x 全面更新。"
date:   2017-12-03 15:15:00 +0800
tags: [spring,redis]
categories: [spring boot]
image: assets/images/cache.png
---
## 1.概述

在应用中有效的利用redis缓存可以很好的提升系统性能，特别是对于查询操作，可以有效的减少数据库压力。

本文最早写于 2017 年（Spring Boot 1.x 时代），已经针对 Spring Boot 3.x / 4.x 全面更新。旧版文章中的 ```RedisCacheManager``` 配置代码在现行版本中已无法编译，如果你是从搜索引擎找到旧内容的，请以本文为准。

具体的代码参照该 [示例项目](https://github.com/qihaiyan/springcamp) 中的 ```spring-cache``` 模块。

## 2.添加依赖

在build.gradle加入

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-redis'
}
```

SpringBoot会自动引入redis相关的依赖，客户端默认使用Lettuce。运行程序前需要先启动一个redis服务，例如使用Docker：

```
docker run -d --name redis -p 6379:6379 redis
```

否则在读写缓存时会报连接错误。

## 3.通过注解启用缓存

在SpringBoot中启用redis缓存非常简单，只需要在Application主类上添加```@EnableCaching```注解，之后在需要启用缓存的查询方法上添加```@Cacheable```注解。

```java
@SpringBootApplication
@EnableCaching
public class DemoApplication {
...
```

<!-- more -->

查询接口：

```java
public interface TestRepository extends JpaRepository<Test, Integer> {

    @Override
    @Cacheable(value = "testCache", key = "#id")
    Optional<Test> findById(Integer id);
}
```

与旧版文章相比，这里有两个重要的变化：

- Spring Data JPA 2.0 起，```findOne``` 方法更名为 ```findById```，返回值是 ```Optional```。
- ```key = "#id"``` 通过 SpEL 直接指定缓存的Key为方法参数值，生成的Key形如 ```testCache:1```，天然可读。不再需要像旧版文章那样，通过更换Key的序列化器来"美化"Key。

使用参数名 ```#id``` 需要编译时开启 ```-parameters``` 参数，SpringBoot的Gradle/Maven插件默认已经开启。如果你的项目没有使用这些插件，可以改用 ```#a0``` 代替 ```#id```。

旧版文章提到"实体类需要实现Serializable接口"，这仅在默认的JDK序列化方式下成立。按照第5节配置JSON序列化后，实体类不再需要实现 ```Serializable```。

数据发生变更时，可以配合 ```@CachePut``` 和 ```@CacheEvict``` 注解保持缓存与数据库的一致性：

```java
@Override
@CacheEvict(value = "testCache", key = "#id")
void deleteById(Integer id);
```

至此我们的程序就具有了从redis缓存中查询数据的能力。默认配置下value使用JDK序列化存储，内容是二进制数据，且没有过期时间，如果在意这些可以继续进行下面的配置。

## 4.可读的KEY

现行版本的Spring Data Redis默认使用 ```StringRedisSerializer``` 序列化Key，配合 ```key = "#id"``` 生成的Key已经是可读的字符串，在redis-cli中使用 ```SCAN``` 命令可以看到（生产环境不要使用 ```KEYS *```，该命令会阻塞redis）：

```
SCAN 0 MATCH testCache:* COUNT 100
1) "testCache:1"
```

顺便说明一下旧版文章中"乱码"Key的由来：在Spring Data Redis 1.x时代，未指定Key时Spring用 ```SimpleKey``` 对象作为缓存Key，而该对象会经过JDK序列化存储，因此出现了 ```\xac\xed\x00\x05...``` 这样的二进制内容。现行版本中Key默认序列化为字符串，这个问题已经不复存在。

## 5.JSON序列化与过期时间

默认的value序列化方式是JDK序列化，存储内容可读性差，且要求实体类实现 ```Serializable```。通过一个缓存配置类，可以把value的序列化方式改为JSON，同时设置统一的过期时间和Key前缀：

```java
@Configuration
public class CacheConfig implements CachingConfigurer {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {

        RedisCacheConfiguration cacheConfiguration = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofHours(1))
                .computePrefixWith(cacheName -> cacheName.concat(":"))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(connectionFactory)
                .cacheDefaults(cacheConfiguration)
                .build();
    }
}
```

与旧版文章的配置相比，有几个关键变化：

- ```new RedisCacheManager(redisTemplate)``` 构造方法在Spring Data Redis 2.0中已被移除，改用 ```RedisCacheManager.builder(...)``` 来构建。
- 过期时间从 ```setDefaultExpiration(3600)``` 改为 ```entryTtl(Duration.ofHours(1))```。
- ```RedisCachePrefix``` 接口已被移除，定制Key前缀改用 ```computePrefixWith```。
- 配置基类 ```CachingConfigurerSupport``` 在Spring Framework 6.0中已被废弃，直接实现 ```CachingConfigurer``` 接口即可。
- value序列化从JDK序列化改为 ```GenericJackson2JsonRedisSerializer```，redis中存储的是可读的JSON字符串，实体类也无需实现 ```Serializable```。

如果只需要调整过期时间和null值处理，也可以不写代码，直接使用配置项：

```properties
spring.cache.redis.time-to-live=1h
spring.cache.redis.cache-null-values=false
```

需要注意的是，```disableCachingNullValues()``` 禁止缓存null后，查询不到数据时每次请求都会穿透到数据库；如果查询不存在的数据是常态，可以考虑缓存空值或空对象来防止缓存穿透。

最后说明一下版本差异：如果你的项目已经升级到Spring Boot 4.x（对应Spring Data Redis 4.0），JSON序列化器需要从 ```GenericJackson2JsonRedisSerializer```（基于Jackson 2）替换为 ```GenericJacksonJsonRedisSerializer```（基于Jackson 3，包名从 ```com.fasterxml.jackson``` 变为 ```tools.jackson```），示例项目中的 ```spring-cache``` 模块即为Spring Boot 4.x的写法。

## 6.总结

在SpringBoot中启用redis缓存非常简单，只需要加几个注解即可。配合 ```@Cacheable``` 的 ```key``` 属性可以得到可读的缓存Key，通过 ```RedisCacheManager.builder``` 与 ```RedisCacheConfiguration``` 可以进一步定制序列化方式和过期时间，让存储到redis中的数据具有良好的可读性。
