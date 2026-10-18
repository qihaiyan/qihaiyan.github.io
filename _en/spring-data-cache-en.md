---
layout: post
title:  "Using Redis Cache in a Spring Boot Project"
date:   2017-12-03 15:15:00 +0800
lang: en
slug_zh: spring-data-cache
tags: [spring,redis]
categories: [spring boot]
image: assets/images/cache.png
description: "How to enable Redis caching in Spring Boot with @Cacheable to reduce database load and improve query performance, including readable cache keys, JSON serialization and TTL configuration. Updated for Spring Boot 3.x / 4.x."
---
## 1. Overview

Using the Redis cache effectively in an application can greatly improve system performance; for queries in particular, it can effectively reduce the load on the database.

This article was originally written in 2017 (the Spring Boot 1.x era) and has been fully updated for Spring Boot 3.x / 4.x. The ```RedisCacheManager``` configuration code in the old version no longer compiles on current releases, so if you found the old content through a search engine, please follow this version instead.

The complete code is available in the [example project](https://github.com/qihaiyan/springcamp), in the ```spring-cache``` module.

## 2. Adding the Dependency

Add the following to build.gradle:

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-redis'
}
```

Spring Boot automatically pulls in the Redis-related dependencies, with Lettuce as the default client. Before running the application, you need a Redis server, for example via Docker:

```
docker run -d --name redis -p 6379:6379 redis
```

Otherwise reading from or writing to the cache fails with a connection error.

## 3. Enabling Caching with Annotations

Enabling Redis caching in Spring Boot is very simple: just add the ```@EnableCaching``` annotation to the main Application class, then add the ```@Cacheable``` annotation to the query methods that should use the cache.

```java
@SpringBootApplication
@EnableCaching
public class DemoApplication {
...
```

<!-- more -->

The query interface:

```java
public interface TestRepository extends JpaRepository<Test, Integer> {

    @Override
    @Cacheable(value = "testCache", key = "#id")
    Optional<Test> findById(Integer id);
}
```

Compared with the old version of this article, there are two important changes here:

- Since Spring Data JPA 2.0, the ```findOne``` method has been renamed to ```findById``` and returns an ```Optional```.
- ```key = "#id"``` uses SpEL to specify the cache key directly from the method argument, producing a readable key such as ```testCache:1```. There is no longer any need to "prettify" keys by swapping the key serializer as the old version of this article did.

Using the parameter name ```#id``` requires the ```-parameters``` compiler flag, which the Spring Boot Gradle/Maven plugins enable by default. If your project does not use these plugins, use ```#a0``` instead of ```#id```.

The old version of this article said "the entity class must implement the Serializable interface" — that only holds for the default JDK serialization. With the JSON serialization configured in section 5, the entity class no longer needs to implement ```Serializable```.

When data changes, combine ```@CachePut``` and ```@CacheEvict``` to keep the cache consistent with the database:

```java
@Override
@CacheEvict(value = "testCache", key = "#id")
void deleteById(Integer id);
```

At this point the application can query data from the Redis cache. With the default configuration, values are stored with JDK serialization — binary data with no expiration time — so if that matters to you, continue with the configuration below.

## 4. Readable Keys

Current versions of Spring Data Redis serialize keys with the ```StringRedisSerializer``` by default, so combined with ```key = "#id"``` the keys are already readable strings. In redis-cli you can inspect them with the ```SCAN``` command (never use ```KEYS *``` in production — it blocks Redis):

```
SCAN 0 MATCH testCache:* COUNT 100
1) "testCache:1"
```

For the record, here is where the "gibberish" keys in the old version of this article came from: in the Spring Data Redis 1.x era, when no key was specified Spring used a ```SimpleKey``` object as the cache key, and that object was stored through JDK serialization, producing binary content such as ```\xac\xed\x00\x05...```. In current versions keys are serialized as strings by default, so this problem no longer exists.

## 5. JSON Serialization and Expiration Time

The default value serializer is JDK serialization, which is unreadable and requires entities to implement ```Serializable```. With a cache configuration class you can switch value serialization to JSON and set a global expiration time and key prefix:

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

Compared with the configuration in the old version of this article, several things have changed:

- The ```new RedisCacheManager(redisTemplate)``` constructor was removed in Spring Data Redis 2.0; use ```RedisCacheManager.builder(...)``` instead.
- Expiration moved from ```setDefaultExpiration(3600)``` to ```entryTtl(Duration.ofHours(1))```.
- The ```RedisCachePrefix``` interface was removed; customize the key prefix with ```computePrefixWith```.
- The ```CachingConfigurerSupport``` base class was deprecated in Spring Framework 6.0; simply implement the ```CachingConfigurer``` interface.
- Value serialization moved from JDK serialization to ```GenericJackson2JsonRedisSerializer```, so Redis stores readable JSON strings and entities no longer need to implement ```Serializable```.

If you only need to adjust the TTL and null handling, you can do it without any code, using properties:

```properties
spring.cache.redis.time-to-live=1h
spring.cache.redis.cache-null-values=false
```

Note that once ```disableCachingNullValues()``` forbids caching nulls, every request for a nonexistent record penetrates to the database; if lookups of missing data are common, consider caching empty values or null objects to protect against cache penetration.

One final note on versions: if your project has upgraded to Spring Boot 4.x (Spring Data Redis 4.0), replace the ```GenericJackson2JsonRedisSerializer``` (based on Jackson 2) with ```GenericJacksonJsonRedisSerializer``` (based on Jackson 3; the package root changed from ```com.fasterxml.jackson``` to ```tools.jackson```). The ```spring-cache``` module in the example project shows the Spring Boot 4.x style.

## 6. Summary

Enabling Redis caching in Spring Boot is very simple — a few annotations are all it takes. The ```key``` attribute of ```@Cacheable``` gives you readable cache keys, and ```RedisCacheManager.builder``` together with ```RedisCacheConfiguration``` lets you further customize the serialization and expiration time, so the data stored in Redis stays readable.
