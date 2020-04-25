---
layout: post
title:  "java并发编程"
date:   2020-4-12 21:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/java-concurrency.jpg
---

常用的java并发编程技术。

## 一、概述

传统的java并发能力依靠的是多线程，相比于现代的方法是Reactive编程，本文介绍多线程的实现，Reactive编程方法的介绍可参见[Reactive编程](https://springcamp.cn/spring-boot/reactive-program-1/)。

多线程并发编程有2个核心概念，原子性和可见性。原子性的介绍随处可见，简单来说就是一组操作要么全部成功，要么全部失败，不存在中间状态。

可见性是指一个线程中数据的变化是否能被其它线程感知。

多线程编程中要一直注意的一个问题点就是check-then-act的处理，我们的程序中存着大量的 条件判断->执行 的处理，这种简单的处理在单线程中不会存在什么问题，但是在多线程环境中却是极易出错。需要综合考虑原子性和可见性。“竞态条件”表述的就是这个问题。

本文主要介绍的内容：竞态条件、java内存模型（happens-before）、synchronized、原子类、锁、ThreadLocal变量、CountDownLatch、CompletableFuture。

<!-- more -->

## 二、竞态条件

当多个线程对共享资源进行处理的时候，可能由于不同的执行顺序导致产生不同的结果。比较典型的是check-then-act操作，如以下代码：

``` java
class Race {
  private Long value;
  Long get(){
    if( value == null ){
      value = initialize();
    }
    return value;
  }
}
```

当这个类的同一个对象在多个线程中执行get方法时，由于get方法不是原子操作，initialize方法可能会执行多次。解决这个问题可以通过将get方法改为synchronized方法或者是将value改为原子类。

再来看另外一种竞态条件。

``` java
class Waiter implements Runnable {
    private boolean shouldFinish;

    void finish() {
        shouldFinish = true;
    }

    public void run() {
        long iteration = 0;
        while (!shouldFinish) {
            iteration++;
        }

        System.out.println("Finished after: " + iteration);
    }
}
public class DataRace {

    public static void main(String[] args) throws InterruptedException {
        Waiter waiter = new Waiter();
        Thread waiterThread = new Thread(waiter);
        waiterThread.start();  // 在另一个的线程中执行waiter的run方法，该方法通过判断shouldFinish变量的值确定是否退出循环
        waiter.finish(); // 在主线程中修改shouldFinish变量的值
        waiterThread.join();
    }
}
```

正常情况下在执行完waiter的finish方法后，run方法中的循环会退出，但是也有可能run方法会进入死循环。我们可以通过延迟waiter.finish()的执行来模拟这种情况。将main方法做一下修改：

``` java
public class DataRace {

    public static void main(String[] args) throws InterruptedException {
        Waiter waiter = new Waiter();
        Thread waiterThread = new Thread(waiter);
        waiterThread.start();
        Thread.sleep(10L);  // 延迟10毫秒后再调用finish方法，会发现程序会一直运行不退出，在run方法中shouldFinish一直是false
        waiter.finish();
        waiterThread.join();
    }
}
```

再次执行这个程序，会发现run方法进入了死循环，即使waiter.finish()已经将shouldFinish设置成true，循环仍然没有退出。产生这个问题的原因就是在另一个的线程中读到的shouldFinish变量的值是脏数据。

可以通过将 ```shouldFinish``` 变量声明为 ```volatile``` 来解决这个问题。

这种现象是源于java内存模型的happens-before规则，一个线程对变量的写入操作的结果只有符合happens-before规则情况下才会被其它线程读取到。 该规则的描述如下（[原文](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html)）：

1. 程序的顺序性规则：一个线程中，按照程序的顺序，前面的操作happens-before后续的任何操作。

2. volatile规则：对一个volatile变量的写操作，happens-before后续对这个变量的读操作。

3. 锁规则：对一个锁的解锁操作，happens-before后续对这个锁的加锁操作。

4. 线程start()规则：主线程A启动线程B，线程B中可以看到主线程启动B之前的操作。也就是start() happens before 线程B中的操作。

5. 线程join()规则：主线程A等待子线程B完成，当子线程B执行完毕后，主线程A可以看到线程B的所有操作。也就是说，子线程B中的任意操作，happens-before join()的返回。

6. 传递性规则：如果A happens-before B，B happens-before C，那么A happens-before C。

所以将 ```shouldFinish``` 变量声明为 ```volatile```后，符合规则3，执行finish方法后对```shouldFinish```的修改会被读线程读取到修改后的结果。如果没有加```volatile```关键字，就没有符合happens-before规则。