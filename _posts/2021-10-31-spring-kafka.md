---
layout: post
title:  "spring使用kafka的三种方式（listener、container、stream）"
date:   2021-10-31 16:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/spring-kafka.jpeg
---

本文介绍spring中使用Kafka的三种方式，其中container方式最灵活，但是开发相对较复杂，stream方式使用最简便，listener方式由于提供的最早，使用的较普遍。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-kafka](https://github.com/qihaiyan/springcamp/tree/main/spring-kafka)

## 一、概述

在实际项目中，用到kafka的场景非常普遍，特别是事件驱动的编程模式，kafka基本是标配。

## 二、KafkaListener

KafkaListener应该是目前使用比较多的一种方式，开发简单，易于理解。但是从易用性的角度，应该会逐步被spring-cloud-stream所替代。
KafkaListener是一个注解，在对应的方法上加上这个注解，方法就可以处理接收到的kakfa消息，注解中通过topics参数指定需要消费的kakfa的topic，topics参数支持SPEL表达式，可以同时消费多个kafka topic：

```java
@KafkaListener(topics = "test-topic")
    public void receive(ConsumerRecord<String, String> consumerRecord) {
        this.payload = consumerRecord.value();
        log.info("received payload='{}'", payload);
    }
```

带注解的方法的入参是一个ConsumerRecord变量，存放了kafka中接收到的消息。

同时需要对kafka进行配置，可以指定kakfa服务器的地址，以及序列化方式：

```yml
spring.kafka:
    bootstrap-servers: 192.168.1.1:2181
    consumer:
      group-id: utgroup
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
```

## 三、ConcurrentMessageListenerContainer

通过ConcurrentMessageListenerContainer可以已可编程的方式来处理kafka消息，这种方式的好处是topic是在程序中指定的，这样可以将topic的配置存贮在任何地方，比如数据库中，也可以按照不同的条件分支指定不同的topic，非常灵活。这是其它两种方式做不到的。

ConcurrentMessageListenerContainer的配置：

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

以上代码定义了MessageListenerContainerConsumer这个类，是一个spring的bean，在PostConstruct这个bean的初始化代码中，我们使用了ConcurrentMessageListenerContainer，并指定了topic ```public static final String LISTENER_CONTAINER_TOPIC = "container-topic"```，在这个为了便于演示我们使用了一个常量，实际上这个topic的值可以是任意变量，可以从数据库中读取，也可以通过实际的场景动态计算，这样就做到了topic的灵活配置。

## 四、spring-cloud-stream

spring-cloud-stream是springcloud的一个子项目，这个项目的目标是一个事件驱动（Event-Driven）的编程框架。spring-cloud-stream对kafka进行了非常好的抽象，除了kakfa，还支持RabbitMQ，程序中除了配置文件外，完全看不到kafka的痕迹，意味着我们在开发的时候不需要关心底层的kakfa的细节，如果像从kafka切换到RabbitMQ，只需要修改一下引入的jar包和配置文件。

详细介绍见spring的官方文档： [https://spring.io/projects/spring-cloud-stream](https://spring.io/projects/spring-cloud-stream)

spring-cloud-stream是用了spring-cloud-function，我们只需要在程序中实现一个function接口，就可以处理kafka消息，编写非常简单。

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

除了配置文件外，代码中只需要一行代码```public Function<String, Object> handle()```就实现了kafka消息的处理，这行代码完全看不出跟kakfa有什么关系，就是一个普通的方法，把抽象做到了极致。
需要注意方法的名字于配置文件中的名字要匹配。

配置：

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

注意配置文件中 ```handle-in-0``` 和 ```handle-out-0``` 这2行配置，handle指的就是前面代码中的```public Function<String, Object> handle()``` handle这个方法。spring-cloud-stream就是通过方法名和配置文件中配置项的名字，来确立代码和配置的匹配关系，这也是约定优于配置的编程思想的体现。
