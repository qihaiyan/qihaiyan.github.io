---
layout: post
title:  "Spring Boot Unit Testing Techniques"
date:   2021-04-18 17:20:00 +0800
lang: en
slug_zh: spring-boot-unit-test
tags: [spring,java]
categories: [spring boot]
image: assets/images/ut.jpg
description: "Spring Boot unit testing practice: testRestTemplate for REST calls, Mockito for external dependencies, embedded H2 and kafka, no external services needed."
---

Throughout the software delivery process, the unit testing stage is the earliest point where defects can be discovered, and the stage where they can be regression-tested repeatedly. The more thorough the testing done at this stage, the better the software quality is assured.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-unit-test](https://github.com/qihaiyan/springcamp/tree/main/spring-unit-test)

## 1. Overview

End-to-end testing of a feature often depends on many external components, such as databases, redis, kafka, and third-party APIs, and the environment executing the unit tests may be network-restricted and unable to access these external services. Therefore, we want to use unit testing techniques to perform complete functional testing without depending on external services.

## 2. Testing REST Interfaces

springboot provides the testRestTemplate tool for testing endpoints in unit tests. It only requires the relative path of the endpoint, without a domain name or port. This feature is very useful because the web server of the springboot unit test environment runs on a random port, specified by the following annotation:

``` java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
```

Here is how to test our ```/remote``` endpoint with testRestTemplate:

``` java
    @Test
    public void testRemoteCallRest() {
        String resp = testRestTemplate.getForObject("/remote", String.class);
        System.out.println("remote result : " + resp);
        assertThat(resp, is("{\"code\": 200}"));
    }
```

## 3. Third-Party API Dependencies

In the example above, our remote endpoint calls a third-party API ```http://someservice/foo```. Our build server may be network-restricted and unable to access this third-party API, which would make the unit tests impossible to run. We can solve this problem with the ```MockRestServiceServer``` tool provided by springboot.

First, declare a MockRestServiceServer variable

``` java
private MockRestServiceServer mockRestServiceServer;
```

Initialize it during the initialization phase of the unit test

``` java
    @Before
    public void before() {
        mockRestServiceServer = MockRestServiceServer.bindTo(restTemplate).ignoreExpectOrder(true).build();

        this.mockRestServiceServer.expect(manyTimes(), MockRestRequestMatchers.requestTo(Matchers.startsWithIgnoringCase("http://someservice/foo")))
                .andRespond(withSuccess("{\"code\": 200}", MediaType.APPLICATION_JSON));

    }
```

This way, when our unit test calls the ```http://someservice/foo``` endpoint, it always gets the fixed response ```{"code": 200}``` instead of actually accessing the third-party API.

## 4. Database Dependencies

The database dependency is fairly simple: just use h2, an embedded database, so that all database operations are executed against h2.

Using the gradle configuration as an example:

``` groovy
testImplementation 'com.h2database:h2'
```

The database connection in the unit test configuration file uses h2:

``` yaml
spring:
  data:
    url: jdbc:h2:mem:ut;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
    username: sa
    password:
```

Database operations can be performed directly in the unit test code:

``` java
MyDomain myDomain = new MyDomain();
myDomain.setName("test");
myDomain = myDomainRepository.save(myDomain);
```

When we call the endpoint to query the record in the database, the result is found correctly:

``` java
MyDomain resp = testRestTemplate.getForObject("/db?id=" + myDomain.getId(), MyDomain.class);
System.out.println("db result : " + resp);
assertThat(resp.getName(), is("test"));
```

When an endpoint returns Page pagination data, some special handling is required, otherwise a JSON serialization error occurs.

Define our own Page class:

``` java
    public class TestRestResponsePage<T> extends PageImpl<T> {
    @JsonCreator(mode = JsonCreator.Mode.PROPERTIES)
    public TestRestResponsePage(@JsonProperty("content") List<T> content,
                                @JsonProperty("number") int number,
                                @JsonProperty("size") int size,
                                @JsonProperty("pageable") JsonNode pageable,
                                @JsonProperty("empty") boolean empty,
                                @JsonProperty("sort") JsonNode sort,
                                @JsonProperty("first") boolean first,
                                @JsonProperty("totalElements") long totalElements,
                                @JsonProperty("totalPages") int totalPages,
                                @JsonProperty("numberOfElements") int numberOfElements) {

        super(content, PageRequest.of(number, size), totalElements);
    }

    public TestRestResponsePage(List<T> content) {
        super(content);
    }

    public TestRestResponsePage() {
        super(new ArrayList<>());
    }
}
```

Call the endpoint and receive the custom Page class:

``` java
RequestEntity<Void> requestEntity = RequestEntity.get("/dbpage").build();
ResponseEntity<TestRestResponsePage<MyDomain>> pageResp = testRestTemplate.exchange(requestEntity, new ParameterizedTypeReference<TestRestResponsePage<MyDomain>>() {
    });
System.out.println("dbpage result : " + pageResp);
assertThat(pageResp.getBody().getTotalElements(), is(1L));
```

Since the return type is generic, we need to use the ```testRestTemplate.exchange``` method; the get methods do not support generic return types.

## 5. Redis Dependencies

There is an open source redis mock server that imitates most redis commands; we only need to include this redis-mockserver.
The original version was developed by a Chinese developer. The example uses a version forked by someone else that added some commands, but its source code can no longer be found, so I forked another version and added the setex and zscore commands. You can build it yourself if needed. The code is available at [https://github.com/qihaiyan/redis-mock](https://github.com/qihaiyan/redis-mock)

Using the gradle configuration as an example:

``` groovy
testImplementation 'com.github.fppt:jedis-mock:1.0.1'
```

The connection in the unit test configuration file uses the redis mock server:

``` yaml
spring:
  redis:
    port: 10033
```

Add a separate redis configuration class that starts the redis mock server during unit tests:

``` java
@TestConfiguration
public class TestRedisConfiguration {

    private final RedisServer redisServer;

    public TestRedisConfiguration(@Value("${spring.redis.port}") final int redisPort) throws IOException {
        redisServer = RedisServer.newRedisServer(redisPort);
    }

    @PostConstruct
    public void postConstruct() throws IOException {
        redisServer.start();
    }

    @PreDestroy
    public void preDestroy() {
        redisServer.stop();
    }
}
```

## 6. Kafka Dependencies

Spring provides a kafka test component that can start an embedded kafka broker, EmbeddedKafka, during unit tests to simulate real kafka operations.

Using the gradle configuration as an example:

``` groovy
testImplementation "org.springframework.kafka:spring-kafka-test"
```

Initialize EmbeddedKafka with a ClassRule; there are two topics: testEmbeddedIn and testEmbeddedOut.

``` java
    private static final String INPUT_TOPIC = "testEmbeddedIn";
    private static final String OUTPUT_TOPIC = "testEmbeddedOut";
    private static final String GROUP_NAME = "embeddedKafkaApplication";

    @ClassRule
    public static EmbeddedKafkaRule embeddedKafkaRule = new EmbeddedKafkaRule(1, true, INPUT_TOPIC, OUTPUT_TOPIC);

    public static EmbeddedKafkaBroker embeddedKafka = embeddedKafkaRule.getEmbeddedKafka();

    private static KafkaTemplate<String, String> kafkaTemplate;

    private static Consumer<String, String> consumer;

    @BeforeClass
    public static void setup() {

        Map<String, Object> senderProps = KafkaTestUtils.producerProps(embeddedKafka);
        DefaultKafkaProducerFactory<String, String> pf = new DefaultKafkaProducerFactory<>(senderProps);
        kafkaTemplate = new KafkaTemplate<>(pf, true);

        Map<String, Object> consumerProps = KafkaTestUtils.consumerProps(GROUP_NAME, "false", embeddedKafka);
        DefaultKafkaConsumerFactory<String, String> cf = new DefaultKafkaConsumerFactory<>(consumerProps);
        consumer = cf.createConsumer();
        embeddedKafka.consumeFromAnEmbeddedTopic(consumer, OUTPUT_TOPIC);
    }

```

In the unit test configuration file, these two kafka topics can be specified

``` yaml
cloud.stream.bindings:
    handle-out-0.destination: testEmbeddedOut
    handle-in-0.destination: testEmbeddedIn
    handle-in-0.group: embeddedKafkaApplication
```

## 7. Modifying Configuration Properties During Tests

When executing test logic, you may need to temporarily change the value of a configuration property, but the configuration file cannot be modified while the unit tests are running. This can be handled with ReflectionTestUtils.

The production code has a configuration property:

``` yaml
common:
  value: origin
```

This property is referenced in MyService through the field originValue:

``` java
@Value("${common.value}")
    private String originValue;
```

When running a particular unit test, we expect to change this property to test:

``` java
ReflectionTestUtils.setField(myService, "originValue", "test");
```
