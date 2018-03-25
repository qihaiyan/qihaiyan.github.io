---
layout: post
title:  "Reactive编程（三）:一个简单的HTTP服务"
date:   2018-3-25 10:15:00 +0800
tags: [spring,java]
categories: [spring-boot]
---

书接上文 [Reactive编程](https://springcamp.cn/spring-boot/reactive-program-2/) ，我们已经了解了基础的API，现在我们开始编写实际的应用。Reactive对并发编程进行了很好的抽象，也有很多底层的特性需要我们去关注。当使用这些特性时，我们可以对之前隐藏在容器、平台、框架中的细节进行控制。

## Spring MVC由阻塞转向Reactive

Reactive要求我们以不同的思路来看待问题。区别于传统的request->response模式，所有的数据都是发布为一个序列 (Publisher) 然后进行订阅（Subscriber）。区别于同步等待返回结果，改为注册一个回调。只要我们习惯了这种方式，就不会觉得很复杂。但是没办法让整个环境都同时变为Reactive模式，所以避免不了要跟老式的阻塞API打交道。

假设我们有一个返回HttpStatus的阻塞方法：

``` java
private RestTemplate restTemplate = new RestTemplate();

private HttpStatus block(int value) {
    return this.restTemplate.getForEntity("http://example.com/{value}", String.class, value)
            .getStatusCode();
}
```

<!-- more -->

我们需要传递不同的参数来重复调用这个方法，并对返回的结果进行处理。这是一个典型的 "scatter-gather"应用场景。例如从多个页面中提取前N条数据。

这是一个采用错误方式的例子：

``` java
Flux.range(1, 10) (1)
    .log()
    .map(this::block) (2)
    .collect(Result::new, Result::add) (3)
    .doOnSuccess(Result::stop) (4)
```

1. 调用10次接口
2. 产生阻塞
3. 将结果进行汇总后放入一个对象
4. 最后结束处理 (结果是一个 ```Mono<Result>```)

不要采用这种方式来编写代码。这是一种错误的实现方式，这样会阻塞住调用线程，这跟循环调用block()没什么区别。好的实现应该是把```block()```的调用放到工作线程中。我们可以采用一个返回```Mono<HttpStatus>```的方法：

``` java
private Mono<HttpStatus> fetch(int value) {
    return Mono.fromCallable(() -> block(value)) (1)
        .subscribeOn(this.scheduler);            (2)
}
```

1. 将阻塞调用放到一个 ```Callable`` 中
2. 在工作线程中进行订阅

```scheduler``` 单独定义为一个共享变量：

``` java

  Scheduler scheduler = Schedulers.parallel()

```

然后用 ```flatMap()``` 代替 ```map()```

``` java

Flux.range(1, 10)
    .log()
    .flatMap(                             (1)
        this::fetch, 4)                   (2)
    .collect(Result::new, Result::add)
    .doOnSuccess(Result::stop)

```

1. 在新的publisher中并行处理
2. flatMap的并行参数

## 嵌入 Non-Reactive 服务

如果想将上面的代码放入一个servlet这种的Non-Reactive的服务中，可以使用Spring MVC：

``` java

@RequestMapping("/parallel")
public CompletableFuture<Result> parallel() {
    return Flux.range(1, 10)
      ...
      .doOnSuccess(Result::stop)
      .toFuture();
}

```

在阅读了 ```@RequestMapping``` 的javadoc以后，我们会发现这个方法会返回一个 ```CompletableFuture``` ，应用会选择在单独的线程中返回值。在我们的例子中这个单独的线程由 ```scheduler``` 提供。

## 没有免费的午餐

利用工作线程进行 scatter-gather 计算是一个好的模式，但是也不完美 - 没有阻塞调用方，但还是阻塞了一些东西，只不过是把问题转移了。我们有一个非阻塞IO的 HTTP 服务，将处理放入线程池，一个请求一个线程 - 这是servlet容器的机制（例如tomcat）。请求是异步处理的，因此tomcat内部的工作线程没有被阻塞，我们的 ```scheduler``` 会创建4个线程。在处理10个请求时，理论上处理性能会提高4倍。简单来说，如果我们在单个线程中顺序处理10个请求要花1000ms，我们所采用的方式只需250ms。

我们可以通过增加线程来进一步提升性能（分配16个线程）：

``` java

private Scheduler scheduler = Schedulers.newParallel("sub", 16);

```

> Tomcat 默认会分配100个线程来处理请求，当所有的请求同时处理时，我们的 scheduler 线程池会成为一个瓶颈。我们的 scheduler 线程池数量远小于 Tomcat 的线程池数量。这说明性能调优不是一个简单的事情，需要考虑各个参数和资源的匹配情况。

相比固定数量的线程池，我们可以采用更灵活的线程池，可以根据需要动态调整线程数量。Reactor 已经提供了这种机制，使用 ```Schedulers.elastic()``` 后可以看到当请求增多时，线程数量会随之增加。

## 全面采用 Reactive

从阻塞调用到reactive的桥接是一种有效的模式，并且用Spring MVC的技术很容易实现。接下来我们将完全弃用阻塞模式，采用新的API和新的工具。最终我们实现全栈Reactive。

在我们的例子中，第一步先用 ```spring-boot-starter-web-reactive``` 替换 ```spring-boot-starter-web``` :

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

在controller中，不再使用 ```CompletableFuture``` 代之以返回一个 ```Mono``` :

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

将这段代码放到SpringBoot应用中，可以运行在 Tomcat, Jetty 或者 Netty, 取决于classpath引入了哪个包。Tomcat 是默认的容器，如果想用别的容器，需要把 Tomcat 从 classpath 中去掉，然后引入其它的容器。这3个容器在启动时间、内存使用和运行时资源上相差不大。

我们仍然调用 ```block()``` 阻塞服务接口，所以我们仍需在工作线程中订阅以免阻塞调用方。我们也可以采用一个非阻塞的客户端，例如用新的 ```WebClient``` 替换 ```RestTemplate``` :

``` java

private WebClient client = new WebClient(new ReactorHttpClientRequestFactory());

private Mono<HttpStatus> fetch(int value) {
    return this.client.perform(HttpRequestBuilders.get("http://example.com"))
            .extract(WebResponseExtractors.response(String.class))
            .map(response -> response.getStatusCode());
}

```

注意 ```WebClient.perform()``` 的返回值是一个转换为 ```Mono<HttpStatus>``` 的Reactive类型，但是我们没有订阅它。订阅的工作由框架来完成。

## 控制反转

现在我们去掉 ```fetch()``` 调用之后的并发参数：

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

1. 进行10次调用
2. 在新的publisher中并行处理

由于不再使用额外的订阅线程，相比于阻塞与Reactive桥接模式中的代码简洁了很多，现在是全面Reactive模式了。```WebClient``` 返回一个 ```Mono``` ，在然而然的我们需要在转换链中使用 ```flatMap()``` 。编写这种代码是一个很好的体验，易于理解便于维护。同时不再需要线程池和并发参数，也没有了影响性能的魔法数字4 。性能取决于系统资源而不是应用的线程控制。

应用可以运行在 Tomcat, Jetty 或 Netty 上. Tomcat 和 Jetty 的支持基于 Servlet 3.1 的异步处理，受限于一个请求一个线程。而运行在 Netty 上则没有这个限制。只要客户端不阻塞，会尽快的分发客户端请求。由于Netty服务不是一个请求一个线程，因此不会使用大量的线程。

> 注意，很多应用的阻塞调用不只是HTTP，还有数据库操作。当前很少的数据库支持非阻塞的客户端（除了 MongoDB 和 Couchbase）。线程池和 blocking-to-reactive 模式会长期存在。

## 仍然没有免费的午餐

首先，我们的代码是声明式的，不方便调试，错误发生时不容易定位。使用原生的API，例如不通过Spring框架而直接使用Reactor，会使情况变的更糟，因为我们自己要做很多的错误处理，每次进行网络调用都要写很多样板代码。通过组合使用 Spring 和 Reactor 我们可以方便的查看堆栈信息和未捕获的异常。由于运行的线程不受我们控制，因此在理解上会有困难。

其次，一旦编写错误导致一个Reactive回调被阻塞，在同一线程上的所有请求都会挂起。在servlet容器中，由于是一个请求一个线程，一个请求阻塞时，其它的请求不会受影响。而在Reactive中，一个请求被阻塞会导致所有请求的延迟都增加。

## 总结

在异步处理中能够控制所有的环节是非常好的：每一个层级都有线程池和队列。我们可以使一些层级具有弹性能力，可以根据负载动态调整。但是这也是一种负担，我们期望有更加简洁的方式。可扩展性的分析结果趋向于减少多余的线程，不要超出硬件资源的限制条件。

Reactive 不能解决所有问题的方案，事实上它本身不是一个方案，它只是促进了某一类问题的解决方案的产生。学习的成本、程序的调整、后续的维护成本可能远大于其所带来的益处。所以在是否使用 Reactive 这个问题上要非常谨慎。