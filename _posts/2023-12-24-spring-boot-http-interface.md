---
layout: post
title:  "Spring Boot 3.2 新特性之 HTTP Interface"
date:   2023-12-24 16:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/http-interface.jpg
---

SpringBoot 3.2引入了新的 HTTP interface 用于http接口调用，采用了类似 openfeign 的风格。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-http-interface](https://github.com/qihaiyan/springcamp/tree/main/spring-http-interface)

## 一、概述

HTTP Interface 是一个类似于 openfeign 的同步接口调用方法，采用 Java interfaces 声明远程接口调用的方法，理念上类似于SpringDataRepository，可以很大程度精简代码。

要使远程调用的接口可以执行，还需要通过 HttpServiceProxyFactory 指定底层的http接口调用库，支持 RestTemplate、WebClient、RestClient三种。

## 二、引入 HTTP interface

首先引入 spring-boot-starter-web 依赖。

在 build.gradle 中增加一行代码:

``` groovy
implementation 'org.springframework.boot:spring-boot-starter-web'
```

## 三、声明接口调用 Interface

通过声明 Interface 的方式实现远程接口调用方法：

``` java
public interface MyService {
    @GetExchange("/anything")
    String getData(@RequestHeader("MY-HEADER") String headerName);

    @GetExchange("/anything/{id}")
    String getData(@PathVariable long id);

    @PostExchange("/anything")
    String saveData(@RequestBody MyData data);

    @DeleteExchange("/anything/{id}")
    ResponseEntity<Void> deleteData(@PathVariable long id);
}
```

在上述代码中，我们分别声明了包括 GET/POST/DELETE 操作的四个方法，其中第一个方法演示了如何在远程接口调用时指定header参数，只需要简单的使用 RequestHeader 注解即可。

## 四、使用声明的方法

类似于SpringDataRepository，使用 HTTP interface 也非常简单，只需要注入对应的 Bean 即可：

``` java
public class MyController {
    @Autowired
    private MyService myService;

    @GetMapping("/foo")
    public String getData() {
        return myService.getData("myHeader");
    }

    @GetMapping("/foo/{id}")
    public String getDataById(@PathVariable Long id) {
        return myService.getData(id);
    }

    @PostMapping("/foo")
    public String saveData() {
        return myService.saveData(new MyData(1L, "demo"));
    }

    @DeleteMapping("/foo")
    public ResponseEntity<Void> deleteData() {
        ResponseEntity<Void> resp = myService.deleteData(1L);
        log.info("delete {}", resp);
        return resp;
    }
}
```

便于演示方便，我们编写了自己的Controller。

在Controller中，我们注入声明好的 HTTP interface：

```java
    @Autowired
    private MyService myService;
```

当我们自己的接口被调用时，接口内部会通过注入的 MyService 声明的方法调用其它系统的接口。

```java
RestClient restClient = RestClient.builder(restTemplate).baseUrl("https://httpbin.org").build();
RestClientAdapter adapter = RestClientAdapter.create(restClient);
HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();
```

## 五、实现 HTTP interface

Spring framework 通过 HttpServiceProxyFactory 来实现 HTTP interface 方法：

``` java
@Configuration
public class MyClientConfig {
    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder.build();
    }

    @Bean
    public MyService myService(RestTemplate restTemplate) {
        restTemplate.setUriTemplateHandler(new DefaultUriBuilderFactory("https://httpbin.org"));
        RestTemplateAdapter adapter = RestTemplateAdapter.create(restTemplate);
        HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();

        return factory.createClient(MyService.class);
    }
}
```

在上述配置中，我们可以看到 MyService 这个 HTTP interface 对应的 Bean 的初始化方法。

如果想使用 Spring Boot 3.2 新出的 RestClient，那初始化代码可以改为

```java
RestClient restClient = RestClient.builder(restTemplate).baseUrl("https://httpbin.org").build();
RestClientAdapter adapter = RestClientAdapter.create(restClient);
HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();
```

## 六、单元测试

常用的单元测试方法对于 HTTP interface 仍然可用，对应的文章可以参照：[springboot单元测试技术](https://springcamp.cn/spring-boot-unit-test/)

```java
@Slf4j
@RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class DemoApplicationTest {

    @Autowired
    private TestRestTemplate testRestTemplate;
    @Autowired
    private RestTemplate restTemplate;

    private MockRestServiceServer mockRestServiceServer;

    @Before
    public void before() {
        mockRestServiceServer = MockRestServiceServer.bindTo(restTemplate).ignoreExpectOrder(true).build();
        this.mockRestServiceServer.expect(ExpectedCount.manyTimes(), MockRestRequestMatchers.requestTo(Matchers.startsWithIgnoringCase("https://httpbin.org")))
                .andExpect(method(HttpMethod.GET))
                .andRespond(MockRestResponseCreators.withSuccess("{\"get\": 200}", MediaType.APPLICATION_JSON));
        this.mockRestServiceServer.expect(ExpectedCount.manyTimes(), MockRestRequestMatchers.requestTo(Matchers.startsWithIgnoringCase("https://httpbin.org")))
                .andExpect(method(HttpMethod.POST))
                .andRespond(MockRestResponseCreators.withSuccess("{\"post\": 200}", MediaType.APPLICATION_JSON));
        this.mockRestServiceServer.expect(ExpectedCount.manyTimes(), MockRestRequestMatchers.requestTo(Matchers.startsWithIgnoringCase("https://httpbin.org")))
                .andExpect(method(HttpMethod.DELETE))
                .andRespond(MockRestResponseCreators.withSuccess("{\"delete\": 200}", MediaType.APPLICATION_JSON));
    }

    @Test
    public void testRemoteCallRest() {
        log.info("testRemoteCallRest get {}", testRestTemplate.getForObject("/foo", String.class));
        log.info("testRemoteCallRest getById {}", testRestTemplate.getForObject("/foo/1", String.class));
        log.info("testRemoteCallRest post {}", testRestTemplate.postForObject("/foo", new MyData(1L, "demo"), String.class));
        testRestTemplate.exchange("/foo", HttpMethod.DELETE, HttpEntity.EMPTY, String.class);
    }
}
```
