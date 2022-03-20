---
layout: post
title:  "springboot单元测试技术"
date:   2021-04-18 17:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/ut.jpg
---

整个软件交付过程中，单元测试阶段是一个能够最早发现问题，并且可以重复回归问题的阶段，在单元测试阶段做的测试越充分，软件质量就越能得到保证。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-unit-test](https://github.com/qihaiyan/springcamp/tree/master/spring-unit-test)

## 一、概述

一个功能的全链路测试，往往要依赖于很多外部组件，如数据库、redis、kafka、第三方接口等，单元测试的执行环境有可能受网络限制没有办法访问这些外部服务。因此，我们希望通过一些技术手段，能够用单元测试技术进行完整的功能测试，而不依赖于外部服务。

## 二、REST接口的测试

springboot提供了testRestTemplate工具用于在单元测试中测试接口，该工具只需指定接口的相对路径，不需要指定域名和端口。这个特性非常有用，因为springboot的单元测试运行环境的web服务是一个随机端口，是通过下面这个注解指定的：

``` java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
```

以下是通过testRestTemplate测试我们开发的```/remote```接口的方法：

``` java
    @Test
    public void testRemoteCallRest() {
        String resp = testRestTemplate.getForObject("/remote", String.class);
        System.out.println("remote result : " + resp);
        assertThat(resp, is("{\"code\": 200}"));
    }
```

## 三、第三方接口的依赖

上面的例子中，我们的remote接口会调用一个第三方接口 ```http://someservice/foo```，我们的构建服务器中有可能受网络限制，无法访问这个第三方接口，就会导致单元测试无法执行。我们可以通过springboot提供的 ```MockRestServiceServer``` 工具来解决这个问题。

首先定义一个MockRestServiceServer变量

``` java
private MockRestServiceServer mockRestServiceServer;
```

在单元测试的初始化阶段进行初始化

``` java
    @Before
    public void before() {
        mockRestServiceServer = MockRestServiceServer.bindTo(restTemplate).ignoreExpectOrder(true).build();

        this.mockRestServiceServer.expect(manyTimes(), MockRestRequestMatchers.requestTo(Matchers.startsWithIgnoringCase("http://someservice/foo")))
                .andRespond(withSuccess("{\"code\": 200}", MediaType.APPLICATION_JSON));

    }
```

这样，当我们的单元测试程序中调用```http://someservice/foo```接口时，就会固定返回```{"code": 200}```这个返回值，而不是真正的去访问这个第三方接口。

## 四、数据库的依赖

数据库的依赖比较简单，直接使用h2这个嵌入式数据库就可以，所有的数据库操作都是在h2这个嵌入式数据库中执行的。

已gradle配置为例：

``` groovy
testImplementation 'com.h2database:h2'
```

单元测试配置文件中的数据库连接使用h2:

``` yaml
spring:
  data:
    url: jdbc:h2:mem:ut;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
    username: sa
    password:
```

单元测试程序中可以直接进行数据库操作：

``` java
MyDomain myDomain = new MyDomain();
myDomain.setName("test");
myDomain = myDomainRepository.save(myDomain);
```

当我们调用接口查询数据库中的记录时，能够正确查询到结果：

``` java
MyDomain resp = testRestTemplate.getForObject("/db?id=" + myDomain.getId(), MyDomain.class);
System.out.println("db result : " + resp);
assertThat(resp.getName(), is("test"));
```

当接口返回Page分页数据时，需要做一点特殊处理，否则会报json序列化错误。

定义自己的Page类：

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

调用接口返回自定义的Page类：

``` java
RequestEntity<Void> requestEntity = RequestEntity.get("/dbpage").build();
ResponseEntity<TestRestResponsePage<MyDomain>> pageResp = testRestTemplate.exchange(requestEntity, new ParameterizedTypeReference<TestRestResponsePage<MyDomain>>() {
    });
System.out.println("dbpage result : " + pageResp);
assertThat(pageResp.getBody().getTotalElements(), is(1L));
```

由于返回结果是泛型，所以需要使用```testRestTemplate.exchange```方法，get方法不支持返回泛型。

## 五、redis的依赖

网上有一个开源的redis mockserver，模仿了大部分的redis指令，我们只需要引入这个redis-mockserver即可。
最初版本是一个国人开发的，示例中引入的是老外fork的一个版本，补充了一些指令，但是找不到源码了，我又fork了一个版本，补充了setex、zscore两个指令，有需要的可以自己编译。[代码连接 https://github.com/qihaiyan/redis-mock](https://github.com/qihaiyan/redis-mock)

已gradle配置为例：

``` groovy
testImplementation 'com.github.fppt:jedis-mock:1.0.1'
```

单元测试配置文件中的数据库连接使用redis mockserver:

``` yaml
spring:
  redis:
    port: 10033
```

增加一个单独的redis配置文件，用于在单元测试中启动redis mockserver：

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

## 六、kafka的依赖

spring提供了一个kafka的测试组件，可以在单元测试期间启动一个嵌入式的kafka服务EmbeddedKafka，模拟真实的kafka操作。

已gradle配置为例：

``` groovy
testImplementation "org.springframework.kafka:spring-kafka-test"
```

通过ClassRule初始化EmbeddedKafka，有两个topic: testEmbeddedIn 和 testEmbeddedOut 。

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

在单元测试程序的配置文件中，可以指定这2个kafka的topic

``` yaml
cloud.stream.bindings:
    handle-out-0.destination: testEmbeddedOut
    handle-in-0.destination: testEmbeddedIn
    handle-in-0.group: embeddedKafkaApplication
```
