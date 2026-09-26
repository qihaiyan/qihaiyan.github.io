---
layout: post
title:  "Reactive Programming (Part 1): Background of Reactive Programming"
date:   2018-3-4 14:38:00 +0800
lang: en
slug_zh: reactive-program-1
tags: [spring,java]
categories: [spring boot]
image: assets/images/background.jpg
description: "Part 1 of the Reactive series: concrete examples of core concepts, its relation to concurrency and functional programming, and Reactor and Reactive Streams."
---

Reactive programming is fun and is being discussed in all sorts of places, but its concepts are not easy to grasp. This article introduces the related concepts in a concrete way. Reactive programming overlaps conceptually with concurrency and high performance, but differs from them completely in principle. Reactive programming is very similar to functional programming. Some people believe reactive programming is not a new concept at all and that they use it every day (for example, in JavaScript). Others think it is a new invention from Microsoft (the name Reactive originally came from C#). Similar techniques have recently appeared in Java programming as well (see the [Reactive Streams initiative](http://www.reactive-streams.org/)). It is easy to make mistakes about when and where to use reactive programming.

## 1. What Is It?

Reactive programming is a micro-architecture style that changes behavior by combining smart routing and event consumption. This definition is somewhat abstract, and you will encounter many other definitions online.
The concept of reactive programming can be traced back to 1970 or even earlier, so it is nothing new, but thanks to microservices and multi-core processors it has found new uses in today's enterprise applications.
Here are a few simple, clear explanations:
```
The basic idea behind reactive programming is to have specific data types that represent values that change over time. The methods that process these time-varying values themselves contain values that change over time.
```
and
```
You can simply think of a program as a spreadsheet and variables as cells in the sheet. When the value of some cells changes, any other cells that reference those cells change as well. This is the same as functional programming.
```

Functional programming often implies high performance, concurrency, asynchrony, and non-blocking IO. To begin with we do not necessarily have to use functional programming; the reactive model can handle these concerns naturally. What we really care about is the implementation that solves these problems. We could implement an effective functional programming framework in a synchronous, single-threaded way, but there would be little point in doing so.

## 2. Use Cases for Reactive Programming

Questions like "What are the benefits?" are hard to answer for beginners. Here are a few examples that illustrate common use cases:

<!-- more -->

### External Service Calls

Most back-end systems today are RESTful, and the underlying protocol is blocking and synchronous. Services also call each other, and the next request cannot be made until the first request has completed. A client may give up on a request before the server has finished processing it. External service calls, especially when several services must be called to complete the processing, are therefore a scenario that needs optimizing.

### High-Concurrency Message Consumption

High-concurrency message processing is a common scenario in enterprise applications, and the reactive pattern is a great fit for handling messages (events can easily be converted into messages).

### Spreadsheets

This is not an enterprise scenario, but the reactive pattern handles this kind of requirement with ease.

### Abstracting Asynchronous Calls

Reactive programming frees us from caring whether a call is synchronous or asynchronous. Pure asynchronous programming is tedious, and the reactive pattern can simplify it.

## 3. Comparison

Here are a few technologies whose concepts resemble reactive programming:

### Ruby Event-Machine

Event-Machine is an abstraction for concurrent programming. It allows Ruby to handle highly concurrent requests with a single thread.

### Actor Model

Like object-oriented programming, the Actor Model is an important research direction in computer science that dates back to the seventies. An Actor is an abstraction of computation that can be used in concurrent systems. Actors send messages to each other, so in a sense they are reactive too. The Actor Model and Reactive overlap considerably at the conceptual level; the differences are usually at the implementation level (for example, [Akka](https://doc.akka.io/docs/akka/current/java.html) can be used for inter-process communication, a notable feature of that framework).

### Deferred results (Futures)

Java 1.5 introduced many new features, including Doug Lea's "java.util.concurrent", which contains the concept of the deferred result, encapsulated as a Future. It is a good example of abstracting asynchronous programming: you can write asynchronous programs in a non-asynchronous style. Futures work well for simple concurrent tasks, but when the tasks depend on each other you fall into "nested callback hell". Reactive avoids that situation.

### Map-reduce and fork-join

Abstracting parallel processing is very valuable, and there are many examples of it. In Java programming we recently got Map-reduce and fork-join. Map-reduce is used in Hadoop, and fork-join is built into the JDK from version 1.7 onwards. Like deferred results, these two techniques cannot handle complex combinations of calls.

### Coroutines

Coroutines can pass control to one another without the caller coordinating everything, which simplifies concurrent programming. Reactive programming can be implemented with coroutines. Fibers and Generators are both coroutine techniques.

## Reactive Programming in Java

Java is not a "reactive" language and cannot natively support coroutines. Other languages on the JVM (Scala and Clojure) support coroutines well; Java only gained support in JDK 9. But many technologies already provide reactive support on the JVM:

### Reactive Streams

A very low-level specification that provides the Publisher and Subscriber interfaces. It was integrated into the java.util.concurrent.Flow package in JDK 9.

### RxJava

An open source technology from Netflix, which has been using reactive programming internally for a long time. According to the classification in David Karnok's [Generations of Reactive](https://akarnokd.blogspot.co.uk/2016/03/operator-fusion-part-1.html), RxJava is second-generation reactive technology.

### Reactor

An open source technology from the Spring team.

According to the classification in David Karnok's [Generations of Reactive](https://akarnokd.blogspot.co.uk/2016/03/operator-fusion-part-1.html), Reactor is fourth-generation reactive technology.

### Spring Framework 5.0

Has reactive features built in, including tools for building HTTP services and clients. Spring is built on top of Reactor, but users are free to choose Reactor or RxJava underneath. The supported servers are Tomcat, Jetty, Netty, and Undertow.

### [Ratpack](https://ratpack.io/)

A set of tools for building high-performance web applications. Spring Boot can use this framework directly.

### Akka

A development framework implementing the Actor Model, usable from Scala and Java, and third-generation reactive technology.

## 4. Why Now?

Interest in reactive technology keeps growing because it helps us save server resources: a small number of threads can support a much higher load. Reactive, non-blocking, asynchronous — these provide a good way to solve problems. But there is no free lunch, and every technology has its appropriate use cases. Reactive does not solve our problems directly; it just gives us one more option when solving them.

## 5. Summary

This article introduced reactive programming conceptually; in [the next part](https://springcamp.cn/reactive-program-2/) we look at some concrete code examples. Most importantly, we will tell you when to choose reactive technology and when to stick with existing technology.
