---
layout: post
title:  "Spring统一修改RequestBody"
date:   2024-07-06 15:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/rest-controller-advice.png
---

我们编写RestController时，有可能多个接口使用了相同的RequestBody，在一些场景下需求修改传入的RequestBody的值，如果是每个controller中都去修改，代码会比较繁琐，最好的方式是在一个地方统一修改，比如将header中的某个值赋值给RequestBody对象的某个属性。 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-modify-request-body](https://github.com/qihaiyan/springcamp/tree/master/spring-modify-request-body)

## 一、概述

在spring中可以使用RequestBodyAdviceAdapter修改RestController的请求参数。

## 二、自定义 RequestBodyAdviceAdapter

以下代码为自定义 ModifyBodyAdvice 实现 RequestBodyAdviceAdapter

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

便于演示处理过程，我们在代码中写死了要修改的请求对象的属性为 foo ，从请求header中获取foo这个header的值，然后通过反射赋值到请求对象的foo属性。

## 三、验证统一修改逻辑

我们通过编写单元测试的方式验证RequestBody的值是否能够正常修改。
在DemoApplicationTest这个单元测试程序中进行接口调用，并验证返回结果。

```java
   @Test
    public void test() {
        ReqBody reqBody = new ReqBody();
        ResponseEntity<ReqBody> resp = testRestTemplate.exchange(RequestEntity.post("/test").header("foo", "test").body(reqBody), ReqBody.class);
        log.info("result : {}", resp);
        assertThat(resp.getBody().getFoo(), is("test"));
    }
```

我们调用controller时传入了的RequestBody为 ReqBody的一个对象，这个对象没有对属性进行赋值，在请求header中发送了foo这个header，按照处理逻辑，controller中接收到的ReqBody对象的foo的值应该是header的值。
