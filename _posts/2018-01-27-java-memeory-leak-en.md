---
layout: post
title:  "How to Avoid Memory Leaks in Java Programs"
date:   2018-1-27 19:28:00 +0800
lang: en
slug_zh: java-memeory-leak
tags: [java]
categories: [java]
image: assets/images/memoryleak.png
description: "Common causes of Java memory leaks and how to avoid them: static references, String.intern(), unclosed streams, and HashSet misuse, plus how to find them."
---
Although the JVM has garbage collection, Java programs can still leak memory if the code does not follow certain rules, eventually leading to an OutOfMemory error.

### 1. Causes of Java Memory Leaks

Objects in Java come in two kinds with respect to usage: referenced and unreferenced. Garbage collection only reclaims unreferenced objects. A referenced object is never collected, even if it is no longer used. Therefore, when a program holds a large number of referenced but useless objects, a memory leak occurs.

### 2. Java Heap Memory Leaks

The size of the JVM heap is controlled by the -Xms and -Xmx parameters.

#### 2.1 Objects Referenced by Static Fields

Memory leaks occur when large objects are referenced by static fields.

Example:

```java
private Random random = new Random();

public static final ArrayList<Double> list = new ArrayList<Double>(1000000);

for (int i = 0; i < 1000000; i++) { list.add(random.nextDouble()); }
```

An ArrayList is dynamically allocated on the heap; normally it is collected by the GC once it is no longer used. In this example, however, it is referenced by the static field list, and static fields are never collected, so this huge ArrayList stays in heap memory forever.

So pay special attention to how static fields are used: avoid having static fields reference large objects or collections (such as ArrayList).

<!-- more -->

#### 2.2 The String.intern() Method

Calling String.intern() on a large string puts the string into the JVM's memory pool (PermGen), which is never garbage collected. So if large strings are interned, a large amount of uncollectable memory is produced, causing a memory leak.

If you must intern large strings, adjust the size of PermGen with the -XX:MaxPermSize parameter.

### 2.3 Streams Not Closed After Reading

Forgetting to close streams is a common development mistake that leads to memory leaks. Every stream corresponds to an open file handle at the OS level; if the stream is not closed, the operating system's file handle stays open, and the JVM consumes memory to keep track of the file handles opened by the operating system.
Example:

```java
BufferedReader br = new BufferedReader(new FileReader(path));
return br.readLine();
```

To fix this, in versions before Java 8 you can add the close operation in a finally block:

```java
 BufferedReader br = new BufferedReader(new FileReader(path));
    try {
        return br.readLine();
    } finally {
        if (br != null) br.close();
    }
```

In Java 8 you can use the try-with-resources statement:

```java
try (BufferedReader br = new BufferedReader(new FileReader(path))) {
    return br.readLine();
}
```

Be careful to close network connections and database connections as well. If a connection pool is used, closing is handled by the pool, and the application code does not need to deal with it.

#### 2.4 Adding Objects Without hashCode() and equals() to a HashSet

This is a simple but very common scenario. Normally a Set filters out duplicate objects, but without hashCode() and equals() implementations, duplicates keep being added to the Set and never get a chance to be removed.

So implementing hashCode() and equals() for your classes is a good programming habit. Lombok's @EqualsAndHashCode makes this very convenient.

### 3. How to Find Memory Leaks

#### 3.1 Enable GC Logging

By specifying -verbose:gc in the JVM parameters, you can record the details of every GC run and use them to analyze memory usage.

#### 3.2 Profiling

Analyze memory with Visual VM or the JDK's built-in Java Mission Control.

#### 3.3 Code Review

Use code reviews and static code analysis to find faulty code that causes memory leaks.

### 4. Summary

Code-level checks can help uncover some memory leaks, but leaks in production are often hard to detect in advance, because many problems only appear under heavy concurrency. That is why you should also run load tests with stress-testing tools to surface potential memory leaks early.
