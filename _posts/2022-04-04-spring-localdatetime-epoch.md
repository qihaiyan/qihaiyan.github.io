---
layout: post
title:  "spring-rest接口LocalDateTime转时间戳"
date:   2022-04-04 17:50:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/epoch.jpg
---

本文介绍spring-rest接口中的LocalDateTime日期类型转时间戳的方法。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-localdatetime-epoch](https://github.com/qihaiyan/springcamp/tree/master/spring-redis-spring-localdatetime-epoch)

## 一、概述

java程序中一般将日期类型定义为LocalDateTime，数据库中保存的时间是0时区的时间（UTC时间）。对于接口来说，为了支持全球化多时区，接口中的日期类型通常会返回UTC时间戳，简称Epoch，数据类型为long,前端程序会根据本地时区，将时间戳转换为日期格式的字符串，如YYYY-mm-dd HH:mm:ss。

如果在每个时间型字段在接口返回时都进行转换处理，会比较繁琐。应该在一个统一的地方处理这种转换，业务逻辑处理过程中不感知这种转换。

## 二、通过Jackson2ObjectMapperBuilderCustomizer进行全局类型转换

spring提供了```Jackson2ObjectMapperBuilderCustomizer```可以用于自定义json与对象之间相互转换的处理。

通过自定义```Jackson2ObjectMapperBuilderCustomizer```，我们可以在json与对象的相互转换转换阶段完成LocalDateTime和Epoch之间的转换，包括接口的入参和出参。

``` java
@Configuration
public class LocalDateTimeToEpochSerdeConfig {

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer jackson2ObjectMapperBuilderCustomizer() {
        return builder -> builder.serializerByType(LocalDateTime.class, new LocalDateTimeToEpochSerializer())
                .deserializerByType(LocalDateTime.class, new LocalDateTimeFromEpochDeserializer());
    }

    /**
     * 序列化
     */
    public static class LocalDateTimeToEpochSerializer extends JsonSerializer<LocalDateTime> {
        @Override
        public void serialize(LocalDateTime value, JsonGenerator gen, SerializerProvider serializers)
                throws IOException {
            if (value != null) {
                long timestamp = value.atZone(ZoneId.systemDefault()).toInstant().getEpochSecond();
                gen.writeNumber(timestamp);
            }
        }
    }

    /**
     * 反序列化
     */
    public static class LocalDateTimeFromEpochDeserializer extends JsonDeserializer<LocalDateTime> {
        @Override
        public LocalDateTime deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
            NumberDeserializers.LongDeserializer longDeserializer = new NumberDeserializers.LongDeserializer(Long.TYPE, 0L);
            Long epoch = longDeserializer.deserialize(p, ctxt);
            return LocalDateTime.ofInstant(Instant.ofEpochSecond(epoch), ZoneId.systemDefault());
        }
    }
}
```

以上代码中分别包含了json的序列化和反序列化操作，在序列化操作中，把LocalDateTime转换为Epoch。

``` java
   /**
     * 序列化
     */
    public static class LocalDateTimeToEpochSerializer extends JsonSerializer<LocalDateTime> {
        @Override
        public void serialize(LocalDateTime value, JsonGenerator gen, SerializerProvider serializers)
                throws IOException {
            if (value != null) {
                long timestamp = value.atZone(ZoneId.systemDefault()).toInstant().getEpochSecond();
                gen.writeNumber(timestamp);
            }
        }
    }
```

在反序列化操作中，把Epoch转换为LocalDateTime。

``` java
    /**
     * 反序列化
     */
    public static class LocalDateTimeFromEpochDeserializer extends JsonDeserializer<LocalDateTime> {
        @Override
        public LocalDateTime deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
            NumberDeserializers.LongDeserializer longDeserializer = new NumberDeserializers.LongDeserializer(Long.TYPE, 0L);
            Long epoch = longDeserializer.deserialize(p, ctxt);
            return LocalDateTime.ofInstant(Instant.ofEpochSecond(epoch), ZoneId.systemDefault());
        }
    }
```

通过以上配置，我们可以在实体类中使用LocalDateTime类型。客户端请求接口时，对于返回结果，自动转换为Epoch数据，对于请求参数，自动从Epoch转换为LocalDateTime。
