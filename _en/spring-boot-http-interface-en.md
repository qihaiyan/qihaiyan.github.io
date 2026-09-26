---
layout: post
title:  "Spring Boot 3.2 New Feature: HTTP Interface"
date:   2023-12-24 16:20:00 +0800
lang: en
slug_zh: spring-boot-http-interface
tags: [spring,java,featured]
categories: [spring boot]
image: assets/images/http-interface.jpg
description: "Declare remote HTTP calls as Java interfaces in Spring Boot 3.2, OpenFeign style, backed by HttpServiceProxyFactory and RestTemplate, RestClient, or WebClient."
---

Spring Boot 3.2 introduces the new HTTP interface for calling HTTP APIs, in a style similar to openfeign.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-http-interface](https://github.com/qihaiyan/springcamp/tree/main/spring-http-interface).

## 1. Overview

The HTTP interface is a synchronous way of calling remote APIs, similar to openfeign. Remote API calls are declared as Java interfaces, conceptually like SpringDataRepository, which can greatly reduce boilerplate code.

To make the declared interfaces executable, you also need to specify the underlying HTTP client library via HttpServiceProxyFactory; RestTemplate, WebClient, and RestClient are the three options supported.

## 2. Adding the HTTP interface

First add the spring-boot-starter-web dependency.

Add one line to build.gradle:

``` groovy
implementation 'org.springframework.boot:spring-boot-starter-web'
```

## 3. Declaring the Interface

Remote API call methods are implemented by declaring an interface:

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

In the code above we declare four methods covering GET/POST/DELETE operations. The first method shows how to pass a header parameter in a remote API call — simply use the RequestHeader annotation.

## 4. Using the Declared Methods

Like SpringDataRepository, the HTTP interface is very easy to use — just inject the corresponding bean:

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

For demonstration purposes we wrote our own controller.

In the controller, we inject the declared HTTP interface:

```java
    @Autowired
    private MyService myService;
```

When our own endpoint is called, it internally uses the methods declared by the injected MyService to call other systems' APIs.

```java
RestClient restClient = RestClient.builder(restTemplate).baseUrl("https://httpbin.org").build();
RestClientAdapter adapter = RestClientAdapter.create(restClient);
HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();
```

## 5. Implementing the HTTP interface

Spring framework implements the HTTP interface methods through HttpServiceProxyFactory:

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

In the configuration above we can see how the bean for the MyService HTTP interface is initialized.

If you want to use the new RestClient from Spring Boot 3.2, the initialization code can be changed to

```java
RestClient restClient = RestClient.builder(restTemplate).baseUrl("https://httpbin.org").build();
RestClientAdapter adapter = RestClientAdapter.create(restClient);
HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();
```

## 6. Unit Testing

The usual unit testing techniques still apply to the HTTP interface; see the article: [Spring Boot unit testing](https://springcamp.cn/spring-boot-unit-test/)

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
