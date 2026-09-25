---
layout: post
title:  "Using AOP in a Spring Boot Project"
date:   2018-2-18 21:31:00 +0800
lang: en
slug_zh: spring-boot-aop
tags: [spring]
categories: [spring boot]
image: assets/images/aop.png
description: "Core concepts and practical usage of Spring AOP: pointcuts with execution and @annotation, advice types, and centralizing cross-cutting logic in aspects."
---
## 1. Overview

Implementing common logic with AOP can greatly simplify coding, for example signature verification and access control. Spring's declarative transactions are also implemented with AOP.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-aop](https://github.com/qihaiyan/springcamp/tree/main/spring-aop)

Spring's AOP technology has 4 core concepts:

1. Pointcut: defines which methods will be intercepted, for example ```execution(* cn.springcamp.springaop.service.*.*(..))```

2. Advice: the action to take after a method is intercepted

3. Aspect: combines a Pointcut and an Advice to form an aspect

4. Join Point: an instance of a Pointcut at execution time

5. Weaver: the framework that implements AOP, for example AspectJ or Spring AOP

## 2. Pointcut Definition

There are two commonly used Pointcut definitions: execution and @annotation. The execution definition is non-invasive to methods and is used for fairly generic aspects. @annotation can be added as an annotation to specific methods, like Spring's Transaction annotation.

The execution pointcut definitions should be placed in a common class so that pointcut definitions are managed centrally.

Example:

```java
public class CommonJoinPointConfig {
    @Pointcut("execution(* cn.springcamp.springaop.service.*.*(..))")
    public void serviceLayerExecution() {}
}
```

Then in a concrete Aspect class, the pointcut can be referenced via ```CommonJoinPointConfig.serviceLayerExecution()```.

```java
public class BeforeAspect {
    @Before("CommonJoinPointConfig.serviceLayerExecution()")
    ...
}
```

When a pointcut needs to change, you only modify the CommonJoinPointConfig class instead of every Aspect class.

<!-- more -->

## 3. Common Aspects

1. Before: runs the Advice before the method executes, commonly used for signature verification, access control, etc.

2. After: runs after the method completes, whether it succeeded or threw an exception.

3. AfterReturning: runs only after the method executes successfully.

4. AfterThrowing: runs only after the method throws an exception.

A simple Aspect:

```java
@Aspect
@Component
public class BeforeAspect {
    @Before("CommonJoinPointConfig.serviceLayerExecution()")
    public void before(JoinPoint joinPoint) {
        System.out.println(" -------------> Before Aspect ");
        System.out.println(" -------------> before execution of " + joinPoint);
    }
}
```

## 4. Custom Annotation

Suppose we want to collect the execution time of specific methods. A reasonable way is to define a custom annotation and add it to the methods whose execution time we want to collect.

First define a TrackTime annotation:

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
public @interface TrackTime {
    String param() default "";
}
```

Then define an Aspect class that implements the annotation's behavior:

```java
@Aspect
@Component
public class TrackTimeAspect {
    @Around("@annotation(trackTime)")
    public Object around(ProceedingJoinPoint joinPoint, TrackTime trackTime) throws Throwable {
        Object result = null;
        long startTime = System.currentTimeMillis();
        result = joinPoint.proceed();
        long timeTaken = System.currentTimeMillis() - startTime;
        System.out.println(" -------------> Time Taken by " + joinPoint + " with param[" + trackTime.param() + "] is " + timeTaken);
        return result;
    }
}
```

Using this annotation on a method collects that method's execution time:

```java
@TrackTime(param = "myService")
public String runFoo() {
    System.out.println(" -------------> foo");
    return "foo";
}
```

Note that the ```@TrackTime(param = "myService")``` annotation accepts a parameter.

To let the annotation accept a parameter, specify one when defining the annotation: ```String param() default "默认值"```,

and in the Aspect class, the around method takes the corresponding parameter. The @Around annotation must also use the parameter's variable name trackTime, not the class name TrackTime.

```java
@Around("@annotation(trackTime)")
public Object around(ProceedingJoinPoint joinPoint, TrackTime trackTime)
```

## 5. Summary

When running the example project, the console outputs the following:

```
 -------------> Before Aspect 
 -------------> before execution of execution(String cn.springcamp.springaop.service.MyService.runFoo())
 -------------> foo
 -------------> Time Taken by execution(String cn.springcamp.springaop.service.MyService.runFoo()) with param[myService] is 8
 -------------> After Aspect 
 -------------> after execution of execution(String cn.springcamp.springaop.service.MyService.runFoo())
 -------------> AfterReturning Aspect 
 -------------> execution(String cn.springcamp.springaop.service.MyService.runFoo()) returned with value foo
```

As we can see, the aspects execute in the order: Before, After, Around, AfterReturning (AfterThrowing)
