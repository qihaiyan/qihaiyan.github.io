---
layout: post
title:  "spring并发编程CompletableFuture使用不当导致的死锁问题"
date:   2021-01-10 18:50:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/threadblock.jpg
---

Spring自带线程池使用很方便，不过在相对复杂的并发编程场景中，使用时还是需要根据使用场景仔细考虑配置，否则可能会遇到本文中提及的坑。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-taskexecutor-block](https://github.com/qihaiyan/springcamp/tree/master/spring-taskexecutor-block)

## 一、概述

spring自带线程池有2个核心配置，一个是线程池的大小，一个是队列的大小。
ThredPoolTaskExcutor的处理流程：
新建线程并处理请求，直到线程数大小等于corePoolSize
将请求放入workQueue中，线程池中的空闲线程去workQueue中取任务并处理
当workQueue满时，就新建线程并处理请求，当线程池子大小大小等于maximumPoolSize时，会用RejectedExecutionHandler来做拒绝处理

Reject策略有四种：
(1)AbortPolicy策略，是默认的策略，拒绝请求并抛出异常RejectedExecutionException。
(2)CallerRunsPolicy策略 ,由调用线程执行任务.
(3)DiscardPolicy策略，拒绝请求但不抛出异常.
(4)DiscardOldestPolicy策略，丢弃最早进入队列的任务.

<!-- more -->

## 二、多个异步处理共用同一个线程池的异常情况

模拟一个耗时的操作，该操作通过Async注解设置为异步执行。Async会默认使用名为taskExecutor的线程池。该操作返回一个CompletableFuture，后续的处理中会等待该异步操作执行完成。

``` java
@Service
public class DelayService {
    @Async
    public CompletableFuture<String> delayFoo(String v) {
        try {
            Thread.sleep(1000L);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        System.out.println(v + " runs in thread: " + Thread.currentThread().getName());
        return CompletableFuture.completedFuture(v);
    }
}
```

设置线程池，将线程池大小设置为2，队列设置为一个比线程池大的值，此处为10。当队列大小大于等于线程池大小时，就会出现本文遇到的程序阻塞的问题。

``` java
    @Bean
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(2);
        executor.setQueueCapacity(10);
        executor.setThreadNamePrefix("taskExecutor-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.initialize();
        return executor;
    }
}
```

并发处理：

``` java
    while (true) {
        try {
            CompletableFuture.runAsync(
                () -> CompletableFuture.allOf(Stream.of("1", "2", "3")
                .map(v -> delayService.delayFoo(v))
                .toArray(CompletableFuture[]::new)) // 将数组中的任务提交到线程池中
                .join(), taskExecutor); // 通过join方法等待任务完成
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
```

## 三、问题分析

程序启动后，很快就会阻塞，通过jstack查看线程状态，发现taskExecutor-1、taskExecutor-2、main三个线程都处在WAITING状态，等待CompletableFuture.join方法执行完成。

``` java
priority:5 - threadId:0x00007f7f8eb36800 - nativeId:0x3e03 - nativeId (decimal):15875 - state:WAITING
stackTrace:
java.lang.Thread.State: WAITING (parking)
at sun.misc.Unsafe.park(Native Method)
- parking to wait for <0x00000007961fe548> (a java.util.concurrent.CompletableFuture$Signaller)
at java.util.concurrent.locks.LockSupport.park(LockSupport.java:175)
at java.util.concurrent.CompletableFuture$Signaller.block(CompletableFuture.java:1693)
at java.util.concurrent.ForkJoinPool.managedBlock(ForkJoinPool.java:3323)
at java.util.concurrent.CompletableFuture.waitingGet(CompletableFuture.java:1729)
at java.util.concurrent.CompletableFuture.join(CompletableFuture.java:1934)
```

通过分析程序的执行过程，不难发现阻塞的原因。CompletableFuture.join方法用于无法执行完成。
由于线程池设置的Queue的大小大于线程池的大小，当线程池满时，delayFoo方法会处在队列中，随着程序的执行，总会出现线程池中都是CompletableFuture.join方法，队列中都是delayFoo方法的情况。
这时候线程中的join方法在等待队列中的delayFoo方法执行完成，而队列中的delayFoo方法由于等不到可用线程，又没办法正常执行，整个程序就陷入了死锁状态。

解决的方法也很简单，就是将队列的大小设置为小于线程数的大小，这样队列中的方法就有机会拿到线程，从而不会因为线程占满而进入死锁状态。
