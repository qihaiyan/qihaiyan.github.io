---
layout: post
title:  "SpringBoot项目中使用redis缓存"
date:   2017-12-03 15:15:00 +0800
tags: [spring,redis]
categories: [spring]
---
## 1.概述

在应用中有效的利用redis缓存可以很好的提升系统性能，特别是对于查询操作，可以有效的减少数据库压力。

具体的代码参照该 [示例项目](https://github.com/qihaiyan/boot-multi-datasource)

## 2.添加引用

在build.gradle加入
```
compile('org.springframework.boot:spring-boot-starter-data-redis')
```
SpringBoot会自动引入redis相关的jar包。加入该引用后，需要在本地安装redis并启动，否则程序启动时会报错。

## 3.通过注解启用缓存

在SpringBoot中启用redis非常简单，只需要在Application主类上添加```@EnableCaching```注解，之后在需要启用缓存的查询方法上添加```@Cacheable```注解。

```java
@SpringBootApplication
@EnableCaching
public class DemoApplication implements CommandLineRunner{
...
```

<!-- more -->

查询接口：

```java
public interface TestRepository extends JpaRepository<Test, Integer> {
    @Cacheable(value = "testCache")
    public Test findOne(Integer id);
}
```

实体类需要实现Serializable接口，否则程序会报错，因为无法把java对象序列化到redis中。SpringBoot中redis默认使用DefaultSerializer，这个用的是jdk自身的序列化方法。

总共有以下几种序列化方法，具体的使用场景可以参考[官方文档](https://docs.spring.io/spring-data/redis/docs/1.8.9.RELEASE/reference/html/#redis:serializer)

```
1. GenericJackson2JsonRedisSerializer
2. GenericToStringSerializer
3. Jackson2JsonRedisSerializer
4. JacksonJsonRedisSerializer
5. JdkSerializationRedisSerializer
6. OxmSerializer
7. StringRedisSerializer
```

至此我们的程序就具有了从redis缓存中查询数据的能力，如果对redis中存储的KEY的美观程度不介意的话，工作到此就结束了。

## 4.美观的KEY

执行我们的程序以后，在redis-cli中执行```KEY *```命令，会发现key的值是一堆类似于乱码的东西:

```
"testCache:\xac\xed\x00\x05sr\x00\x11java.lang.Integer\x12\xe2\xa0\xa4\xf7\x81\x878\x02\x00\x01I\x00\x05valuexr\x00\x10java.lang.Number\x86\xac\x95\x1d\x0b\x94\xe0\x8b\x02\x00\x00xp\x00\x00\x00\x01"
```

这中key值对于redis的运维人员来说估计是不可接受的，我们要想办法让key值变的好看一些，至少要让人能看得懂。

出现上面的key值的原因就是spring中默认采用了SimpleKey这个类来生成redis的key。

解决方法也很简单，增加缓存配置，指定redis生成key的方式：

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

其中

```java
redisTemplate.setKeySerializer(new GenericToStringSerializer<Object>(Object.class));
```

这行代码指定了redis中key值的生成方式，```GenericToStringSerializer```这个序列化方法会把java对象转换为字符串存储到redis中。

## 5.总结

在SpringBoot中启用redis缓存非常简单，只需要加几个注解即可。同时我们可以通过增加缓存配置的方式，让存储到redis中的key值具有良好的可读性，而不是一堆类似于乱码的数据。