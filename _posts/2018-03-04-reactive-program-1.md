---
layout: post
title:  "Reactive编程（一）:Reactive编程的背景"
date:   2018-3-4 14:38:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/background.jpg
---

Reactive编程很有趣，现在也有各种各样的讨论，概念上不是很容易理解。本文会以具体的形式介绍相关的概念。Reactive编程跟并发和高性能在概念上有一些重合，但在原理上完全不同。Reactive编程跟函数式编程是非常类似的。一些人认为Reactive编程并不是什么新概念，他们在日常工作中经常使用（例如javascript）。另一些人认为这是微软做出的新发明（Reactive这个名字最早来源于C#）。在java编程中最近也有了类似的技术（参见[Reactive Streams initiative](http://www.reactive-streams.org/)）。在何时和何处使用Reactive编程这个问题上很容易犯错误。

## 1.是什么？

Reactive编程是一种通过将智能路由和事件消费组合起来改变行为的微架构风格。这个定义有些抽象，你在网上会接触到其它的各种各样的定义。
Reactive编程的概念可以追溯到1970年或者更早，因此并不是什么新鲜概念，但是因为有了微服务和多核处理器，在现在的企业应用中有了新的用法。
下面有几个简单明了的解释：
```
Reactive编程背后的基本思想是指表示随时间变化的值的特定数据类型。处理这些随时间变化的值的方法里本身也包含着随时间变化的值。
```
以及
```
可以简单的把程序当作是一个电子表格，把变量当作是表格里的单元格。当表格里的某些单元格的值变化后，如果其它的单元格引用了这些单元格的值，那么其它的单元格的值也会跟着改变。这跟函数式编程是一样的。
```

函数式编程往往代表着高性能、并发、异步、非阻塞IO。开始时我们可以不必非用函数式编程，Reactive模型可以很自然的处理这些问题。我们真正关心的是解决这些问题的实现。我们可以用同步和单线程的方式来实现一个有效的函数式编程框架，但是这么做并没什么意义。

## 2. Reactive编程的应用场景

类似于“有什么好处？”这样的问题对于新手来说是很难回答的。有几个例子来解释通用的适用场景：

<!-- more -->

### 外部服务调用

当今的后端系统很多都是RESTful的，底层协议是阻塞和同步的。并且服务之间会相互调用，必须要等到第一个请求调用完成后才能调用下一个请求。客户端可能在服务端处理完成之前就放弃请求了。因此外部服务调用，特别是需要调用多个服务才能完成处理的时候，是一个需要去优化的场景。

### 高并发的消息消费

高并发的消息处理是企业应用的常见场景，Reactive模式非常适合处理消息（事件可以很容易的转换为消息）。

### 电子表格

这不是一个企业应用场景，但是Reactive模式可以很轻松的处理这种需求。

### 对异步调用进行抽象

Reactive编程可以让我们不用关心调用是同步的还是异步的，单纯的异步编程是很繁琐的，Reactive模式可以简化异步编程。

## 3. 比较

以下是几个与Reactive编程有类似概念的技术：

### Ruby Event-Machine

Event-Machine是一个并发编程的抽象。可以让Ruby用一个单线程来处理高并发的请求。

### Actor Model

与面向对象编程类似，Actor Model是计算机科学的一个重要研究方向，早在七十年代就有了。Actor是计算的一个抽象，可以用于并发系统。Actor之间相互发送消息，因此在某种意义上也是反应式的。Actor和Reactive在概念上有很高的重合度。区别往往在实现层面（例如[Akka](doc.akka.io/docs/akka/current/java.html)可以用于进程间通信，是这个框架的显著特点）。

### Deferred results (Futures)

Java 1.5引入了很多新特性，包括Doug Lea 的 "java.util.concurrent"，其中有deferred result这个概念，被封装成Future。这是对异步编程进行抽象的一个很好的例子，可以非异步的形式来开发异步程序。在简单的并发任务场景下，Future是很好用的，但是当这些任务相互依赖的时候，会陷入“nested callback hell”。而Reactive可以避免这种情况的出现。

### Map-reduce and fork-join

将并行处理进行抽象是很有意义的，这样的例子很多。Java编程中最近有了Map-reduce 和 fork-join。Map-reduce用于Hadoop，fork-join是jdk1.7之后的版本自带的功能。这2个技术与Deferred results类似，不能应对复杂的组合调用场景。

### Coroutines

coroutine可以相互之间传递控制权，不用由调用者统一协调，可以简化并发编程。可以用coroutine来实现Reactive编程。Fibers和Generators都属于coroutine技术。

## Reactive Programming in Java

java不是“reactive”的语言，不能原生支持Coroutine。在JVM上的其它语言（Scala 和 Clojure）可以很好的支持Coroutine，java直到jdk9才支持。但是很多技术已经在jvm上实现了Reactive的支持：

### Reactive Streams

一个非常底层的约定，提供了Publisher和Subscriber接口。被集成到jdk9的java.util.concurrent.Flow包中。

### RxJava

Netflix开源的技术，内部已经使用Reactive编程已经很长时间了。根据David Karnok的[Generations of Reactive](https://akarnokd.blogspot.co.uk/2016/03/operator-fusion-part-1.html)中的分类，RxJava是第二代Reactive技术。

### Reactor

Spring团队开源的技术。

根据David Karnok的[Generations of Reactive](https://akarnokd.blogspot.co.uk/2016/03/operator-fusion-part-1.html)中的分类，RxJava是第四代Reactive技术。

### Spring Framework 5.0

内置了Reactive的特性，包含了构建HTTP服务和客户端的工具。Spring构建于Reactor技术之上，但是用户可以自由选择底层是使用Reactor还是RxJava。服务器支持omcat, Jetty, Netty 和 Undertow。

### [Ratpack](https://ratpack.io/)

一组构建高性能web应用的工具，Spring Boot可以直接使用该框架。

### Akka

一个实现Actor模型的开发框架，可以在Scala和Java中使用，是第三代的Reactive技术。

## 4. 为什么是现在？

Reactive技术的热度在不断提升，是因为该技术可以帮助我们节省服务器资源，可以用少量的线程支持更高的负载。Reactive、非阻塞、异步提供了很好的解决问题的方法。但是天下没有免费的午餐，每种技术都有适用场景。Reactive并不能直接解决我们的问题，只是让我们在解决问题时多了一种选择。

## 5. 总结

此文从概念上介绍了Reactive编程，在[下一节](https://springcamp.cn/spring-boot/reactive-program-2)中我们看一些具体的代码示例。最重要的是，我们会告诉你何时选择Reactive技术，何时选择现有的技术。