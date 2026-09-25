---
layout: post
title:  "Modifying RequestBody Globally in Spring"
date:   2024-07-06 15:30:00 +0800
lang: en
slug_zh: spring-controller-modify-request-body
tags: [spring,java]
categories: [spring boot]
image: assets/images/rest-controller-advice.png
description: "How to modify RestController request bodies uniformly with RequestBodyAdviceAdapter, for example assigning a header value to a RequestBody field automatically."
---

When writing RestControllers, several endpoints may share the same RequestBody, and in some scenarios we need to modify the incoming RequestBody values. Modifying it in every controller is cumbersome; the best approach is to modify it in one place, for example assigning a value from a header to a property of the RequestBody object. The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-modify-request-body](https://github.com/qihaiyan/springcamp/tree/main/spring-modify-request-body)

## 1. Overview

In spring, RequestBodyAdviceAdapter can be used to modify the request parameters of a RestController.

## 2. Custom RequestBodyAdviceAdapter

The following code is a custom ModifyBodyAdvice that extends RequestBodyAdviceAdapter

``` java
@ControllerAdvice
public class ModifyBodyAdvice extends RequestBodyAdviceAdapter {
    @Autowired
    HttpServletRequest httpServletRequest;

    @Override
    @NonNull
    public Object afterBodyRead(@NonNull Object body, @NonNull HttpInputMessage inputMessage,
                                @NonNull MethodParameter parameter, @NonNull Type targetType,
                                @NonNull Class<? extends HttpMessageConverter<?>> converterType) {
        String requestMethod = httpServletRequest.getMethod();
        String fieldName = "foo";

        if (StringUtils.startsWithIgnoreCase(requestMethod, HttpMethod.PUT.name())
                || StringUtils.startsWithIgnoreCase(requestMethod, HttpMethod.POST.name())
        ) {
            Field field = ReflectionUtils.findField(body.getClass(), fieldName);
            if (field != null) {
                ReflectionUtils.makeAccessible(field);
                String paramValue = Optional.ofNullable(httpServletRequest.getHeader(fieldName)).orElse("");
                Method method = ReflectionUtils.findMethod(body.getClass(), "set" +
                        StringUtils.capitalize(fieldName), field.getType());
                if (method != null) {
                    ReflectionUtils.invokeMethod(method, body, paramValue);
                }
            }
        }
        return super.afterBodyRead(body, inputMessage, parameter, targetType, converterType);

    }

    @Override
    public boolean supports(@NonNull MethodParameter methodParameter,
                            @NonNull Type targetType,
                            @NonNull Class<? extends HttpMessageConverter<?>> converterType) {
        return true;
    }
}
```

To make the process easy to demonstrate, the property to modify on the request object is hard-coded as foo in the code: we read the value of the foo header from the request headers and assign it to the foo property of the request object via reflection.

## 3. Verifying the Unified Modification Logic

We verify that the RequestBody values are modified correctly by writing unit tests.
The DemoApplicationTest unit test calls the endpoint and verifies the returned result.

```java
   @Test
    public void test() {
        ReqBody reqBody = new ReqBody();
        ResponseEntity<ReqBody> resp = testRestTemplate.exchange(RequestEntity.post("/test").header("foo", "test").body(reqBody), ReqBody.class);
        log.info("result : {}", resp);
        assertThat(resp.getBody().getFoo(), is("test"));
    }
```

When we call the controller, the RequestBody we pass in is an object of ReqBody with none of its properties set, and the request sends a foo header. According to the processing logic, the foo value of the ReqBody object received in the controller should be the header value.
