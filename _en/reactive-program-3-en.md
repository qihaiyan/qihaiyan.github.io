---
layout: post
title:  "Reactive Programming (Part 3): A Simple HTTP Service"
date:   2018-3-25 10:15:00 +0800
lang: en
slug_zh: reactive-program-3
tags: [spring,java]
categories: [spring boot]
image: assets/images/reactivehttp.png
description: "Part 3 of the Reactive programming series: migrate a Spring MVC application from blocking calls to a fully reactive stack with WebClient, Netty, and Reactor."
---

Continuing from the previous article on [Reactive programming](https://springcamp.cn/reactive-program-2/): we have covered the basic API, and now we start building a real application. Reactive is a good abstraction over concurrent programming, but it also exposes many low-level features that need our attention. When we use them, we can control details that used to be hidden inside containers, platforms, and frameworks.

## Spring MVC: From Blocking to Reactive

Reactive asks us to look at problems with a different mindset. Instead of the traditional request->response pattern, all data is published as a sequence (a Publisher) and then subscribed to (a Subscriber). Instead of waiting synchronously for the result, we register a callback. Once we get used to this style it no longer feels complicated. But there is no way to make the whole environment reactive at the same time, so we inevitably have to deal with old-style blocking APIs.

Suppose we have a blocking method that returns an HttpStatus:

``` java
private RestTemplate restTemplate = new RestTemplate();

private HttpStatus block(int value) {
    return this.restTemplate.getForEntity("http://example.com/{value}", String.class, value)
            .getStatusCode();
}
```

<!-- more -->

We need to call this method repeatedly with different arguments and process the results. This is a typical "scatter-gather" scenario — for example, extracting the top N entries from multiple pages.

Here is an example of the wrong way to do it:

``` java
Flux.range(1, 10) (1)
    .log()
    .map(this::block) (2)
    .collect(Result::new, Result::add) (3)
    .doOnSuccess(Result::stop) (4)
```

1. Call the endpoint 10 times
2. It blocks
3. Aggregate the results into a single object
4. Finish the processing at the end (the result is a ```Mono<Result>```)

Do not write code this way. It is a wrong implementation: it blocks the calling thread, which is no different from calling block() in a loop. A good implementation puts the ```block()``` call on a worker thread. We can use a method that returns a ```Mono<HttpStatus>```:

``` java
private Mono<HttpStatus> fetch(int value) {
    return Mono.fromCallable(() -> block(value)) (1)
        .subscribeOn(this.scheduler);            (2)
}
```

1. Put the blocking call in a ```Callable```
2. Subscribe on a worker thread

The ```scheduler``` is defined separately as a shared variable:

``` java

  Scheduler scheduler = Schedulers.parallel()

```

Then use ```flatMap()``` instead of ```map()```

``` java

Flux.range(1, 10)
    .log()
    .flatMap(                             (1)
        this::fetch, 4)                   (2)
    .collect(Result::new, Result::add)
    .doOnSuccess(Result::stop)

```

1. Process in parallel in new publishers
2. The concurrency argument of flatMap

## Embedding in a Non-Reactive Service

If you want to put the code above into a non-reactive service such as a servlet, you can use Spring MVC:

``` java

@RequestMapping("/parallel")
public CompletableFuture<Result> parallel() {
    return Flux.range(1, 10)
      ...
      .doOnSuccess(Result::stop)
      .toFuture();
}

```

After reading the javadoc of ```@RequestMapping``` we find that this method returns a ```CompletableFuture```, and the application chooses to produce the value on a separate thread. In our example that separate thread is provided by the ```scheduler```.

## No Free Lunch

Using worker threads for the scatter-gather computation is a good pattern, but it is not perfect — the caller is no longer blocked, but something is still blocked; the problem has merely been moved. We have a non-blocking IO HTTP service and put the processing into a thread pool with one thread per request — that is the servlet container's mechanism (Tomcat, for example). Requests are processed asynchronously, so Tomcat's internal worker threads are not blocked, and our ```scheduler``` creates 4 threads. With 10 requests to process, in theory the processing performance improves 4x. Put simply: if processing 10 requests sequentially on a single thread takes 1000ms, our approach needs only 250ms.

We can push performance further by adding threads (allocating 16):

``` java

private Scheduler scheduler = Schedulers.newParallel("sub", 16);

```

> Tomcat allocates 100 threads for requests by default. When all requests are processed at the same time, our scheduler thread pool becomes a bottleneck — the number of threads in our scheduler pool is far smaller than Tomcat's. This shows that performance tuning is not a simple matter: you need to consider how the various parameters match the available resources.

Instead of a fixed-size thread pool we can use a more flexible one that adjusts the number of threads dynamically as needed. Reactor already provides such a mechanism: with ```Schedulers.elastic()``` you can see the thread count grow as the number of requests increases.

## Going Fully Reactive

Bridging from blocking calls to reactive is an effective pattern, and it is easy to implement with Spring MVC. Next we will drop the blocking mode entirely and adopt the new API and the new tools. In the end we go fully reactive across the stack.

In our example, the first step is to replace ```spring-boot-starter-web``` with ```spring-boot-starter-web-reactive```:

Maven:

``` xml

<dependencies>
  <dependency>
   <groupId>org.springframework.boot.experimental</groupId>
     <artifactId>spring-boot-starter-web-reactive</artifactId>
  </dependency>
  ...
</dependencies>
    <dependencyManagement>
     <dependencies>
       <dependency>
         <groupId>org.springframework.boot.experimental</groupId>
         <artifactId>spring-boot-dependencies-web-reactive</artifactId>
         <version>0.1.0.M1</version>
         <type>pom</type>
         <scope>import</scope>
      </dependency>
     </dependencies>
    </dependencyManagement>

```

Gradle:

``` groovy

dependencies {
	compile('org.springframework.boot.experimental:spring-boot-starter-web-reactive')
    ...
}
dependencyManagement {
	imports {
		mavenBom "org.springframework.boot.experimental:spring-boot-dependencies-web-reactive:0.1.0.M1"
	}
}

```

In the controller, instead of returning a ```CompletableFuture``` we now return a ```Mono```:

``` java

@RequestMapping("/parallel")
public Mono<Result> parallel() {
    return Flux.range(1, 10)
            .log()
            .flatMap(this::fetch, 4)
            .collect(Result::new, Result::add)
            .doOnSuccess(Result::stop);
}

```

Put this code into a Spring Boot application and it can run on Tomcat, Jetty, or Netty, depending on which jar is on the classpath. Tomcat is the default container; to use a different one, remove Tomcat from the classpath and bring in the other container. The three containers differ little in startup time, memory usage, and runtime resources.

We still call ```block()``` to block the service endpoint, so we still need to subscribe on a worker thread to avoid blocking the caller. We can also switch to a non-blocking client, for example replacing ```RestTemplate``` with the new ```WebClient```:

``` java

private WebClient client = new WebClient(new ReactorHttpClientRequestFactory());

private Mono<HttpStatus> fetch(int value) {
    return this.client.perform(HttpRequestBuilders.get("http://example.com"))
            .extract(WebResponseExtractors.response(String.class))
            .map(response -> response.getStatusCode());
}

```

Note that ```WebClient.perform()``` returns a reactive type that is converted into a ```Mono<HttpStatus>```, but we do not subscribe to it. The subscription is done by the framework.

## Inversion of Control

Now we drop the concurrency argument from the ```fetch()``` calls:

``` java

@RequestMapping("/netty")
public Mono<Result> netty() {
    return Flux.range(1, 10) (1)
        .log() //
        .flatMap(this::fetch) (2)
        .collect(Result::new, Result::add)
        .doOnSuccess(Result::stop);
}

```

1. Make 10 calls
2. Process in parallel in new publishers

Since we no longer use extra subscription threads, the code is much simpler than in the blocking-to-reactive bridge version — we are now fully reactive. ```WebClient``` returns a ```Mono```, and naturally we need to use ```flatMap()``` in the processing chain. Writing code like this is a pleasant experience: easy to understand and easy to maintain. We no longer need a thread pool or concurrency arguments, and the magic number 4 that hurt performance is gone. Performance depends on system resources rather than the application's thread management.

The application can run on Tomcat, Jetty, or Netty. The Tomcat and Jetty support is based on Servlet 3.1 async processing and is limited to one thread per request; running on Netty has no such limitation. As long as the client does not block, client requests are dispatched as quickly as possible. Since the Netty service is not one thread per request, it does not use a huge number of threads.

> Note that in many applications the blocking calls are not just HTTP but also database operations. Very few databases currently support non-blocking clients (MongoDB and Couchbase aside). Thread pools and the blocking-to-reactive pattern will be around for a long time.

## Still No Free Lunch

First, our code is declarative, which makes it inconvenient to debug — when an error occurs it is not easy to locate. Using the raw APIs, for example using Reactor directly without the Spring framework, makes things worse, because we have to do a lot of error handling ourselves and write a lot of boilerplate for every network call. By combining Spring and Reactor we can conveniently inspect stack traces and uncaught exceptions. Understanding can still be difficult, since the threads things run on are not under our control.

Second, once a coding mistake causes a reactive callback to block, all requests on that thread hang. In a servlet container, because there is one thread per request, a blocked request does not affect the others. In reactive, one blocked request increases the latency of all requests.

## Summary

Being able to control every part of asynchronous processing is great: every level has its thread pools and queues. We can make some levels elastic and adjust them dynamically to the load. But that is also a burden, and we would like something simpler. Scalability analysis tends to point toward removing superfluous threads and not exceeding the limits of the hardware.

Reactive is not a solution to all problems — in fact it is not itself a solution; it merely promotes the emergence of solutions to a certain class of problems. The cost of learning, of adjusting the program, and of later maintenance can far outweigh the benefits. So be very careful when deciding whether or not to use reactive.
