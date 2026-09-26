---
layout: post
title:  "Java Concurrency Programming: Multithreading, Atomicity, and Visibility"
date:   2020-4-12 21:30:00 +0800
lang: en
slug_zh: java-concurrency
tags: [spring,java]
categories: [spring boot]
image: assets/images/java-concurrency.jpg
description: "A practical guide to Java multithreading: race conditions, happens-before, synchronized, atomics, locks, ThreadLocal, CountDownLatch, and CompletableFuture."
---

Commonly used Java concurrency programming techniques.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-currency](https://github.com/qihaiyan/springcamp/tree/main/spring-currency).

## 1. Overview

Traditional Java concurrency relies on multithreading, while the modern alternative is Reactive programming. This article covers the multithreading approach; for an introduction to Reactive programming, see [Reactive Programming](https://springcamp.cn/reactive-program-1/).

Multithreaded concurrent programming has two core concepts: atomicity and visibility. Atomicity is discussed everywhere; put simply, a group of operations either all succeed or all fail, with no intermediate state.

Visibility refers to whether a change made to data by one thread can be perceived by other threads.

One issue that requires constant attention in multithreaded programming is check-then-act handling. Our programs are full of "check condition -> act" operations. This simple pattern causes no problems in single-threaded code, but it is extremely error-prone in a multithreaded environment and requires careful consideration of both atomicity and visibility. The term "race condition" describes exactly this problem.

This article covers: race conditions, the Java memory model (happens-before), synchronized, atomic classes, locks, ThreadLocal variables, CountDownLatch, and CompletableFuture.

<!-- more -->

## 2. Race Conditions

When multiple threads operate on a shared resource, different execution orders may produce different results. A typical case is the check-then-act operation, as in the following code:

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

When the same instance of this class has its get method executed by multiple threads, get is not an atomic operation, so initialize may be executed multiple times. This can be fixed by making get a synchronized method or by changing value to an atomic class.

Now let's look at another kind of race condition.

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
        waiterThread.start();  // run waiter's run method in another thread; the method checks the value of shouldFinish to decide whether to exit the loop
        waiter.finish(); // modify the value of shouldFinish in the main thread
        waiterThread.join();
    }
}
```

Normally, after waiter's finish method has executed, the loop in run exits. However, it is also possible for run to get stuck in an infinite loop. We can simulate this by delaying the execution of waiter.finish(). Modify the main method as follows:

``` java
public class DataRace {

    public static void main(String[] args) throws InterruptedException {
        Waiter waiter = new Waiter();
        Thread waiterThread = new Thread(waiter);
        waiterThread.start();
        Thread.sleep(10L);  // call finish after a 10 ms delay; the program then keeps running and never exits, because shouldFinish is always false inside run
        waiter.finish();
        waiterThread.join();
    }
}
```

Running the program again, you will find that run is stuck in an infinite loop: even though waiter.finish() has set shouldFinish to true, the loop still does not exit. The cause of this problem is that the value of shouldFinish read by the other thread is stale data.

This can be fixed by declaring the ```shouldFinish``` variable as ```volatile```.

This phenomenon stems from the happens-before rules of the Java memory model: the result of one thread's write to a variable is guaranteed to be visible to other threads only when a happens-before relationship holds. The ```synchronized``` and ```volatile``` constructs, as well as the ```Thread.start()``` and ```Thread.join()``` methods, all establish happens-before relationships. The rules are described as follows ([original text](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/package-summary.html)):

1. Program order rule: within a single thread, every action happens-before any subsequent action in that thread, in program order.

2. Volatile rule: a write to a volatile variable happens-before every subsequent read of that variable.

3. Monitor lock rule: an unlock of a lock happens-before every subsequent lock on that same lock.

4. Thread start() rule: when thread A starts thread B, everything thread A did before starting B is visible to B; in other words, start() happens-before any action in thread B.

5. Thread join() rule: when thread A waits for child thread B to complete, once B finishes, thread A can see all of B's actions; in other words, any action in thread B happens-before the return of join().

6. Transitivity rule: if A happens-before B and B happens-before C, then A happens-before C.

So once the ```shouldFinish``` variable is declared ```volatile```, rule 2 applies, and the change to ```shouldFinish``` made by the finish method is read by the reading thread as the updated value. Without the ```volatile``` keyword, no happens-before relationship exists.

## 3. synchronized

```synchronized``` provides a pessimistic locking mechanism. Code declared with synchronized is exclusive: only one thread can hold the lock at a time, which guarantees both atomicity and visibility. synchronized can be applied to a method or to a block of code. When applied to a static method, the class lock is used; otherwise the object lock is used.

Locking a code block:

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

Locking a method:

```java
class SynchronizedMethod {
    private int counter0;

    synchronized void increment() {
        counter0++;
    }
}
```

## 4. ThreadLocal

Although ```synchronized``` achieves atomicity, it relies on a pessimistic locking mechanism, which has a performance cost. If variables do not need to be shared between threads, you can use ```ThreadLocal``` variables to avoid concurrency problems caused by multiple threads modifying the same variable at the same time.

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

## 5. Atomics

Another way to simplify concurrent programming is to use atomic data structures. These structures guarantee atomicity and visibility by themselves, are convenient to use, and can prevent the check-then-act problem in multithreaded environments.

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

Since shouldFinish is an atomic object, shouldFinish.compareAndSet is an atomic operation, so the problem of reading stale data never occurs.

## 6. Locks

The java.util.concurrent.locks package provides the same functionality as ```synchronized``` and builds on it — for example, you can inspect a lock's state and interrupt lock acquisition. For workloads with many reads and few writes, ReadWriteLock can further improve performance.

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

When using locks, always perform the unlock operation in a finally block: if the program throws an exception, the lock is not released automatically, and failing to unlock in a finally block can leave the program deadlocked.

## 7. CountDownLatch

CountDownLatch is typically used to synchronize the execution progress of multiple threads. For example, when one thread needs to wait for three other threads to finish before continuing, CountDownLatch is a good fit.

CountDownLatch works like a counter. When a thread calls the CountDownLatch's await method it enters a blocked state; other threads call countDown to decrement the counter. Only when the counter reaches 0 does the operation blocked by await resume execution.

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

## 8. CompletableFuture

CompletableFuture is a commonly used multithreaded concurrency mechanism provided by Java 8. Although parallelStream also offers multithreaded concurrency, the rule of thumb for choosing between them is: use CompletableFuture when there are IO operations, and use parallelStream for pure computation without IO.

The reason is that parallelStream uses the JVM's default ForkJoinPool, which typically allocates only a small number of threads (by default the number of CPU cores), and you cannot substitute a different thread pool. With IO operations or other high-latency work, the pool is easily exhausted. CompletableFuture, on the other hand, allows you to specify the thread pool — you can assign different pools to different kinds of processing, isolating thread pools by business domain.

First, let's simulate an IO method with a delay for the demonstrations that follow:

```java
public static Long getPrice(String prod) {
        delay();  // simulate the latency of a service call
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

### 1. supplyAsync: creates an asynchronous task

```java
ExecutorService executor = Executors.newFixedThreadPool(10);

CompletableFuture<Long> future = CompletableFuture.supplyAsync(() -> getPrice("accept"), executor);
```

supplyAsync is a factory method that returns a CompletableFuture. Its arguments are an implementation of Supplier or Runnable, which can be expressed as a lambda expression, and it also specifies the executor as the thread pool used for execution.

### 2. thenAcceptAsync: takes the result of a CompletableFuture as input and runs the specified method on it

```java
future.thenAccept(p -> {
            System.out.println("Executing in " + Thread.currentThread().getName() + ", async price is: " + p);
        }, executor);
```

It takes the result produced in the first step (the value returned by getPrice) as input and executes the operation.

### 3. thenApply: takes the result of a CompletableFuture, computes on it, and returns a new CompletableFuture, similar to a stream's map operation.

```java
CompletableFuture<String> result = future.thenApply(p -> p + "1");
```

This step converts the ```CompletableFuture<Long>``` from the first step into a ```CompletableFuture<String>```.

### 4. thenCompose: combines two CompletableFutures, with the first one's result as the input to the second.

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

### 5. thenCombine: performs further computation on the results of two CompletableFutures

```java
CompletableFuture<Long> future1 = CompletableFuture.supplyAsync(() -> getPrice("combine1"));
CompletableFuture<Long> future2 = CompletableFuture.supplyAsync(() -> getPrice("combine2"));
CompletableFuture<Long> result = future1.thenCombine(future2, (f1, f2) -> f1 + f2);
```

Once both future1 and future2 have finished computing, this code adds the results of the two futures together and returns a new CompletableFuture.

### 6. exceptionally: exception handling

exceptionally is the simplest way to handle exceptions in a CompletableFuture. When an exception occurs, the method returns a default value.

```java
CompletableFuture<Long> future1 = CompletableFuture.supplyAsync(() -> getPrice("exception1"));

CompletableFuture<Long> future2 = CompletableFuture
                .supplyAsync(() -> (1L / 0) ) // simulate throwing an exception
                // return a default value when an exception occurs; without exceptionally here, the exception would be thrown by the later join call
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

### 7. Executing CompletableFutures in Parallel

Suppose we have an array in which every item requires a call to getPrice to fetch its price. We can combine a stream with CompletableFuture.

```java
List<Long> prices = Stream.of("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12")
                .map(p -> CompletableFuture.supplyAsync(() -> getPrice("exception1"), executor)) // use the stream's map operation to start a CompletableFuture for every element
                .collect(Collectors.toList())
                .stream()
                .map(CompletableFuture::join) // wait for all CompletableFutures to finish computing
                .collect(Collectors.toList());
```

Note that two collect operations are required here; it cannot be simplified to the following:

```java
ist<Long> prices2 = Stream.of("1", "2", "3")
                .map(p -> CompletableFuture.supplyAsync(() -> getPrice("exception1")))
                .map(CompletableFuture::join)
                .collect(Collectors.toList());
```

This looks more concise, but it has a serious flaw: for each element, join — a blocking operation — executes immediately after the first map creates the CompletableFuture, effectively turning the whole thing into sequential execution.
