---
layout: post
title:  "Reactive编程（二）:代码演示"
date:   2018-3-18 14:38:00 +0800
tags: [spring,java]
categories: [spring-boot]
---

书接上文 [Reactive编程](https://springcamp.cn/spring-boot/reactive-program-1/) ，我们继续用真实的代码来解释一些概念。我们会更进一步理解Reactive的与众不同以及它的功能。这些例子很抽象，但能够让我们更进一步理解用到的API和编程风格，真实的感受它的与众不同。我们将会看到Reactive的核心元素，学习如何控制数据流，如果需要的话还会用到后台线程进行处理。

## 建立项目

我们用Reactor库来进行演示。当然也可以用其它的工具。如果不想拷贝黏贴代码，可以直接使用 [github](https://github.com/dsyer/reactive-notes) 上的示例项目。

通过 [https://start.spring.io](https://start.spring.io) 来建立一个空的项目并添加Reactor Core依赖。

可以使用Maven:

``` xml
<dependency>
  <groupId>io.projectreactor</groupId>
  <artifactId>reactor-core</artifactId>
  <version>3.0.0.RC2</version>
</dependency>
```

也可以使用Gradle:

``` java
compile 'io.projectreactor:reactor-core:3.0.0.RC2'
```

## 工作原理

Reactive由一系列事件以及发布和订阅这些事件的2个参与方组成的一个序列。我们也可以称之为stream。如果需要，我们使用streams这个名词，但是java8有一个java.util.Stream库，与我们在这儿要讲的概念是不同的，不要将这2个概念混淆。我们尽量集中阐述publisher和subscriber（Reactive Streams的行为）。

我们会使用```Reactor```库，把publisher称为 ```Flux```（实现了Reactive Streams的```Publisher```接口），在RxJava库中的名称是```Observable``` ，代表的是类似的概念。(Reactor2.0中的名称为Stream，很容易跟Java 8 的 Streams混淆，因此我们只使用Reactor 3.0中的新定义)。

<!-- more -->

## 创建

```Flux``` 是POJO类型的事件序列的一个Publisher，例如 ```Flux<T>``` 是类型 ```T``` 的一个Publisher。```Flux``` 有一系列从不同的来源创建示例的静态方法。例如从数组创建 ```Flux``` ：

``` java

Flux<String> flux = Flux.just("red", "white", "blue");

```
我们创建了一个Flux，现在我们开始用它做一些事情。实际上只有2件事可以做：操作（转换或与其它序列组合）和订阅。

## 单值序列

我们经常遇到的序列往往只有一个元素，或者是没有元素，例如通过id查找记录。在Reactor中Mono表示单值Flux或空Flux。Mono的API与Flux类似，但是更简洁，因为不是所有的操作对单值序列有意义。RxJava中类似的类型叫Single，空序列叫Completable。在Reactor中空序列是```Mono<Void>```。

## 操作符

Flux的绝大部分方法都是操作。在这儿我们不会把所有的方法都讲一遍（可以看javadoc），我们只需要弄明白操作是什么，可以做什么。
例如，可以用```log()```将Flux的内部事件显示出来，或者用```map()```进行转换：

``` java

Flux<String> flux = Flux.just("red", "white", "blue");

Flux<String> upper = flux
  .log()
  .map(String::toUpperCase);

```

这段代码将输入的字符串转换成大写，非常简单明了。同时很有意思的一点是（时刻注意，虽然刚开始不太习惯），数据并没有开始处理。什么都不会显示，因为什么都没有发生（可以自己运行一下代码），调用Flux的操作符仅仅是建立了一个执行计划。操作符实现的逻辑只有当数据开始流动时才会执行，当某一方订阅这个Flux的时候。

Java 8 的 Streams 也有类似的处理数据流的方式：

``` java

Stream<String> stream = Streams.of("red", "white", "blue");
Stream<String> upper = stream.map(value -> {
    System.out.println(value);
    return value.toUpperCase();
});

```
但是Flux 和 Stream有非常大的差异，Stream的API不适用于Reactive。

## 订阅

要让数据流生效，我们需要用subscribe()方法来订阅Flux，这些方法会回溯我们之前定义的操作链，请求publisher 产生数据。在我们的简单示例中，字符串集合会被遍历进行处理。在更复杂的场景中，可能是从文件系统读取文件，或者从数据库中读取数据，或者是调用一个http服务。

开始调用subscribe()：

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
.subscribe();

```

输出内容：

```

09:17:59.665 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxIterable$IterableSubscription@3ffc5af1)
09:17:59.666 [main] INFO reactor.core.publisher.FluxLog -  request(unbounded)
09:17:59.666 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
09:17:59.667 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
09:17:59.667 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
09:17:59.667 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

可以看到当subscribe()没有参数时，会请求 publisher 发送所有的数据 - 只有一个request并且是 "unbounded"。我们还可以看到发布的每一项的回调(onNext())，结束的回调(onComplete())，以及原始订阅的回调(onSubscribe())。如果需要，我们还可以用Flux的doOn*()方法来监听这些事件的回调。

subscribe()方法是重载的，有很多变体。其中一个重要且常用的形式是带回调参数。第一个参数是 Consumer ，用于每一个数据项的回调，还可以增加一个可选的 Consumer 用于错误处理，以及一个序列完成后执行的 Runnable 。

例如，为每一个数据项增加回调：

``` java

Flux.just("red", "white", "blue")
    .log()
    .map(String::toUpperCase)
.subscribe(System.out::println);

```

输出为：

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

我们可以通过多种方法控制数据流使它变成 "bounded" 。用于控制的内部接口是从 Subscriber 获取到的 Subscription 。与前面简单调用 subscribe() 等价的复杂形式是：

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

想要控制数据流为一次消费2个数据项，可以更加智能的使用Subscription ：

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

这个 Subscriber 每次会打包2个数据项。这个场景很普遍，因此我们会考虑把实现提取到一个专门的类中以方便使用。输出如下：

```

09:47:13.562 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@61832929)
09:47:13.564 [main] INFO reactor.core.publisher.FluxLog -  request(2)
09:47:13.564 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  request(2)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
09:47:13.565 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

事实上批量订阅是一个非常普遍的场景，因此 Flux 已经包含了相关的方法。上面的例子可以实现为：

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
.subscribe(null, 2);

```

（注意subscribe方法带了一个请求限制参数）输出为：

```

10:25:43.739 [main] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@4667ae56)
10:25:43.740 [main] INFO reactor.core.publisher.FluxLog -  request(2)
10:25:43.740 [main] INFO reactor.core.publisher.FluxLog -  onNext(red)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  onNext(white)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  request(2)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  onNext(blue)
10:25:43.741 [main] INFO reactor.core.publisher.FluxLog -  onComplete()

```

## 线程、调度和后台处理

上面的示例中有一个有趣的特点是所有的log方法都是在主线程中执行的，即 subscribe() 调用者的线程。这是一个关键点：Reactor以尽可能少的线程来实现高性能。过去5年我们习惯于使用多线程、线程池和异步处理来提升系统性能。对于这种新的思路可能会比较诧异。但是事实是：即使是JVM这种专门对线程处理做过优化的技术，线程切换的成本也是很高的。在单个线程上进行计算总是要快的多。Reactor给了我们进行异步编程的方法，并且假设我们知道我们在做什么。

Flux提供了一些方法来控制线程的边界。例如，可以使用 ```Flux.subscribeOn()``` 配置一个订阅在后台线程中进行处理:

``` java

Flux.just("red", "white", "blue")
  .log()
  .map(String::toUpperCase)
  .subscribeOn(Schedulers.parallel())
.subscribe(null, 2);

```

输出结果：

```

13:43:41.279 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onSubscribe(reactor.core.publisher.FluxArray$ArraySubscription@58663fc3)
13:43:41.280 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  request(2)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(red)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(white)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  request(2)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onNext(blue)
13:43:41.281 [parallel-1-1] INFO reactor.core.publisher.FluxLog -  onComplete()

```

可以看到订阅和所有的处理都在 "parallel-1-1" 这个后台线程中。单线程对于CPU密集型的处理来说是没问题的。然而如果是IO密集型的处理就可能会阻塞。在这个场景中，我们希望处理尽可能的完成不至于阻塞调用方。一个线程池仍会提供很大的帮助，我们可以用 ```Schedulers.parallel()``` 获取线程池。将单个数据项的处理拆分到独立的线程中进行处理，我们需要把它放到独立的发布方中，每个发布方都在后台线程中请求执行结果。一种方法是调用 flatMap() 操作，会把数据项映射到一个 Publisher 并返回一个新类型的序列：

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

注意 ```flatMap()``` 把数据项放入一个子 publisher ，这样可以控制每个子项的订阅而不是整个序列的订阅。Reactor内部的默认行为可以尽可能长的挂起在一个线程上，因此如果需要特定的数据项在后台线程中处理，必须要明确的指明。事实上这是一系列强制进行并行计算的方法中的一种。

输出内容：

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

现在是多个线程在进行处理，并且 flatMap() 中的批量参数保证只要可能每次都会处理2个数据项。Reactor会让自己尽可能的聪明，预先从 Publisher 中提取数据项，并且估算订阅方的等待时间。

Flux 还有一个 publishOn() 方法的作用类似，只不过控制的是发布方的行为：

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

输出内容：

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

注意订阅方的回调（内容为 "Consumed: …​"）执行在发布方线程 ```pub-1-1``` 上。如果把 subscribeOn() 方法去掉，会发现所有的数据项的处理都在线程 ```pub-1-1``` 上。这再一次说明 Reactor 使用尽可能少的线程 - 如果没有明确的指定要切换线程，下一个调用会在当前调用的线程上执行。

## 提取器：有副作用的订阅者

另一种订阅序列的方式是调用 ```Mono.block()``` 或 ```Mono.toFuture()``` 或 ```Flux.toStream()``` (这些是提取器方法，将 Reactive 类型转换为阻塞类型)。Flux 还有 collectList() 和 collectMap() 将 Flux 转换成 Mono。他们并没有真正的订阅序列，但是他们会抛弃控制订阅单个数据项的能力。

警告：
一个黄金规则是“永远不要调用提取器”。当然有一些例外，例如在测试程序中需要能够通过阻塞来汇总结果。

这些方法用于将 Reactive 转换为阻塞模式，当我们需要适配一个老式的API，例如Spring MVC的时候。在调用 Mono.block() 的时候，我们放弃了 Reactive Streams 所有优势。这是 Reactive Streams 和 Java 8 Streams 的关键区别 - Java Stream只有 "all or nothing" 的订阅模式，等同于 Mono.block()。当然 subscribe() 也会阻塞调用线程，因此与转换方法一样危险，但是有足够的控制手段 - 可以用 subscribeOn() 防止阻塞，也可以通过背压来将数据项进行溢出并且定时的决定是否继续处理。

## 总结

这篇文章我们讲述了 Reactive Streams 和 Reactor API 的基本概念。可以通过 [GitHub](https://github.com/dsyer/reactive-notes) 上的示例代码或者是 [Lite RX Hands On](https://github.com/reactor/lite-rx-api-hands-on) 实验项目来进一步了解。在下一篇文章中我们会更深入的发掘 Reactive 模型中的阻塞、分发、异步等方面，并且展示能够真正受益的机会。