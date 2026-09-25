---
layout: post
title:  "Logging Request and Response Content with Spring RestTemplate"
date:   2023-05-03 16:20:00 +0800
lang: en
slug_zh: spring-rest-template-log
tags: [spring,java]
categories: [spring boot]
image: assets/images/rest-log.png
description: "How to log third-party API requests and responses in one place using a RestTemplate interceptor, keeping business code clean and log formats consistent."
---

Applications often need to call third-party APIs to implement business features. To make debugging and troubleshooting easier, we usually need to log the request parameters and the returned results to the log file. In Spring projects, RestTemplate is typically used to call third-party APIs.
Logging uniformly during RestTemplate calls keeps the code clean and the log format consistent, which is far more convenient than sprinkling API call logs throughout the business logic.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log).

## 1. Overview

Before using RestTemplate you need to define its bean, and when defining the bean you can specify ```interceptors``` to print logs.

## 2. Defining the RestTemplate Bean and Specifying Interceptors

The RestTemplate bean is defined in the RestTemplateConfig class.

RestTemplateConfig.java:

``` java
@Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder
                .requestFactory(() -> new HttpComponentsClientHttpRequestFactory(httpClient()))
                .interceptors(new CustomClientHttpRequestInterceptor())
                .build();
    }
```

The ```interceptors``` method specifies our own log-printing interceptors.

## 3. Implementing the Logging Interceptors

The custom interceptor needs to implement the ClientHttpRequestInterceptor interface.

``` java
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
```

Logging the request URL and request parameters is straightforward: simply print the arguments of the intercept method to the log.

Logging the response body requires some special handling.

With the line ```ClientHttpResponse response = execution.execute(request, bytes);``` we get the response, but the returned data cannot be read directly.

Because the ```getBody()``` method of the response returns an InputStream, reading it directly would leave subsequent processing unable to get the result.

Therefore we need to wrap the result returned by the execution.execute method and put the response into a custom BufferingClientHttpResponseWrapper class.

```ClientHttpResponse responseWrapper = new BufferingClientHttpResponseWrapper(response);```

The BufferingClientHttpResponseWrapper class copies the body data into a local variable so that the body can be read multiple times.

The BufferingClientHttpResponseWrapper class is implemented as follows:

``` java
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
        public int getRawStatusCode() throws IOException {
            return this.response.getRawStatusCode();
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
```

This class mainly gives ```getBody()``` special treatment: when the method is called, ```treamUtils.copyToByteArray``` copies the body data into a local variable.

Every subsequent read of the body comes from the local variable, avoiding the problem where the body cannot be read again after the first read.

## 4. Calling the API and Checking the Log Output

In the code we simulate calling a third-party API ```http://someservice/foo```; the call is implemented in the DemoController class:

```java
@GetMapping("/demo/get")
public Object demoGet(String arg) {
    return restTemplate.postForObject("http://someservice/foo", new BodyRequest("test"), BodyRequest.class);
}
```

The unit test code ```DemoApplicationTest``` calls this endpoint.

```java
String resp = testRestTemplate.getForObject("/demo/get?arg=test", String.class)
```

After running the unit tests, you can see the request parameters and the response printed in the log:

```
HTTP Method: POST, URI: http://someservice/foo, Headers: [Accept:"application/json, application/*+json", Content-Type:"application/json", Content-Length:"15"]
HTTP body: {"arg1":"test"}
RESPONSE body: {"code": 200}
```

The response ```{"code": 200}``` printed in the log is the data we mocked for the ```http://someservice/foo``` API in the unit test.

For details on how to mock a third-party API, see the article [Spring Boot unit testing](https://springcamp.cn/spring-boot-unit-test/).
