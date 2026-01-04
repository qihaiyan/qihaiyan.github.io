---
layout: post
title:  "Spring RestTemplate配置DNS解析超时"
date:   2024-06-16 15:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/dns-timeout.jpg
---

RestTemplate 常用的超时设置方法可以设置连接超时、接口请求超时、接口响应超时，但是对于DNS解析超时往往没有简单的方法可以设置。本文介绍设置DNS解析超时时间的方法，具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log)

## 一、概述

在spring中使用RestTemplate调用远程接口时往往需要设置超时时间，否则当对方接口过慢时，很容易把自己系统堵死。连接超时、发送请求超时、接收响应超时都有直接的方法可以进行调用设置，设置DNS解析超时需要通过相对复杂的方法进行处理。

## 二、自定义 CustomDnsResolver

首先RestTemplate配置使用apache httpclient进行http接口调用，apache httpclient内部通过默认的DnsResolver进行DNS解析，我们可以通过自己实现DnsResolver方法来设置DNS解析超时时间。

以下代码为自定义 CustomDnsResolver 实现 DnsResolver。

``` java
public static class CustomDnsResolver implements DnsResolver {

        private final DnsResolver systemDnsResolver;
        private final Integer connectTimeout;

        public CustomDnsResolver(Integer connectTimeout) {
            this.systemDnsResolver = SystemDefaultDnsResolver.INSTANCE;
            this.connectTimeout = connectTimeout;
        }

        @Override
        public InetAddress[] resolve(final String host) {
            try {
                return CompletableFuture.supplyAsync(() -> {
                    try {
                        return systemDnsResolver.resolve(host);
                    } catch (UnknownHostException e) {
                        throw new RuntimeException(e);
                    }
                }).get(connectTimeout, TimeUnit.SECONDS);
            } catch (InterruptedException | ExecutionException | TimeoutException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public String resolveCanonicalHostname(String host) throws UnknownHostException {
            return systemDnsResolver.resolveCanonicalHostname(host);
        }
    }
```

DNS解析的方法为resolve，我们resolve方法中通过CompletableFuture.supplyAsync调用系统的DNS解析方法，然后通过CompletableFuture.get方法进行超时控制。

## 三、配置apache httpclient使用自定义的CustomDnsResolver

PoolingHttpClientConnectionManager常用的构造方法只有一个Registry参数，该方法无法指定自定义 DnsResolver ，所以我们需要改用支持指定DnsResolver的构造方法。

```java
    PoolingHttpClientConnectionManager poolingConnectionManager = new PoolingHttpClientConnectionManager(
                registry,
                PoolConcurrencyPolicy.STRICT,
                PoolReusePolicy.LIFO,
                TimeValue.NEG_ONE_MILLISECOND,
                null,
                new CustomDnsResolver(2),
                null);
```

构造方法的第6个参数就是DnsResolver，我们在初始化DnsResolver类时指定了超时时间为2，单位为秒。更灵活的方式应该是将该超时时间参数放到配置文件中。

通过自定义的CustomDnsResolver类，同时在PoolingHttpClientConnectionManager构造方法中传入CustomDnsResolver对象，就能够对DNS解析超时进行控制。