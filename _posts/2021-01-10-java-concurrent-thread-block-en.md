---
layout: post
title:  "Deadlock Caused by Misusing Spring's Built-in Thread Pool"
date:   2021-01-10 18:50:00 +0800
lang: en
slug_zh: java-concurrent-thread-block
tags: [spring,java]
categories: [spring boot]
image: assets/images/threadblock.jpg
description: "How misuse of Spring's built-in ThreadPoolTaskExecutor can block requests: core settings, queue sizing and rejection policy pitfalls explained."
---

Spring's built-in thread pool is very convenient to use, but in relatively complex concurrency scenarios you still need to think carefully about the configuration for your use case, otherwise you may run into the pitfalls described in this post.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-taskexecutor-block](https://github.com/qihaiyan/springcamp/tree/main/spring-taskexecutor-block).

## 1. Overview

Spring's built-in thread pool has 2 core settings: the size of the thread pool, and the size of the queue.
The processing flow of ThreadPoolTaskExecutor:
Create new threads and process requests until the number of threads equals corePoolSize;
Put requests into the workQueue, where idle threads in the pool pick up tasks from the workQueue and process them;
When the workQueue is full, create new threads to process requests; when the pool size reaches maximumPoolSize, the RejectedExecutionHandler is used to reject the request.

There are four rejection policies:

(1) AbortPolicy: the default policy; the request is rejected and a RejectedExecutionException is thrown.

(2) CallerRunsPolicy: the task is executed by the calling thread.

(3) DiscardPolicy: the request is rejected but no exception is thrown.

(4) DiscardOldestPolicy: the task that entered the queue earliest is discarded.

<!-- more -->

## 2. Problems When Multiple Async Operations Share One Thread Pool

We simulate a time-consuming operation that is executed asynchronously via the Async annotation. By default, Async uses the thread pool named taskExecutor. The operation returns a CompletableFuture, and the subsequent processing waits for this async operation to complete.

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

Configure the thread pool with a pool size of 2, and a queue larger than the pool — 10 here. When the queue size is greater than or equal to the pool size, the program blocking problem described in this post occurs.

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

Concurrent processing:

``` java
    while (true) {
        try {
            CompletableFuture.runAsync(
                () -> CompletableFuture.allOf(Stream.of("1", "2", "3")
                .map(v -> delayService.delayFoo(v))
                .toArray(CompletableFuture[]::new)) // submit the tasks in the array to the thread pool
                .join(), taskExecutor); // wait for the tasks to complete via the join method
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
```

## 3. Problem Analysis

After the application starts, it blocks quickly. Checking the thread states with jstack shows that the three threads taskExecutor-1, taskExecutor-2, and main are all in the WAITING state, waiting for the CompletableFuture.join method to complete.

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

By analyzing the execution flow of the program, the cause of the blocking is not hard to find.
Because the queue size is configured larger than the pool size, when the pool is full the delayFoo method sits in the queue. As the program keeps running, a situation will inevitably arise where the pool contains only CompletableFuture.join calls while the queue contains only delayFoo calls.

At that point, the join calls occupying the threads are waiting for the delayFoo methods in the queue to finish, while the delayFoo methods in the queue cannot run because no thread is available. The whole program falls into a deadlock.

The fix is also simple: set the queue size smaller than the number of threads, so that the methods waiting in the queue have a chance to get a thread, and the program will no longer deadlock from all threads being occupied.
