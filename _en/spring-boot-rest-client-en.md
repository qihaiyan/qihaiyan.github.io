---
layout: post
title:  "Spring Boot 3.2 New Feature: RestClient"
date:   2023-12-03 16:20:00 +0800
lang: en
slug_zh: spring-boot-rest-client
tags: [spring,java]
categories: [spring boot]
image: assets/images/rest-client.jpg
description: "RestClient in Spring Boot 3.2 is a fluent, chainable alternative to RestTemplate for HTTP calls: GET/POST requests, the exchange method, and error handling."
---

Spring Boot 3.2 introduces the new RestClient for calling HTTP APIs, with a fluent API style that supports chained calls.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-data-jdbc-client](https://github.com/qihaiyan/springcamp/tree/main/spring-data-jdbc-client).

## 1. Overview

RestClient is a synchronous API-calling tool similar to RestTemplate. While RestTemplate follows the template design pattern, RestClient adopts a fluent API style — simple, flexible, easy to read and maintain.

## 2. Adding RestClient

First add the spring-boot-starter-web dependency.

Add one line to build.gradle:

``` groovy
implementation 'org.springframework.boot:spring-boot-starter-web'
```

Configuring RestClient:

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

In the configuration we still define a RestTemplate and use it to initialize the RestClient, so that we can keep RestTemplate's log-printing feature (see [https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log))

If you don't want to keep using RestTemplate, the initialization code can be changed to

```java
RestClient.builder().requestFactory(new HttpComponentsClientHttpRequestFactory(httpClient())).build();
```

We also configure a requestFactory for the RestClient, so it can call APIs over persistent connections.

## 3. Calling GET APIs

Calling a GET API and returning a String:

``` java
restClient.get()
                .uri("https://httpbin.org/get")
                .retrieve()
                .body(String.class)
```

Calling a GET API and returning an object:

``` java
restClient.get()
                .uri("https://httpbin.org/get")
                .retrieve()
                .body(MyData.class);
```

Calling a GET API and returning a List:

``` java
List<String> list = restClient.get()
                .uri("http://someservice/list")
                .retrieve()
                .body(new ParameterizedTypeReference<>() {});
```

## 4. Calling POST APIs

```java
MyData postBody = new MyData("test", "test RestClient");
        ResponseEntity<String> respObj = restClient.post()
                .uri("https://httpbin.org/post")
                .contentType(MediaType.APPLICATION_JSON)
                .body(postBody)
                .retrieve()
                .toEntity(String.class);
```

## 5. Calling APIs with Exchange

When you need finer-grained control over the API response, you can use the exchange method.
For example, have the restClient return an empty string when the API responds with 4xx, and the normal result otherwise:

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

## 6. Error Handling

When the API returns an error, you can check for it in the onStatus method and act accordingly:

```java
restClient.get()
                .uri("https://httpbin.org/status/404")
                .retrieve()
                .onStatus(status -> status.value() == 404, (request, response) -> {
                    log.info("status 404");
                })
                .toBodilessEntity();
```

The toBodilessEntity method is a way of ignoring the API response; use it when you don't need to read the API response result.
