---
layout: post
title:  "Reactive Programming (Part 2): Code Demonstration"
date:   2018-3-18 14:38:00 +0800
lang: en
slug_zh: reactive-program-2
tags: [spring,java]
categories: [spring boot]
image: assets/images/code.jpg
description: "Part 2 of the Reactive programming series: understand the core elements through concrete Reactor code, learn to control data flow and use background threads."
---

Continuing from the previous article on [Reactive programming](https://springcamp.cn/reactive-program-1/), we keep explaining concepts with real code. We will go a step further in understanding what makes reactive different and what it can do. The examples are abstract, but they let us understand the APIs and programming style being used and truly feel what makes it different. We will look at the core elements of reactive, learn how to control the flow of data, and, where needed, use background threads to do the processing.

## Setting Up the Project

We will use the Reactor library for the demonstration. Other tools can of course be used. If you don't want to copy and paste the code, you can use the example project on [GitHub](https://github.com/dsyer/reactive-notes) directly.

Use [https://start.spring.io](https://start.spring.io) to create an empty project and add the Reactor Core dependency.

You can use Maven:

``` xml
<dependency>
  <groupId>io.projectreactor</groupId>
  <artifactId>reactor-core</artifactId>
  <version>3.0.0.RC2</version>
</dependency>
```

Or Gradle:

``` java
compile 'io.projectreactor:reactor-core:3.0.0.RC2'
```

## How It Works

Reactive is a sequence of events together with the two parties that publish and subscribe to those events. We can also call it a stream. We use the word streams where needed, but Java 8 has the java.util.Stream library, which is a different concept from what we are discussing here — do not confuse the two. We will focus as much as possible on publishers and subscribers (the behavior of Reactive Streams).

We will use the ```Reactor``` library and call a publisher a ```Flux``` (it implements the Reactive Streams ```Publisher``` interface); in the RxJava library the equivalent concept is called an ```Observable```. (In Reactor 2.0 it was called Stream, which is easily confused with Java 8 Streams, so we only use the new definition from Reactor 3.0).

<!-- more -->

## Creation

A ```Flux``` is a Publisher of a sequence of POJO-typed events: for example, ```Flux<T>``` is a Publisher of type ```T```. ```Flux``` has a range of static methods for creating instances from different sources. For example, to create a ```Flux``` from an array:

``` java

Flux<String> flux = Flux.just("red", "white", "blue");

```
We have created a Flux; now let's do something with it. In fact there are only two things you can do with it: apply operators (to transform it or combine it with other sequences) and subscribe to it.

## Single-Value Sequences

Sequences we encounter often have only one element, or none at all — for example, looking up a record by id. In Reactor, Mono represents a single-value Flux or an empty Flux. The Mono API is similar to Flux's but more concise, because not every operation makes sense for a single-value sequence. The equivalent type in RxJava is called Single, and an empty sequence is a Completable. In Reactor an empty sequence is a ```Mono<Void>```.

## Operators

Most methods on a Flux are operators. We will not go through all of them here (see the javadoc); we just need to understand what an operator is and what it can do.
For example, ```log()``` can display the internal events of a Flux, or ```map()``` can transform values:

``` java

Flux<String> flux = Flux.just("red", "white", "blue");

Flux<String> upper = flux
  .log()
  .map(String::toUpperCase);

```

This code converts the input strings to uppercase — very simple and clear. The interesting part (keep this in mind at all times, even though it feels unfamiliar at first) is that no data has been processed yet. Nothing is printed because nothing has happened (try running the code yourself): calling operators on a Flux merely builds an execution plan. The logic implemented by the operators is only executed when data starts to flow — when someone subscribes to the Flux.

Java 8 Streams have a similar way of processing data:

``` java

Stream<String> stream = Streams.of("red", "white", "blue");
Stream<String> upper = stream.map(value -> {
    System.out.println(value);
    return value.toUpperCase();
});

```
But Flux and Stream are very different, and the Stream API does not fit reactive.

## Subscribing

To make the data flow, we need to subscribe to the Flux with the subscribe() methods. These walk back up the chain of operators we defined and ask the publisher to produce data. In our simple example the collection of strings will be iterated and processed. In more complex scenarios it could be reading files from the file system, fetching data from a database, or calling an HTTP service.

Let's start calling subscribe():

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
.subscribe();

```

The output:

```

09:17:59.665 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxIterable$IterableSubscription@3ffc5af1)
09:17:59.666 [main] INFO reactor.core.publisher.FluxLog -  request(unbounded)
09:17:59.666 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
09:17:59.667 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
09:17:59.667 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
09:17:59.667 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

You can see that when subscribe() is called without arguments, it asks the publisher to send all the data — there is a single request, and it is "unbounded". We can also see the callbacks for each published item (onNext()), the completion callback (onComplete()), and the callback for the original subscription (onSubscribe()). If needed, we can also listen for these events using the Flux doOn*() methods.

The subscribe() method is overloaded, with many variants. One important and commonly used form takes callback arguments: the first is a Consumer called back for each item, you can add an optional Consumer for error handling, and a Runnable to be executed when the sequence completes.

For example, adding a callback for each item:

``` java

Flux.just("red", "white", "blue")
    .log()
    .map(String::toUpperCase)
.subscribe(System.out::println);

```

The output is:

```

09:56:12.680 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@59f99ea)
09:56:12.682 [main] INFO reactor.core.publisher.FluxLog -  request(unbounded)
09:56:12.682 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
RED
09:56:12.682 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
WHITE
09:56:12.682 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
BLUE
09:56:12.682 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

We can control the flow of data in several ways to make it "bounded". The internal interface used for control is the Subscription, obtained from the Subscriber. The complex form equivalent to the simple subscribe() call above is:

``` java

.subscribe(new Subscriber<String>() {

    @Override
    public void onSubscribe(Subscription s) {
        s.request(Long.MAX_VALUE);
    }
    @Override
    public void onNext(String t) {
        System.out.println(t);
    }
    @Override
    public void onError(Throwable t) {
    }
    @Override
    public void onComplete() {
    }

});

```

To control the flow so that 2 items are consumed at a time, we can use the Subscription more intelligently:

``` java

.subscribe(new Subscriber<String>() {

    private long count = 0;
    private Subscription subscription;

    @Override
    public void onSubscribe(Subscription subscription) {
        this.subscription = subscription;
        subscription.request(2);
    }

    @Override
    public void onNext(String t) {
        count++;
        if (count>=2) {
            count = 0;
            subscription.request(2);
        }
     }
...

```

This Subscriber bundles 2 items at a time. This scenario is so common that we would consider extracting the implementation into a dedicated class to make it easier to use. The output is as follows:

```

09:47:13.562 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@61832929)
09:47:13.564 [main] INFO reactor.core.publisher.FluxLog -  request(2)
09:47:13.564 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  request(2)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

In fact, batch subscription is such a common scenario that Flux already includes a method for it. The example above can be written as:

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
.subscribe(null, 2);

```

(Note that the subscribe method takes a request-limit argument.) The output is:

```

10:25:43.739 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@4667ae56)
10:25:43.740 [main] INFO reactor.core.publisher.FluxLog -  request(2)
10:25:43.740 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  request(2)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

## Threads, Schedulers, and Background Processing

An interesting feature of the examples above is that all the log methods run on the main thread — the thread of the caller of subscribe(). This is a key point: Reactor achieves high performance with as few threads as possible. For the past 5 years we have been used to improving system performance with multiple threads, thread pools, and asynchronous processing, so this new way of thinking may come as a surprise. But the fact is that thread switching is expensive, even on the JVM, a technology specifically optimized for thread handling. Computing on a single thread is always much faster. Reactor gives us a way to do asynchronous programming and assumes that we know what we are doing.

Flux provides methods to control thread boundaries. For example, you can use ```Flux.subscribeOn()``` to configure the subscription to be processed on a background thread:

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
  .subscribeOn(Schedulers.parallel())
.subscribe(null, 2);

```

The output:

```

13:43:41.279 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@58663fc3)
13:43:41.280 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  request(2)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(red)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(white)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  request(2)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(blue)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onComplete()

```

You can see that the subscription and all the processing happen on the background thread "parallel-1-1". A single thread is fine for CPU-intensive work; however, IO-intensive work could block. In that scenario we want the processing to complete as much as possible without blocking the caller. A thread pool still helps a lot, and we can get one with ```Schedulers.parallel()```. To split the processing of individual items onto separate threads, we need to put each item in its own publisher, with each publisher requesting execution results on a background thread. One way to do this is to call the flatMap() operator, which maps the items to a Publisher and returns a sequence of a new type:

``` java

Flux.just("red", "white", "blue")
  .log()
  .flatMap(value ->
     Mono.just(value.toUpperCase())
       .subscribeOn(Schedulers.parallel()),
     2)
.subscribe(value -> {
  log.info("Consumed: " + value);
})

```

Note that ```flatMap()``` puts the items into a child publisher, so we can control the subscription of each child item instead of the subscription of the whole sequence. Reactor's internal default behavior is to stay on one thread for as long as possible, so if you need specific items processed on a background thread, you must state it explicitly. This is, in fact, one of a series of methods that force parallel computation.

The output:

```

15:24:36.596 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxIterable$IterableSubscription@6f1fba17)
15:24:36.610 [main] INFO reactor.core.publisher.FluxLog -  request(2)
15:24:36.610 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
15:24:36.613 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
15:24:36.613 [parallel-1-1] INFO com.example.FluxFeaturesTests - Consumed: RED
15:24:36.613 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  request(1)
15:24:36.613 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(blue)
15:24:36.613 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onComplete()
15:24:36.614 [parallel-3-1] INFO com.example.FluxFeaturesTests - Consumed: BLUE
15:24:36.617 [parallel-2-1] INFO com.example.FluxFeaturesTests - Consumed: WHITE

```

Now multiple threads are doing the processing, and the batching argument in flatMap() guarantees that 2 items are processed at a time whenever possible. Reactor tries to be as smart as possible, prefetching items from the Publisher and estimating the subscriber's waiting time.

Flux also has a publishOn() method that works similarly, except that it controls the behavior of the publisher:

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
  .subscribeOn(Schedulers.newParallel("sub"))
  .publishOn(Schedulers.newParallel("pub"), 2)
.subscribe(value -> {
    log.info("Consumed: " + value);
});

```

The output:

```

15:12:09.750 [sub-1-1] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxIterable$IterableSubscription@172ed57)
15:12:09.758 [sub-1-1] INFO reactor.core.publisher.FluxLog -  request(2)
15:12:09.759 [sub-1-1] INFO reactor.core.publisher.FluxLog -  onNext(red)
15:12:09.759 [sub-1-1] INFO reactor.core.publisher.FluxLog -  onNext(white)
15:12:09.770 [pub-1-1] INFO com.example.FluxFeaturesTests - Consumed: RED
15:12:09.771 [pub-1-1] INFO com.example.FluxFeaturesTests - Consumed: WHITE
15:12:09.777 [sub-1-1] INFO reactor.core.publisher.FluxLog -  request(2)
15:12:09.777 [sub-1-1] INFO reactor.core.publisher.FluxLog -  onNext(blue)
15:12:09.777 [sub-1-1] INFO reactor.core.publisher.FluxLog -  onComplete()
15:12:09.783 [pub-1-1] INFO com.example.FluxFeaturesTests - Consumed: BLUE

```

Note that the subscriber's callback (the "Consumed: …" messages) executes on the publisher thread ```pub-1-1```. If you remove the subscribeOn() method, you will find that all the items are processed on thread ```pub-1-1``` as well. This shows once again that Reactor uses as few threads as possible — if you do not explicitly ask to switch threads, the next call executes on the current call's thread.

## Extractors: Subscribers with Side Effects

Another way to subscribe to a sequence is to call ```Mono.block()```, ```Mono.toFuture()```, or ```Flux.toStream()``` (these are extractor methods that convert reactive types into blocking types). Flux also has collectList() and collectMap(), which convert a Flux into a Mono. They do not truly subscribe to the sequence, but they throw away the ability to control the subscription of individual items.

A warning: the golden rule is "never call an extractor". There are, of course, some exceptions — for example, in a test program you need to be able to block in order to aggregate the results.

These methods are for converting reactive to blocking mode when we need to adapt to an old-style API, such as Spring MVC. When we call Mono.block(), we give up all the advantages of Reactive Streams. This is the key difference between Reactive Streams and Java 8 Streams — a Java Stream only has an "all or nothing" subscription model, equivalent to Mono.block(). Of course, subscribe() also blocks the calling thread, so it is just as dangerous as the conversion methods, but there are enough means of control — you can use subscribeOn() to prevent blocking, and you can use backpressure to let items spill over and periodically decide whether to continue processing.

## Summary

In this article we covered the basic concepts of Reactive Streams and the Reactor API. You can learn more from the sample code on [GitHub](https://github.com/dsyer/reactive-notes) or the [Lite RX Hands On](https://github.com/reactor/lite-rx-api-hands-on) workshop project. In the next article we dig deeper into blocking, dispatching, asynchrony, and other aspects of the reactive model, and show the opportunities where you can really benefit.
