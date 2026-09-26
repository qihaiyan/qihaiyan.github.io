---
layout: post
title:  "Converting LocalDateTime to Epoch Timestamps in Spring REST APIs"
date:   2022-04-04 17:50:00 +0800
lang: en
slug_zh: spring-localdatetime-epoch
tags: [spring,java]
categories: [spring boot]
image: assets/images/epoch.jpg
description: "Convert LocalDateTime to UTC Epoch timestamps in Spring REST APIs via a global Jackson2ObjectMapperBuilderCustomizer, with no changes to business code."
---

This post shows how to convert the LocalDateTime date type to timestamps in Spring REST APIs.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-localdatetime-epoch](https://github.com/qihaiyan/springcamp/tree/main/spring-redis-spring-localdatetime-epoch)

## 1. Overview

Java programs usually define date types as LocalDateTime, and the times stored in the database are in the zero time zone (UTC). For APIs, to support globalization across multiple time zones, date fields typically return UTC timestamps, commonly abbreviated as Epoch, with a data type of long. The frontend then converts the timestamp into a date-format string according to the local time zone, such as YYYY-mm-dd HH:mm:ss.

Converting every time field when the API returns a response would be tedious. This conversion should be handled in one unified place, so that the business logic is unaware of it.

## 2. Global Type Conversion with Jackson2ObjectMapperBuilderCustomizer

Spring provides the ```Jackson2ObjectMapperBuilderCustomizer``` for customizing the conversion between JSON and objects.

With a custom ```Jackson2ObjectMapperBuilderCustomizer```, we can complete the conversion between LocalDateTime and Epoch during the JSON/object conversion stage, covering both API inputs and outputs.

``` java
@Configuration
public class LocalDateTimeToEpochSerdeConfig {

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer jackson2ObjectMapperBuilderCustomizer() {
        return builder -> builder.serializerByType(LocalDateTime.class, new LocalDateTimeToEpochSerializer())
                .deserializerByType(LocalDateTime.class, new LocalDateTimeFromEpochDeserializer());
    }

    /**
     * Serialization
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
     * Deserialization
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

The code above contains both JSON serialization and deserialization. In the serialization part, LocalDateTime is converted to an Epoch timestamp.

``` java
   /**
     * Serialization
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

In the deserialization part, the Epoch timestamp is converted back to LocalDateTime.

``` java
   /**
     * Deserialization
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

With this configuration, we can use the LocalDateTime type in entity classes. When a client calls the API, response results are automatically converted to Epoch values, and request parameters are automatically converted from Epoch to LocalDateTime.
