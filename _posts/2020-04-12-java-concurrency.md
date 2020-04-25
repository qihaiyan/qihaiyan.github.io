---
layout: post
title:  "java并发编程"
date:   2020-4-12 21:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/java-concurrency.jpg
---

常用的java并发编程技术。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-currency](https://github.com/qihaiyan/springcamp/tree/master/spring-currency)

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

这种现象是源于java内存模型的happens-before规则，一个线程对变量的写入操作的结果只有符合happens-before规则情况下才会被其它线程读取到。 ```synchronized```和```volatile```结构，以及```Thread.start()```和```Thread.join()```方法均可构成happens-before关系。该规则的描述如下（[原文](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html)）：

1. 程序的顺序性规则：一个线程中，按照程序的顺序，前面的操作happens-before后续的任何操作。

2. volatile规则：对一个volatile变量的写操作，happens-before后续对这个变量的读操作。

3. 锁规则：对一个锁的解锁操作，happens-before后续对这个锁的加锁操作。

4. 线程start()规则：主线程A启动线程B，线程B中可以看到主线程启动B之前的操作。也就是start() happens before 线程B中的操作。

5. 线程join()规则：主线程A等待子线程B完成，当子线程B执行完毕后，主线程A可以看到线程B的所有操作。也就是说，子线程B中的任意操作，happens-before join()的返回。

6. 传递性规则：如果A happens-before B，B happens-before C，那么A happens-before C。

所以将 ```shouldFinish``` 变量声明为 ```volatile```后，符合规则3，执行finish方法后对```shouldFinish```的修改会被读线程读取到修改后的结果。如果没有加```volatile```关键字，就没有符合happens-before规则。

## 三、synchronized

```synchronized``` 提供了一种悲观锁机制，synchronized声明的代码块具有排他性，同一时间只有一个线程能够获得锁，通过这种方式确保原子性和可见性。synchronized可以用在方法上，也可以用在一段代码块上。当synchronized可以用在static方法上时，用的是类锁，否则是对象锁。

对代码块枷锁：

```java
class SynchronizedBlock {
    private int counter0;

    void increment() {
        synchronized (this) {
            counter0++;
        }
    }
}
```

对方法枷锁：

```java
class SynchronizedMethod {
    private int counter0;

    synchronized void increment() {
        counter0++;
    }
}
```

## 四、ThreadLocal

虽然通过```synchronized```可以实现原子性，但是由于使用的是悲观锁机制，对性能会有影响。如果多个线程之间的变量不需要共享，可以采用```ThreadLocal```变量，避免多个线程同时修改同一个变量导致出现并发问题。

```java
class ThreadLocalDemo {
    private final ThreadLocal<Transaction> currentTransaction = ThreadLocal.withInitial(NullTransaction::new);

    Transaction currentTransaction() {
        Transaction current = currentTransaction.get();
        if (current.isNull()) {
            current = new TransactionImpl();
            currentTransaction.set(current);
        }
        return current;
    }
}

interface Transaction {
    boolean isNull();
}

class NullTransaction implements Transaction {
    public boolean isNull() {
        return true;
    }
}

class TransactionImpl implements Transaction {
    public boolean isNull() {
        return false;
    }
}
```

## 五、Atomics

另外一种简化并发编程的方式是采用原子数据结构，这种数据结构本身保证了原子性和可见性，可以方便的使用，能够避免多线程环境下check-then-act的问题。

```java
public class Atomic {

    public static void main(String[] args) {
        AtomicRun atomicRun = new AtomicRun();
        Thread waiterThread1 = new Thread(atomicRun);
        Thread waiterThread2 = new Thread(atomicRun);
        waiterThread1.start();
        waiterThread2.start();
    }
}

class AtomicRun implements Runnable {
    private final AtomicBoolean shouldFinish = new AtomicBoolean(false);

    public void run() {
        if (shouldFinish.compareAndSet(false, true)) {
            System.out.println("initialized only once");
        }
    }
}
```

由于shouldFinish是一个原子对象，shouldFinish.compareAndSet是一个原子操作，因此不会出现读取到脏数据的问题。

## 六、Locks

java.util.concurrent.locks包提供了与```synchronized```相同的功能，在此基础上又进行了扩展，例如可以获取锁的状态，可以中断锁。对于读多写少的情况，还可以通过ReadWriteLock来提升性能。

```java
class LockDemo {
    private final Lock lock = new ReentrantLock();
    private int counter0;

    public static void main(String[] args) {
        LockDemo lockDemo = new LockDemo();
        lockDemo.increment();
        System.out.println("count is: " + lockDemo.getCounter0());
    }

    public int getCounter0() {
        return counter0;
    }

    void increment() {
        lock.lock();
        try {
            counter0++;
        } finally {
            lock.unlock();
        }

    }
}

class ReadWriteLockDemo {
    private final ReadWriteLock lock = new ReentrantReadWriteLock();
    private int counter1;

    void increment() {
        lock.writeLock().lock();
        try {
            counter1++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    int current() {
        lock.readLock().lock();
        try {
            return counter1;
        } finally {
            lock.readLock().unlock();
        }
    }
}
```

在使用locks时，要注意一定要在finally方法中执行unlock操作，因为程序出现异常后，不会自动释放锁，如果不在finally方法中执行unlock，会导致程序进入死锁状态。

## 七、CountDownLatch

CountDownLatch一般用于同步多个线程的执行进度，例如有一个线程需要等其它三个线程执行完成后，再继续往下执行，可以用CountDownLatch来处理。

CountDownLatch类似于一个计数器，当一个线程调用CountDownLatch的await方法时会进入阻塞状态，其它线程调用countDown方法对计数器减一，当计数器减为0时，被await方法阻塞的操作才会解除阻塞状态继续执行。

```java
public class CountDownLatchDemo {
    public static void main(String[] args) throws InterruptedException {
        ExecutorService executorService = Executors.newFixedThreadPool(2);

        CountDownLatch latch = new CountDownLatch(1);
        Receiver receiver = new Receiver(latch);
        executorService.submit(receiver);
        latch.await();
        System.out.println("latch done");
        executorService.shutdown();
    }
}

class Receiver implements Runnable {

    private CountDownLatch latch;

    public Receiver(CountDownLatch latch) {
        this.latch = latch;
    }

    public void run() {
        latch.countDown();
    }
}
```

## 八、CompletableFuture

CompletableFuture是一种java8提供的常用的多线程并发编程方法，虽然parallelStream也提供了多线程并发能力，但是在选择上要遵循一个原则：有IO操作的用CompletableFuture，没有IO操作纯计算的用parallelStream。

原因在于parallelStream使用的是jvm的默认ForkJoinPool线程池，该线程池一般只会分配很少的线程数（默认是CPU的核数），不能指定其它线程池。当有IO操作或者类似的延迟较高的操作时，很容易把线程池占满。而CompletableFuture允许指定线程池，可以为不同的处理指定不同的线程池，能够分业务进行线程池的隔离。

首先我们模拟一个延迟IO方法，用于后续的演示：

```java
public static Long getPrice(String prod) {
        delay();  //模拟服务响应的延迟
        Long price = ThreadLocalRandom.current().nextLong(0, 1000);
        System.out.println("Executing in " + Thread.currentThread().getName() + ", get price for " + prod + " is " + price);
        return price;
    }

    private static void delay() {
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
```

1. supplyAsync：该方法用于创建一个异步任务

```java
ExecutorService executor = Executors.newFixedThreadPool(10);

CompletableFuture<Long> future = CompletableFuture.supplyAsync(() -> getPrice("accept"), executor);
```

supplyAsync是一个工厂方法，该方法会返回一个CompletableFuture对象，入参是 Supplier 或者 Runnable 的实现类，可以用Lambda表达式来表示。同时指定了executor作为执行用的线程池。

2. thenAcceptAsync：该方法接收CompletableFuture的执行结果，将结果作为输入执行指定的方法

```java
future.thenAccept(p -> {
            System.out.println("Executing in " + Thread.currentThread().getName() + ", async price is: " + p);
        }, executor);
```

将第一步中的返回结果（getPrice的返回值）作为输入执行操作。

3. thenApply：该方法接收CompletableFuture的执行结果进行计算，返回一个新的CompletableFuture，类似于stream的map操作。

```java
CompletableFuture<String> result = future.thenApply(p -> p + "1");
```

该步操作将第一步中的```CompletableFuture<Long>``` 转换为了 ```CompletableFuture<String>```。

4. thenCompose：用于组合2个CompletableFuture，第一个的计算结果作为第二个的输入。

```java
CompletableFuture<Long> future1 = CompletableFuture
                .supplyAsync(() -> getPrice("compose"));
CompletableFuture<String> result = future1.thenCompose(
    i -> CompletableFuture.supplyAsync(() -> {
        Thread.sleep(2000);
        return i + "World";
    })
);
```

5. thenCombine： 将两个CompletableFuture的计算结果做进一步的计算

```java
CompletableFuture<Long> future1 = CompletableFuture.supplyAsync(() -> getPrice("combine1"));
CompletableFuture<Long> future2 = CompletableFuture.supplyAsync(() -> getPrice("combine2"));
CompletableFuture<Long> result = future1.thenCombine(future2, (f1, f2) -> f1 + f2);
```

这段代码会在future1和future2都计算完成后，把两个future的计算结果进行相加，返回新的CompletableFuture。

6. exceptionally： 异常处理

exceptionally是CompletableFuture最简便的一种异常处理方法。该方法会在异常发生后返回一个默认值。

```java
CompletableFuture<Long> future1 = CompletableFuture.supplyAsync(() -> getPrice("exception1"));

CompletableFuture<Long> future2 = CompletableFuture
                .supplyAsync(() -> (1L / 0) ) //模拟抛出一个异常
                // 出现异常时返回默认值，如果此处没有exceptionally处理，异常会在后续的join中抛出
                .exceptionally((ex) -> {
                    System.out.println("Executing in " + Thread.currentThread().getName() + ", get excetion " + ex);
                    return 0L;
                });

CompletableFuture<Long> result = future1.thenCombine(future2, (f1, f2) -> f1 + f2);

try {
            System.out.println("Executing in " + Thread.currentThread().getName() + " ,combine price is: " + result.join());
} catch (CompletionException ex) {
            System.out.println("Executing in " + Thread.currentThread().getName() + " ,combine price error: " + ex);
}
```

7. 并行执行CompletableFuture

假设我们有一个数组，数组中的每一项都需要调用getPrice方法获取价格，可以采用stream和CompletableFuture组合使用的方式。

```java
List<Long> prices = Stream.of("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12")
                .map(p -> CompletableFuture.supplyAsync(() -> getPrice("exception1"), executor)) //通过stream的map操作，为数组中的每一个元素都启动一个CompletableFuture
                .collect(Collectors.toList())
                .stream()
                .map(CompletableFuture::join) //等待所有的CompletableFuture都完成计算
                .collect(Collectors.toList());
```

注意这儿要有两段collect处理，不能简化为以下写法：

```java
ist<Long> prices2 = Stream.of("1", "2", "3")
                .map(p -> CompletableFuture.supplyAsync(() -> getPrice("exception1")))
                .map(CompletableFuture::join)
                .collect(Collectors.toList());
```

这样写看上去更简洁，但是存在严重的问题。因为对于每一个元素，在第一个map生成CompletableFuture后，会立即执行join阻塞操作，相当于变成了串行。
