---
layout: post
title:  "spring打印http接口请求和响应"
date:   2020-11-22 11:50:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/log.png
---

在程序日志中打印出接口请求和响应的内容是一个基本的技术需求。如果在每个接口中实现请求响应的日志打印，程序编写会很繁琐，我们可以利用spring提供的机制，集中处理接口请求响应的日志打印。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-rest-log-request-response](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-log-request-response)

## 一、概述

基于spring提供的机制，有3种方法可以实现接口请求响应日志的打印，分别是CommonsRequestLoggingFilter、HandlerInterceptor、RequestBodyAdviceAdapter。

<!-- more -->

## 二、修改日志级别打印请求参数

通过设置 web 的日志级别为 DEBUG，spring会自己打印请求参数。该方法打印的内容覆盖了后面介绍的所有方法中日志的内容，如果不需要做定制打印，并且不介意打印的日志级别是DEBUG，那就足够用了。

``` yml
logging:
  level:
    root: INFO
    web: DEBUG
```

## 三、使用 CommonsRequestLoggingFilter 打印请求参数

CommonsRequestLoggingFilter的使用比较简单，只需要实现一个logFilter的bean即可。
只不过logFilter的日志级别是debug，需要在日志配置文件中，将CommonsRequestLoggingFilter类的日志级别设置为debug级别。
同时在生产环境的日志文件中打印debug日志不符合规范。

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

## 四、使用 HandlerInterceptor 打印请求参数

HandlerInterceptor 可以获取到接口执行过程中的 HttpServletRequest 和 HttpServletResponse 信息，因此能够打印出接口请求响应内容。

```java
@Component
public class LogInterceptorAdapter extends HandlerInterceptorAdapter {

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) {

        ServletRequest servletRequest = new ContentCachingRequestWrapper(request);
        Map<String, String[]> params = servletRequest.getParameterMap();

        // 从 request 中读取请求参数并打印
        params.forEach((key, value) -> log.info("logInterceptor " + key + "=" + Arrays.toString(value)));
        // 避免从 inputStream 中读取body并打印

        return true;
    }
}
```

这种方式有个缺陷，对于 application/json 这种请求参数放在body中的方式，需要通过InputStream读取内容，而InputStream只能被读取一次，
一旦在 HandlerInterceptor 中进行了 InputStream 的读取操作，后续的处理就读取不到InputStream中的内容，这是一个很严重的问题。
因此 HandlerInterceptor 不能用于打印请求中的body，可以改造一下该方法，只打印get请求参数，post的请求参数用下面介绍的 RequestBodyAdviceAdapter 方法打印。

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

            // 从 request 中读取请求参数并打印
            params.forEach((key, value) -> log.info("logInterceptor " + key + "=" + Arrays.toString(value)));
            // 避免从 inputStream 中读取body并打印

        }
        return true;
    }
}
```

## 五、使用 RequestBodyAdviceAdapter 打印请求参数

RequestBodyAdviceAdapter 封装了 afterBodyRead 方法，在这个方法中可以通过 Object body 参数获取到body的内容。

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

        // 打印body内容

        return super.afterBodyRead(body, inputMessage, parameter, targetType, converterType);
    }
}
```

## 六、使用 ResponseBodyAdvice 打印响应内容

ResponseBodyAdvice 和 RequestBodyAdviceAdapter 同属于 ControllerAdvice。ResponseBodyAdvice 封装了 beforeBodyWrite 方法，可以获取到响应报文。

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
            // 打印响应body
        }

        return body;
    }
}
```

## 七、使用 filter 打印请求和响应

通过继承spring的 ```OncePerRequestFilter``` 实现自定义filter。在filter中读取请求和响应的body需要做一下特殊处理，因为流只能被读取一次，在filter中被读取了，后续的处理就无法再次读取流的内容了。

spring提供了 ```ContentCachingRequestWrapper``` 和 ```ContentCachingResponseWrapper``` 两个类来解决这个问题。

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
