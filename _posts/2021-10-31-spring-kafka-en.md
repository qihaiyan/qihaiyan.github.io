---
layout: post
title:  "Three Ways to Use Kafka in Spring (listener, container, stream)"
date:   2021-10-31 16:20:00 +0800
lang: en
slug_zh: spring-kafka
tags: [spring,java]
categories: [spring boot]
image: assets/images/spring-kafka.jpeg
description: "Three ways to consume Kafka in Spring compared: @KafkaListener, ConcurrentMessageListenerContainer, and spring-cloud-stream, to help you pick the right one."
---

This post introduces three ways to use Kafka with Spring: the container approach is the most flexible but relatively complex to develop, the stream approach is the simplest to use, and the listener approach, being the oldest, is the most widely used.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-kafka](https://github.com/qihaiyan/springcamp/tree/main/spring-kafka).

## 1. Overview

In real-world projects, Kafka is extremely common, especially in event-driven programming models, where Kafka is essentially the default choice.

## 2. KafkaListener

KafkaListener is probably the most widely used approach today: it is simple to develop with and easy to understand. From a usability standpoint, however, it will likely be gradually replaced by spring-cloud-stream.
KafkaListener is an annotation; adding it to a method makes that method process the received Kafka messages. The topic to consume is specified with the topics parameter, which supports SpEL expressions and can consume multiple Kafka topics at the same time:

```java
@KafkaListener(topics = "test-topic")
    public void receive(ConsumerRecord<String, String> consumerRecord) {
        this.payload = consumerRecord.value();
        log.info("received payload='{}'", payload);
    }
```

The parameter of the annotated method is a ConsumerRecord variable that holds the message received from Kafka.

Kafka also needs to be configured: you can specify the address of the Kafka server and the serialization method:

```yml
spring.kafka:
    bootstrap-servers: 192.168.1.1:2181
    consumer:
      group-id: utgroup
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
```

## 3. ConcurrentMessageListenerContainer

ConcurrentMessageListenerContainer lets you consume Kafka messages programmatically. The advantage of this approach is that the topic is specified in code, so the topic configuration can be stored anywhere, for example in a database, and different topics can be chosen based on different condition branches. It is very flexible — something the other two approaches cannot do.

Configuring ConcurrentMessageListenerContainer:

``` java
@Component
public class MessageListenerContainerConsumer {

    public static final String LISTENER_CONTAINER_TOPIC = "container-topic";

    public Set<String> consumedMessages = new HashSet<>();

    @PostConstruct
    void start() {
        MessageListener<String, String> messageListener = record -> {
            System.out.println("MessageListenerContainerConsumer received message: " + record.value());
            consumedMessages.add(record.value());
        };

        ConcurrentMessageListenerContainer<String, String> container =
                new ConcurrentMessageListenerContainer<>(
                        consumerFactory(),
                        containerProperties(LISTENER_CONTAINER_TOPIC, messageListener));

        container.start();
    }

    private DefaultKafkaConsumerFactory<String, String> consumerFactory() {
        return new DefaultKafkaConsumerFactory<>(
                new HashMap<String, Object>() {
                    {
                        put(BOOTSTRAP_SERVERS_CONFIG, System.getProperty("spring.kafka.bootstrap-servers"));
                        put(GROUP_ID_CONFIG, "groupId");
                        put(AUTO_OFFSET_RESET_CONFIG, "earliest");
                    }
                },
                new StringDeserializer(),
                new StringDeserializer());
    }

    private ContainerProperties containerProperties(String topic, MessageListener<String, String> messageListener) {
        ContainerProperties containerProperties = new ContainerProperties(topic);
        containerProperties.setMessageListener(messageListener);
        return containerProperties;
    }
}
```

The code above defines the MessageListenerContainerConsumer class, which is a Spring bean. In the bean's @PostConstruct initialization code we create a ConcurrentMessageListenerContainer and specify the topic ```public static final String LISTENER_CONTAINER_TOPIC = "container-topic"```. For demonstration purposes we use a constant here, but in practice the topic value can be any variable: it can be read from a database or computed dynamically based on the actual scenario, which makes the topic configuration fully flexible.

## 4. spring-cloud-stream

spring-cloud-stream is a subproject of Spring Cloud whose goal is to be an event-driven programming framework. spring-cloud-stream provides a very good abstraction over Kafka — besides Kafka, it also supports RabbitMQ — and apart from the configuration file, no trace of Kafka appears in the code. That means we don't need to care about the underlying Kafka details when developing; if we want to switch from Kafka to RabbitMQ, we only need to change the jar dependency and the configuration file.

For details, see the official Spring documentation: [https://spring.io/projects/spring-cloud-stream](https://spring.io/projects/spring-cloud-stream)

spring-cloud-stream is built on spring-cloud-function: we only need to implement a function interface in our code to process Kafka messages, which is very simple to write.

``` java
i@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Bean
    public Function<String, Object> handle() {
        return String::toUpperCase;
    }
}
```

Apart from the configuration file, the only line of code needed to process Kafka messages is ```public Function<String, Object> handle()```. Nothing in this line reveals any relation to Kafka — it is just an ordinary method, the abstraction taken to the extreme.
Note that the method name must match the name in the configuration file.

Configuration:

``` yml
spring:
  cloud.stream:
    bindings:
      handle-in-0:
        destination: testEmbeddedIn
        content-type: text/plain
        group: utgroup
      handle-out-0:
        destination: testEmbeddedOut
    kafka:
      binder:
        brokers: 192.168.1.1:2181
        configuration:
          key.serializer: org.apache.kafka.common.serialization.ByteArraySerializer
          value.serializer: org.apache.kafka.common.serialization.ByteArraySerializer
```

Note the ```handle-in-0``` and ```handle-out-0``` entries in the configuration file: handle refers to the ```public Function<String, Object> handle()``` method in the code above. spring-cloud-stream matches code and configuration through the method name and the configuration key name, which reflects the convention-over-configuration programming philosophy.
