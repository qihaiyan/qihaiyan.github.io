---
layout: post
title:  "Logging HTTP Requests and Responses in Spring"
date:   2020-11-22 11:50:00 +0800
lang: en
slug_zh: spring-rest-log-request-response
tags: [spring,java]
categories: [spring boot]
image: assets/images/log.png
description: "Three ways to centrally log REST request and response in Spring: CommonsRequestLoggingFilter, HandlerInterceptor, and RequestBodyAdviceAdapter, compared."
---

Logging the content of API requests and responses is a basic technical requirement. Implementing request and response logging in every endpoint would be very tedious. Instead, we can use the mechanisms provided by Spring to handle request and response logging centrally.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-rest-log-request-response](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-log-request-response).

## 1. Overview

Based on the mechanisms provided by Spring, there are 3 ways to log API requests and responses: CommonsRequestLoggingFilter, HandlerInterceptor, and RequestBodyAdviceAdapter.

<!-- more -->

## 2. Logging Request Parameters by Changing the Log Level

By setting the web log level to DEBUG, Spring prints the request parameters by itself. The output of this approach covers everything logged by all the methods described below. If you don't need customized output and don't mind the log level being DEBUG, this is good enough.

``` yml
logging:
  level:
    root: INFO
    web: DEBUG
```

## 3. Logging Request Parameters with CommonsRequestLoggingFilter

CommonsRequestLoggingFilter is fairly simple to use: you only need to declare a logFilter bean.
The catch is that logFilter logs at the debug level, so in the logging configuration you need to set the log level of the CommonsRequestLoggingFilter class to debug.
Also, printing debug logs to the log file in a production environment is not considered good practice.

``` java
@Bean
public CommonsRequestLoggingFilter logFilter() {
    CommonsRequestLoggingFilter loggingFilter = new CommonsRequestLoggingFilter();

    loggingFilter.setIncludeQueryString(true);
    loggingFilter.setIncludePayload(true);
    loggingFilter.setMaxPayloadLength(2048);

    return loggingFilter;
}
```

## 4. Logging Request Parameters with HandlerInterceptor

HandlerInterceptor can access the HttpServletRequest and HttpServletResponse during request processing, so it can print the request and response content.

```java
@Component
public class LogInterceptorAdapter extends HandlerInterceptorAdapter {

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) {

        ServletRequest servletRequest = new ContentCachingRequestWrapper(request);
        Map<String, String[]> params = servletRequest.getParameterMap();

        // Read the request parameters from the request and log them
        params.forEach((key, value) -> log.info("logInterceptor " + key + "=" + Arrays.toString(value)));
        // Avoid reading the body from the inputStream and logging it

        return true;
    }
}
```

This approach has a flaw: for requests such as application/json, where the request parameters are placed in the body, the content has to be read through the InputStream, and an InputStream can only be read once.
Once the InputStream has been read in a HandlerInterceptor, the subsequent processing can no longer read the content of the InputStream, which is a serious problem.
Therefore HandlerInterceptor cannot be used to print the request body. The method can be adapted to print only GET request parameters, while the POST request parameters are logged with the RequestBodyAdviceAdapter method described below.

```java
@Slf4j
@Component
public class LogInterceptorAdapter extends HandlerInterceptorAdapter {

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) {
        if (DispatcherType.REQUEST.name().equals(request.getDispatcherType().name())
                && request.getMethod().equals(HttpMethod.GET.name())) {

            ServletRequest servletRequest = new ContentCachingRequestWrapper(request);
            Map<String, String[]> params = servletRequest.getParameterMap();

            // Read the request parameters from the request and log them
            params.forEach((key, value) -> log.info("logInterceptor " + key + "=" + Arrays.toString(value)));
            // Avoid reading the body from the inputStream and logging it

        }
        return true;
    }
}
```

## 5. Logging Request Parameters with RequestBodyAdviceAdapter

RequestBodyAdviceAdapter wraps the afterBodyRead method, where the body content can be obtained through the Object body parameter.

```java
@ControllerAdvice
public class CustomRequestBodyAdviceAdapter extends RequestBodyAdviceAdapter {

    @Autowired
    HttpServletRequest httpServletRequest;

    @Override
    public boolean supports(MethodParameter methodParameter, Type type,
                            Class<? extends HttpMessageConverter<?>> aClass) {
        return true;
    }

    @Override
    public Object afterBodyRead(Object body, HttpInputMessage inputMessage,
                                MethodParameter parameter, Type targetType,
            Class<? extends HttpMessageConverter<?>> converterType) {

        // Log the body content

        return super.afterBodyRead(body, inputMessage, parameter, targetType, converterType);
    }
}
```

## 6. Logging Response Content with ResponseBodyAdvice

ResponseBodyAdvice and RequestBodyAdviceAdapter both belong to ControllerAdvice. ResponseBodyAdvice wraps the beforeBodyWrite method, where the response message can be obtained.

```java
@ControllerAdvice
public class CustomResponseBodyAdviceAdapter implements ResponseBodyAdvice<Object> {

    @Override
    public boolean supports(MethodParameter methodParameter,
                            Class<? extends HttpMessageConverter<?>> aClass) {
        return true;
    }

    @Override
    public Object beforeBodyWrite(Object body,
                                  MethodParameter methodParameter,
                                  MediaType mediaType,
                                  Class<? extends HttpMessageConverter<?>> aClass,
                                  ServerHttpRequest serverHttpRequest,
                                  ServerHttpResponse serverHttpResponse) {

        if (serverHttpRequest instanceof ServletServerHttpRequest &&
                serverHttpResponse instanceof ServletServerHttpResponse) {
            // Log the response body
        }

        return body;
    }
}
```

## 7. Logging Request and Response with a Filter

Implement a custom filter by extending Spring's ```OncePerRequestFilter```. Reading the request and response bodies in a filter requires special handling, because a stream can only be read once: once it is read in the filter, the subsequent processing cannot read the stream content again.

Spring provides two classes, ```ContentCachingRequestWrapper``` and ```ContentCachingResponseWrapper```, to solve this problem.

```java
@Slf4j
@Component
public class AccessLogFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        ContentCachingRequestWrapper req = new ContentCachingRequestWrapper(request);
        ContentCachingResponseWrapper resp = new ContentCachingResponseWrapper(response);

        try {
            // Execution request chain
            filterChain.doFilter(req, resp);
            // Get body
            byte[] requestBody = req.getContentAsByteArray();
            byte[] responseBody = resp.getContentAsByteArray();

            log.info("request body = {}", new String(requestBody, StandardCharsets.UTF_8));
            log.info("response body = {}", new String(responseBody, StandardCharsets.UTF_8));
        } finally {
        // Finally remember to respond to the client with the cached data.
            resp.copyBodyToResponse();
        }
    }
}
```
