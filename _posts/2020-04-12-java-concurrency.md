---
layout: post
title:  "java并发编程"
date:   2020-4-12 21:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/java-concurrency.jpg
---

常用的java并发编程技术。

## 概述

传统的java并发能力依靠的是多线程，相比于现代的方法是Reactive编程，本文介绍多线程的实现，Reactive编程方法的介绍可参见[Reactive编程](https://springcamp.cn/spring-boot/reactive-program-1/)。

多线程并发编程有2个核心概念，原子性和可见性。原子性的介绍随处可见，简单来说就是一组操作要么全部成功，要么全部失败，不存在中间状态。

可见性是指一个线程中数据的变化是否能被其它线程感知。

多线程编程中要一直注意的一个问题点就是check-then-act的处理，我们的程序中存着大量的 条件判断->执行 的处理，这种简单的处理在单线程中不会存在什么问题，但是在多线程环境中却是极易出错。需要综合考虑原子性和可见性。“竞态条件”表述的就是这个问题。

本文主要介绍的内容：数据竞争、java内存模型（happens-before）、synchronized、原子类、锁、ThreadLocal变量、CountDownLatch、CompletableFuture。

<!-- more -->

待续。。。