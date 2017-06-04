---
layout: post
title:  "SpringBoot框架中REST接口的异常处理方法"
date:   2017-05-21 18:28:00 +0800
tags: [spring-boot]
categories: [spring-boot]
---
# 一. HTTP状态码
1. 100 到199 的状态码代表信息，描述对于请求的处理。
2. 200 到 299 的状态码表示客户端发来的请求已经被接收并正确处理。
3. 300 到 399 的状态码表示客户端需要进一步的处理才能完成请求，比如重定向到另一个地址。
4. 400 到 499 的状态码表示客户端的请求有错误，需要修正。404就是这种情况。
5. 500 到 599 的状态码表示服务器在处理客户端请求时发生了内部错误。

在SpringBoot中，如果接口中有未处理的异常，会返回500，表示内部服务器错误。简单来说，如果后台程序没有对异常做特殊处理，只要有异常抛出，客户端收到的状态码就是500。

# 二. 在异常类中定义状态码
我们可以通过使用@ResponseStatus注解在异常类中定义返回的状态码。

<!-- more -->

例如：

这是一个用户自定义异常类
```java
@ResponseStatus(value=HttpStatus.NOT_FOUND, reason="No such Order")  // 404
 public class OrderNotFoundException extends RuntimeException {
     // ...
 }
```
在一个接口中抛出这个异常类
```java
@RequestMapping(value="/orders/{id}", method=GET)
 public Order showOrder(@PathVariable("id") long id, Model model) {
     Order order = orderRepository.findOrderById(id);
     if (order == null) throw new OrderNotFoundException(id);
     return order;
 }
```
当这个接口中没有找到指定的order id时，就会返回404。原因是该接口抛出了OrderNotFoundException异常，而这个异常中@ResponseStatus注解指定了返回码是HttpStatus.NOT_FOUND，也就是400。

# 三. 在接口中进行异常处理
可以在接口类中定义带有@ExceptionHandler注解的方法，来处理该类中所有接口的异常。

首先定义一个类用于返回详细的错误信息：
```java
public class RestServiceError {

    private String code;
    private String message;

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public static RestServiceError build (Type errorType, String message) {
        RestServiceError error = new RestServiceError();
        error.code = errorType.getCode();
        error.message = message;
        return error;
    }

    public enum Type {
        BAD_REQUEST_ERROR("error.badrequest", "Bad request error"),
        INTERNAL_SERVER_ERROR("error.internalserver", "Unexpected server error"),
        VALIDATION_ERROR("error.validation", "Found validation issues");

        private String code;
        private String message;

        Type(String code, String message) {
            this.code = code;
            this.message = message;
        }

        public String getCode() {
            return code;
        }

        public String getMessage() {
            return message;
        }
    }
}
```
定义一个带有异常处理方法的REST接口类：
```java
@RestController
public class ControllerWithExceptionHandling {

  // @RequestMapping 方法
  ...
  
  // 异常处理方法：
  // 根据特定的异常返回指定的 HTTP 状态码
  @ResponseStatus(value=HttpStatus.BAD_REQUEST)  // 400
  @ExceptionHandler(ConstraintViolationException.class)
  @ResponseBody
  public RestServiceError handleValidationException(ConstraintViolationException ex) {
        Set<ConstraintViolation<?>> errors = ex.getConstraintViolations();
        StringBuilder strBuilder = new StringBuilder();
        for (ConstraintViolation<?> violation : errors) {
            strBuilder.append(violation.getMessage() + "\n");
        }
        return RestServiceError.build(RestServiceError.Type.VALIDATION_ERROR, strBuilder.toString());
  }
  
  // 通用异常的处理，返回500
  @ResponseStatus(value=HttpStatus.INTERNAL_SERVER_ERROR)  // 500
  @ExceptionHandler(Exception.class)
  @ResponseBody
  public RestServiceError handleException(Exception ex) {
        return RestServiceError.build(RestServiceError.Type.INTERNAL_SERVER_ERROR, ex.getMessage());
  }
}
```
这样，该类中的所有接口如果有异常发生，就会返回对应的 HTTP 状态码，并且在返回的报文体中包含错误描述信息。

如果接口抛出的异常是ConstraintViolationException，就是返回handleValidationException方法中指定的状态码和错误信息，否则返回handleException方法中指定的状态码和错误信息。可以通过增加异常处理方法来处理更多特定的异常。

错误信息结构如下：
```json
{"code":"error.internalserver","message":"内部服务器错误"}
```
# 四. 全局异常处理
上述的方法中是处理特定接口类的异常，需要在每个接口类中进行异常处理。现在介绍一种更简单的全局异常处理方法。

使用@ControllerAdvice类来进行全局异常处理。
```java
@ControllerAdvice
class GlobalControllerExceptionHandler {

  // 异常处理方法：
  // 根据特定的异常返回指定的 HTTP 状态码
  @ResponseStatus(value=HttpStatus.BAD_REQUEST)  // 400
  @ExceptionHandler(ConstraintViolationException.class)
  @ResponseBody
  public RestServiceError handleValidationException(ConstraintViolationException ex) {
        Set<ConstraintViolation<?>> errors = ex.getConstraintViolations();
        StringBuilder strBuilder = new StringBuilder();
        for (ConstraintViolation<?> violation : errors) {
            strBuilder.append(violation.getMessage() + "\n");
        }
        return RestServiceError.build(RestServiceError.Type.VALIDATION_ERROR, strBuilder.toString());
  }
  
  // 通用异常的处理，返回500
  @ResponseStatus(value=HttpStatus.INTERNAL_SERVER_ERROR)  // 500
  @ExceptionHandler(Exception.class)
  @ResponseBody
  public RestServiceError handleException(Exception ex) {
        return RestServiceError.build(RestServiceError.Type.INTERNAL_SERVER_ERROR, ex.getMessage());
  }
}
```
我们可以看到该类的编写方法与上一种处理方式中的编写方法是一致的，相比上一种处理方式的优点是不用每个类去编写异常处理方式，简化了程序的开发，同时可以对所有异常进行集中处理。

# 五. 错误信息的语言本地化处理
上述几个方法中错误信息都是写在代码中的，无法支持多语言处理和自定义配置。下面介绍如何从配置文件中根据本地化语言读取相应的错误信息，能够在英语环境中返回英文描述，在中文环境中返回中文描述。

SpringBoot内置了国际化语言的处理机制，只需几个简单的配置就能够使用该功能。

首先在配置文件中指定信息描述的配置文件，以yml配置为例：
```yml
spring:
  messages:
    basename: i18n/messages
```
通过这个配置，程序会到resources/i18n目录下读取messages.properties、messages_zh_CN.properties等配置文件中的内容。
配置文件内容很简单：

``` 
error.badrequest = 错误的请求参数
error.internalserver = 内部服务器错误
error.validation = 数据校验错误
```

具体读取哪个配置文件，是根据语言环境进行判断的。判断的方法如下：

```java
@Component
public class LocaleMessageUtil {

    @Autowired
    private MessageSource messageSource;

    public RestServiceError getLocalErrorMessage(RestServiceError.Type errorCode, String description) {
        Locale locale = LocaleContextHolder.getLocale();
        String errorMessage = messageSource.getMessage(errorCode.getCode(), null, locale);
        RestServiceError error = RestServiceError.build(errorCode, errorMessage, description);
        return error;
    }

}
```
其中LocaleContextHolder.getLocale()就是读取语言环境的方法。

对上一章节中介绍的全局异常处理方法进行简单的改造，就能支持多语言的异常信息。

```java
@ControllerAdvice
class GlobalControllerExceptionHandler {
  @Autowired
  LocaleMessageUtil localeMessageUtil;
  // 异常处理方法：
  // 根据特定的异常返回指定的 HTTP 状态码
  @ResponseStatus(value=HttpStatus.BAD_REQUEST)  // 400
  @ExceptionHandler(ConstraintViolationException.class)
  @ResponseBody
  public RestServiceError handleValidationException(ConstraintViolationException ex) {
        Set<ConstraintViolation<?>> errors = ex.getConstraintViolations();
        StringBuilder strBuilder = new StringBuilder();
        for (ConstraintViolation<?> violation : errors) {
            strBuilder.append(violation.getMessage() + "\n");
        }
        return localeMessageUtil.getLocalErrorMessage(RestServiceError.Type.IVALIDATION_ERROR);
  }
  
  // 通用异常的处理，返回500
  @ResponseStatus(value=HttpStatus.INTERNAL_SERVER_ERROR)  // 500
  @ExceptionHandler(Exception.class)
  @ResponseBody
  public RestServiceError handleException(Exception ex) {
        return localeMessageUtil.getLocalErrorMessage(RestServiceError.Type.INTERNAL_SERVER_ERROR);
  }
}
```
改动的地方就是引入了我们上面编写的LocaleMessageUtil类，通过这个类的getLocalErrorMessage方法来生成多语言信息。

# 六. 总结
接口异常处理的核心内容就是根据具体异常返回指定的错误信息：
1. HTTP 状态码
2. 返回报文体中的错误描述

异常处理方式常用的有3种，建议用第3种方式进行集中的异常处理：
1. 在异常类中定义状态码和错误信息，适用于指定异常的处理
2. 在REST接口类中定义状态码和错误信息，适用于指定接口类的处理
3. 通过@ControllerAdvice注解定义全局状态码和错误信息
4. 通过SpringBoot的MessageSource来进行多语言支持的处理


