---
layout: post
title:  "Exception Handling for REST APIs in Spring Boot"
date:   2017-05-21 18:28:00 +0800
lang: en
slug_zh: spring-rest-exception
tags: [spring]
categories: [spring boot]
description: "How to handle exceptions in Spring Boot REST endpoints using @ResponseStatus, custom exception classes, and @ControllerAdvice for accurate HTTP status codes."
---
## 1. HTTP Status Codes

1. Status codes from 100 to 199 are informational and describe the handling of the request.
2. Status codes from 200 to 299 indicate that the request sent by the client has been received and processed correctly.
3. Status codes from 300 to 399 indicate that the client must take further action to complete the request, such as redirecting to another address.
4. Status codes from 400 to 499 indicate that the client's request contains an error and needs to be corrected. 404 is one such case.
5. Status codes from 500 to 599 indicate that the server encountered an internal error while processing the client's request.

In Spring Boot, if an endpoint has an unhandled exception, a 500 is returned, meaning internal server error. Simply put, if the back-end code does not handle the exception specially, any exception thrown results in the client receiving a 500 status code.

## 2. Defining the Status Code in the Exception Class

We can use the @ResponseStatus annotation to define the returned status code in an exception class.

<!-- more -->

For example:

Here is a user-defined exception class:

```java
@ResponseStatus(value=HttpStatus.NOT_FOUND, reason="No such Order")  // 404
 public class OrderNotFoundException extends RuntimeException {
     // ...
 }
```

Throw this exception from an endpoint:

```java
@RequestMapping(value="/orders/{id}", method=GET)
 public Order showOrder(@PathVariable("id") long id, Model model) {
     Order order = orderRepository.findOrderById(id);
     if (order == null) throw new OrderNotFoundException(id);
     return order;
 }
```

When the specified order id cannot be found, the endpoint returns 404. The reason is that the endpoint throws an OrderNotFoundException, and the @ResponseStatus annotation on that exception specifies the return code HttpStatus.NOT_FOUND, that is, 400.

## 3. Exception Handling in the Controller

You can define methods annotated with @ExceptionHandler in a controller class to handle exceptions from all endpoints in that class.

First define a class for returning detailed error information:

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

Define a REST controller class with exception handling methods:

```java
@RestController
public class ControllerWithExceptionHandling {

  // @RequestMapping methods
  ...
  
  // Exception handling methods:
  // return the specified HTTP status code for a particular exception
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
  
  // Handling of generic exceptions, returns 500
  @ResponseStatus(value=HttpStatus.INTERNAL_SERVER_ERROR)  // 500
  @ExceptionHandler(Exception.class)
  @ResponseBody
  public RestServiceError handleException(Exception ex) {
        return RestServiceError.build(RestServiceError.Type.INTERNAL_SERVER_ERROR, ex.getMessage());
  }
}
```

This way, if an exception occurs in any endpoint of the class, the corresponding HTTP status code is returned, and the response body contains the error description.

If the exception thrown by the endpoint is a ConstraintViolationException, the status code and error message defined in the handleValidationException method are returned; otherwise, the status code and error message defined in the handleException method are returned. You can add more exception handling methods to handle additional specific exceptions.

The error message structure is as follows:

```json
{"code":"error.internalserver","message":"内部服务器错误"}
```

## 4. Global Exception Handling

The approach above handles exceptions of a specific controller class and requires exception handling in every controller class. Now let's look at a simpler approach: global exception handling.

Use a @ControllerAdvice class for global exception handling.

```java
@ControllerAdvice
class GlobalControllerExceptionHandler {

  // Exception handling methods:
  // return the specified HTTP status code for a particular exception
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
  
  // Handling of generic exceptions, returns 500
  @ResponseStatus(value=HttpStatus.INTERNAL_SERVER_ERROR)  // 500
  @ExceptionHandler(Exception.class)
  @ResponseBody
  public RestServiceError handleException(Exception ex) {
        return RestServiceError.build(RestServiceError.Type.INTERNAL_SERVER_ERROR, ex.getMessage());
  }
}
```

As we can see, this class is written in the same way as in the previous approach. Compared with the previous approach, its advantage is that you do not have to write exception handling in every class, which simplifies development and allows all exceptions to be handled centrally.

## 5. Localizing Error Messages

In the approaches above, the error messages are hard-coded, so multi-language support and custom configuration are not possible. The following shows how to read the appropriate error message from configuration files based on the locale, so that an English environment returns English descriptions and a Chinese environment returns Chinese descriptions.

Spring Boot has built-in internationalization support; only a few simple configuration items are needed to use it.

First specify the message resource basename in the configuration file, using yml configuration as an example:

```yml
spring:
  messages:
    basename: i18n/messages
```

With this configuration, the application reads the contents of messages.properties, messages_zh_CN.properties, and other configuration files under the resources/i18n directory.
The configuration file contents are very simple:

```bash
error.badrequest = 错误的请求参数
error.internalserver = 内部服务器错误
error.validation = 数据校验错误
```

Which configuration file is read is determined by the locale. The lookup method is as follows:

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

Here LocaleContextHolder.getLocale() is the method that reads the current locale.

With a small change to the global exception handling method introduced in the previous section, exception messages can support multiple languages.

```java
@ControllerAdvice
class GlobalControllerExceptionHandler {
  @Autowired
  LocaleMessageUtil localeMessageUtil;
  // Exception handling methods:
  // return the specified HTTP status code for a particular exception
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
  
  // Handling of generic exceptions, returns 500
  @ResponseStatus(value=HttpStatus.INTERNAL_SERVER_ERROR)  // 500
  @ExceptionHandler(Exception.class)
  @ResponseBody
  public RestServiceError handleException(Exception ex) {
        return localeMessageUtil.getLocalErrorMessage(RestServiceError.Type.INTERNAL_SERVER_ERROR);
  }
}
```

The change is that we introduce the LocaleMessageUtil class written above and use its getLocalErrorMessage method to generate the localized messages.

## 6. Summary

The core of endpoint exception handling is returning the specified error information for a given exception:

1. The HTTP status code
2. The error description in the response body

There are three commonly used exception handling approaches, and the third one is recommended for centralized exception handling:

1. Define the status code and error message in the exception class, suitable for handling specific exceptions
2. Define the status code and error message in the REST controller class, suitable for handling a specific controller class
3. Define global status codes and error messages via the @ControllerAdvice annotation
4. Use Spring Boot's MessageSource for multi-language support
