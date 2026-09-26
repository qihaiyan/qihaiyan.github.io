---
layout: post
title:  "Using Redis Cache in a Spring Boot Project"
date:   2017-12-03 15:15:00 +0800
lang: en
slug_zh: spring-data-cache
tags: [spring,redis]
categories: [spring boot]
image: assets/images/cache.png
description: "How to enable Redis caching in Spring Boot with @Cacheable to reduce database load and improve query performance, including serialization configuration."
---
## 1. Overview

Using the Redis cache effectively in an application can greatly improve system performance; for queries in particular, it can effectively reduce the load on the database.

The complete code is available in the example project [https://github.com/qihaiyan/boot-multi-datasource](https://github.com/qihaiyan/boot-multi-datasource).

## 2. Adding the Dependency

Add the following to build.gradle
```
compile('org.springframework.boot:spring-boot-starter-data-redis')
```
Spring Boot automatically pulls in the Redis-related jars. After adding this dependency, you need to install and start Redis locally, otherwise the application reports an error at startup.

## 3. Enabling Caching with Annotations

Enabling Redis in Spring Boot is very simple: just add the ```@EnableCaching``` annotation to the main Application class, then add the ```@Cacheable``` annotation to the query methods that should use the cache.

```java
@SpringBootApplication
@EnableCaching
public class DemoApplication implements CommandLineRunner{
...
```

<!-- more -->

The query interface:

```java
public interface TestRepository extends JpaRepository<Test, Integer> {
    @Cacheable(value = "testCache")
    public Test findOne(Integer id);
}
```

The entity class must implement the Serializable interface, otherwise the program throws an error because the Java object cannot be serialized into Redis. By default, Spring Boot's Redis support uses DefaultSerializer, which is the JDK's own serialization.

There are the following serializers in total; see the [official documentation](https://docs.spring.io/spring-data/redis/docs/1.8.9.RELEASE/reference/html/#redis:serializer) for the use cases of each:

```
1. GenericJackson2JsonRedisSerializer
2. GenericToStringSerializer
3. Jackson2JsonRedisSerializer
4. JacksonJsonRedisSerializer
5. JdkSerializationRedisSerializer
6. OxmSerializer
7. StringRedisSerializer
```

At this point our application can query data from the Redis cache. If you don't mind how the KEYS stored in Redis look, the work ends here.

## 4. Readable Keys

After running our application, executing the ```KEY *``` command in redis-cli shows that the key values look like a pile of gibberish:

```
"testCache:\xac\xed\x00\x05sr\x00\x11java.lang.Integer\x12\xe2\xa0\xa4\xf7\x81\x878\x02\x00\x01I\x00\x05valuexr\x00\x10java.lang.Number\x86\xac\x95\x1d\x0b\x94\xe0\x8b\x02\x00\x00xp\x00\x00\x00\x01"
```

This kind of key value is probably unacceptable to anyone operating Redis, so we need to make the keys look nicer — at least human-readable.

The reason for the keys shown above is that Spring uses the SimpleKey class by default to generate Redis keys.

The solution is also simple: add a cache configuration that specifies how Redis keys are generated:

```java
@Configuration
public class CacheConfig extends CachingConfigurerSupport {

    @Autowired
    private RedisTemplate redisTemplate;

    @Bean
    public CacheManager cacheManager() {

        redisTemplate.setKeySerializer(new GenericToStringSerializer<Object>(Object.class));

        RedisCacheManager cacheManager = new RedisCacheManager(redisTemplate);
        cacheManager.setDefaultExpiration(3600);
        cacheManager.setUsePrefix(true);
        cacheManager.setCachePrefix(new RedisCachePrefix() {
            private final RedisSerializer<String> serializer = new StringRedisSerializer();
            private final String delimiter = ":";

            public byte[] prefix(String cacheName) {
                return this.serializer
                        .serialize(cacheName.concat(this.delimiter));
            }
        });

        return cacheManager;
    }
}
```

Among them,

```java
redisTemplate.setKeySerializer(new GenericToStringSerializer<Object>(Object.class));
```

this line specifies how Redis key values are generated: the ```GenericToStringSerializer``` serializer converts Java objects into strings before storing them in Redis.

## 5. Summary

Enabling Redis caching in Spring Boot is very simple — a few annotations are all it takes. In addition, by adding a cache configuration we can give the keys stored in Redis good readability instead of a pile of gibberish.
