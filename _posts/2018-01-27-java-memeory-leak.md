---
layout: post
title:  "如何避免java程序内存泄漏"
date:   2018-1-27 19:28:00 +0800
tags: [java]
categories: [java]
image: assets/images/memoryleak.png
---
虽然jvm有垃圾回收机制，如果程序编写不注意某些特定规则，仍然会导致java程序内存泄漏，最终可能出现OutOfMemory异常。

### 1.Java内存泄漏的原因

java中的对象从使用上分为2种类型，被引用（referenced）的和不被引用（unreferenced）的。垃圾回收只会回收不被引用的对象。被引用的对象，即使已经不再使用了，也不会被回收。因此如果程序中有大量的被引用的无用对象时，就是出现内存泄漏。

### 2.java堆内存（Heap）泄漏

jvm堆内存的大小是通过 -Xms 和 -Xmx两个参数指定的。

#### 2.1 对象被静态成员引用

当大对象被静态成员引用时，会造成内存泄漏。

示例：

```java
private Random random = new Random();

public static final ArrayList<Double> list = new ArrayList<Double>(1000000);

for (int i = 0; i < 1000000; i++) { list.add(random.nextDouble()); }
```

 ArrayList是在堆上动态分配的对象，正常情况下使用完毕后，会被gc回收，但是在此示例中，由于被静态成员list引用，而静态成员是不会被回收的，所以会导致这个很大的ArrayList一直停留在堆内存中。

因此需要特别注意静态成员的使用方式，避免静态成员引用大对象或集合类型的对象（如ArrayList等）。

<!-- more -->

#### 2.2 String的intern方法

在大字符串上调用String.intern() 方法，intern()会将String放在jvm的内存池中（PermGen ），而jvm的内存池是不会被gc的。因此如果大字符串调用intern()方法后，会产生大量的无法gc的内存，导致内存泄漏。

如果必须要使用大字符串的intern方法，应该通过-XX:MaxPermSize参数调整PermGen内存的大小。

### 2.3 读取流后没有关闭

开发中经常忘记关闭流，这样会导致内存泄漏。因为每个流在操作系统层面都对应了打开的文件句柄，流没有关闭，会导致操作系统的文件句柄一直处于打开状态，而jvm会消耗内存来跟踪操作系统打开的文件句柄。
示例：

```java
BufferedReader br = new BufferedReader(new FileReader(path));
return br.readLine();
```

要解决这个问题，在java8之前的版本中可以在finally中加入关闭操作：

```java
 BufferedReader br = new BufferedReader(new FileReader(path));
    try {
        return br.readLine();
    } finally {
        if (br != null) br.close();
    }
```

java8中可以使用try-with-resources语句：

```java
try (BufferedReader br = new BufferedReader(new FileReader(path))) {
    return br.readLine();
}
```

对于网络连接和数据库连接等也要注意连接的关闭，如果采用了连接池，那关闭操作是由连接池负责的，程序中可以不用处理。

#### 2.4 将没有实现hashCode()和equals()方法的对象加入到HashSet中

这是一个简单却很常见的场景。正常情况下Set会过滤重复的对象，但是如果没有hashCode() 和 equals()实现，重复对象会不断被加入到Set中，并且再也没有机会去移除。

因此给类都加上hashCode() 和 equals()方法的实现是一个好的编程习惯。可以通过Lombok的@EqualsAndHashCode很方便实现这种功能。

### 3. 查找内存泄漏的方法

#### 3.1 记录gc日志

通过在jvm参数中指定-verbose:gc，可以记录每次gc的详细情况，用于分析内存的使用。

#### 3.2 进行profiling

通过Visual VM或jdk自带的Java Mission Control，进行内存分析。

#### 3.3 代码审查

通过代码审查和静态代码检查，发现导致内存泄漏问题的错误代码。

### 4. 总结

代码层面的检查可以帮助发现部分内存泄漏的问题，但是生产环境中的内存泄漏往往不容易提前发现，因为很多问题是在大并发场景下才会出现。因此还需要通过压力测试工具进行压力测试，提前发现潜在的内存泄漏问题。
