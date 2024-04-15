---
layout: post
title:  "Spring Boot 3.2 新特性之 RestClient"
date:   2023-12-03 16:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/rest-client.jpg
---

SpringBoot 3.2引入了新的 RestClient 用于http接口调用，采用了 fluent API 的风格，可以进行链式调用。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-data-jdbc-client](https://github.com/qihaiyan/springcamp/tree/master/spring-data-jdbc-client)

## 一、概述

RestClient 是一个类似于 RestTemplate 的的同步接口调用工具。相比于 RestTemplate 采用的是 template 设计模式，RestClient 采用了 fluent API 风格，简单灵活，易于阅读和维护。

## 二、引入 RestClient

首先引入 spring-boot-starter-web 依赖。

在 build.gradle 中增加一行代码:

``` groovy
implementation 'org.springframework.boot:spring-boot-starter-web'
```

对 RestClient 进行配置：

``` java
@Configuration
public class RestClientConfig {
    public CloseableHttpClient httpClient() {
        Registry<ConnectionSocketFactory> registry =
                RegistryBuilder.<ConnectionSocketFactory>create()
                        .register("http", PlainConnectionSocketFactory.getSocketFactory())
                        .register("https", SSLConnectionSocketFactory.getSocketFactory())
                        .build();
        PoolingHttpClientConnectionManager poolingConnectionManager = new PoolingHttpClientConnectionManager(registry);

        poolingConnectionManager.setDefaultSocketConfig(SocketConfig.custom().setSoTimeout(Timeout.ofSeconds(2)).build());
        poolingConnectionManager.setDefaultConnectionConfig(ConnectionConfig.custom().setConnectTimeout(Timeout.ofSeconds(2)).build());

        // set total amount of connections across all HTTP routes
        poolingConnectionManager.setMaxTotal(200);
        // set maximum amount of connections for each http route in pool
        poolingConnectionManager.setDefaultMaxPerRoute(200);

        RequestConfig requestConfig = RequestConfig.custom()
                .setConnectionKeepAlive(TimeValue.ofSeconds(10))
                .setConnectionRequestTimeout(Timeout.ofSeconds(2))
                .setResponseTimeout(Timeout.ofSeconds(2))
                .build();

        return HttpClients.custom()
                .setDefaultRequestConfig(requestConfig)
                .setConnectionManager(poolingConnectionManager)
                .setKeepAliveStrategy(new DefaultConnectionKeepAliveStrategy())
                .build();
    }

    @Slf4j
    static class CustomClientHttpRequestInterceptor implements ClientHttpRequestInterceptor {
        @Override
        @NonNull
        public ClientHttpResponse intercept(HttpRequest request, @NonNull byte[] bytes, @NonNull ClientHttpRequestExecution execution) throws IOException {
            log.info("HTTP Method: {}, URI: {}, Headers: {}", request.getMethod(), request.getURI(), request.getHeaders());
            request.getMethod();
            if (request.getMethod().equals(HttpMethod.POST)) {
                log.info("HTTP body: {}", new String(bytes, StandardCharsets.UTF_8));
            }

            ClientHttpResponse response = execution.execute(request, bytes);
            ClientHttpResponse responseWrapper = new BufferingClientHttpResponseWrapper(response);

            String body = StreamUtils.copyToString(responseWrapper.getBody(), StandardCharsets.UTF_8);
            log.info("RESPONSE body: {}", body);

            return responseWrapper;
        }
    }

    static class BufferingClientHttpResponseWrapper implements ClientHttpResponse {

        private final ClientHttpResponse response;
        private byte[] body;

        BufferingClientHttpResponseWrapper(ClientHttpResponse response) {
            this.response = response;
        }

        @NonNull
        public HttpStatusCode getStatusCode() throws IOException {
            return this.response.getStatusCode();
        }

        @NonNull
        public String getStatusText() throws IOException {
            return this.response.getStatusText();
        }

        @NonNull
        public HttpHeaders getHeaders() {
            return this.response.getHeaders();
        }

        @NonNull
        public InputStream getBody() throws IOException {
            if (this.body == null) {
                this.body = StreamUtils.copyToByteArray(this.response.getBody());
            }
            return new ByteArrayInputStream(this.body);
        }

        public void close() {
            this.response.close();
        }
    }

    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder
                .requestFactory(() -> new HttpComponentsClientHttpRequestFactory(httpClient()))
                .interceptors(new CustomClientHttpRequestInterceptor())
                .build();
    }

    @Bean
    public RestClient restClient(RestTemplate restTemplate) {
        return RestClient.builder(restTemplate).requestFactory(new HttpComponentsClientHttpRequestFactory(httpClient())).build();
    }
}
```

在配置中我们仍然定义了 RestTemplate ，并使用 RestTemplate 来初始化 RestClient 为的是继续使用 RestTemplate 的日志打印功能 [参照 https://github.com/qihaiyan/springcamp/tree/master/spring-rest-template-log](https://github.com/qihaiyan/springcamp/tree/master/spring-rest-template-log)

如果不想继续使用RestTemplate，那初始化代码可以改为

```java
RestClient.builder().requestFactory(new HttpComponentsClientHttpRequestFactory(httpClient())).build();
```

同时我们给 RestClient 配置了 requestFactory ，可以使用长连接调用接口。

## 三、GET接口调用

调用GET接口返回字符串：

``` java
restClient.get()
                .uri("https://httpbin.org/get")
                .retrieve()
                .body(String.class)
```

调用GET接口对象：

``` java
restClient.get()
                .uri("https://httpbin.org/get")
                .retrieve()
                .body(MyData.class);
```

调用GET接口返回List：

``` java
List<String> list = restClient.get()
                .uri("http://someservice/list")
                .retrieve()
                .body(new ParameterizedTypeReference<>() {});
```

## 四、POST接口调用

```java
MyData postBody = new MyData("test", "test RestClient");
        ResponseEntity<String> respObj = restClient.post()
                .uri("https://httpbin.org/post")
                .contentType(MediaType.APPLICATION_JSON)
                .body(postBody)
                .retrieve()
                .toEntity(String.class);
```

## 五、Exchange接口调用

当需要对接口返回结果进行更加精确的控制时，可以采用 Exchange 方法。
例如当接口返回 4xx 时，让 restClient 返回空字符串，否则返回正常结果：

```java
restClient.get()
                .uri("https://httpbin.org/get")
                .accept(MediaType.APPLICATION_JSON)
                .exchange((request, response) -> {
                    if (response.getStatusCode().is4xxClientError()) {
                        log.info("status 4xx");
                        return "";
                    } else {
                        log.info("response: {}", response);
                        return response;
                    }
                });
```

## 六、错误处理

当接口返回错误时，可以在 onStatus 方法中进行判断并进行对应的操作：

```java
restClient.get()
                .uri("https://httpbin.org/status/404")
                .retrieve()
                .onStatus(status -> status.value() == 404, (request, response) -> {
                    log.info("status 404");
                })
                .toBodilessEntity();
```

toBodilessEntity 方法是一种忽略接口返回结果的方法，当不需要读取接口返回结果时，可以使用 toBodilessEntity 方法。
