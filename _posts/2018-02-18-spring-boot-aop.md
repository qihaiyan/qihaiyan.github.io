---
layout: post
title:  "SpringBoot项目中使用AOP"
date:   2018-2-18 21:31:00 +0800
tags: [spring]
categories: [spring-boot]
image: assets/images/aop.png
---
## 1.概述

将通用的逻辑用AOP技术实现可以极大的简化程序的编写，例如验签、鉴权等。Spring的声明式事务也是通过AOP技术实现的。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-aop](https://github.com/qihaiyan/springcamp/tree/master/spring-aop)

Spring的AOP技术主要有4个核心概念：

1. Pointcut: 切点，用于定义哪个方法会被拦截，例如 ```execution(* cn.springcamp.springaop.service.*.*(..))```

2. Advice: 拦截到方法后要执行的动作

3. Aspect: 切面，把Pointcut和Advice组合在一起形成一个切面

4. Join Point: 在执行时Pointcut的一个实例

5. Weaver: 实现AOP的框架，例如 AspectJ 或 Spring AOP

## 2. 切点定义

常用的Pointcut定义有 execution 和 @annotation 两种。execution 定义对方法无侵入，用于实现比较通用的切面。@annotation 可以作为注解加到特定的方法上，例如Spring的Transaction注解。

execution切点定义应该放在一个公共的类中，集中管理切点定义。

示例：

```java
public class CommonJoinPointConfig {
    @Pointcut("execution(* cn.springcamp.springaop.service.*.*(..))")
    public void serviceLayerExecution() {}
}
```

这样在具体的Aspect类中可以通过 ```CommonJoinPointConfig.serviceLayerExecution()```来引用切点。

```java
public class BeforeAspect {
    @Before("CommonJoinPointConfig.serviceLayerExecution()")
    ...
}
```

当切点需要改变时，只需修改CommonJoinPointConfig类即可，不用修改每个Aspect类。

<!-- more -->

## 3. 常用的切面

1. Before: 在方法执行之前执行Advice，常用于验签、鉴权等。

2. After: 在方法执行完成后执行，无论是执行成功还是抛出异常.

3. AfterReturning: 仅在方法执行成功后执行.

4. AfterThrowing: 仅在方法执抛出异常后执行.

一个简单的Aspect：

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

## 4. 自定义注解

假设我们想收集特定方法的执行时间，一种比较合理的方式是自定义一个注解，然后在需要收集执行时间的方法上加上这个注解。

首先定义一个注解TrackTime：

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
public @interface TrackTime {
    String param() default "";
}
```

然后再定义一个Aspect类，用于实现注解的行为：

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

在某个方法上使用这个注解，就可以收集这个方法的执行时间：

```java
@TrackTime(param = "myService")
public String runFoo() {
    System.out.println(" -------------> foo");
    return "foo";
}
```

注意 ```@TrackTime(param = "myService")``` 注解是可以传参的。

为了让注解可以传参数，需要在定义注解时指定一个参数```String param() default "默认值"```，

同时在Aspect类中，around方法上加上相应的参数，@Around注解中也需要用参数的变量名trackTime，而不能用类名TrackTime。

```java
@Around("@annotation(trackTime)")
public Object around(ProceedingJoinPoint joinPoint, TrackTime trackTime)
```

## 5.总结

在运行示例项目时，控制台会输出以下内容：

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

可以看出几种 Aspect 的执行顺序依次为 Before After Around AfterReturning(AfterThrowing)