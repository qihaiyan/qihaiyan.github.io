---
layout: post
title:  "How to Set a DNS Resolution Timeout for Spring RestTemplate"
date:   2024-06-16 15:30:00 +0800
lang: en
slug_zh: spring-resttemplate-dns-timeout
tags: [spring,java]
categories: [spring boot]
image: assets/images/dns-timeout.jpg
description: "Set a DNS resolution timeout for RestTemplate with a custom DnsResolver injected into the Apache HttpClient connection pool, closing the last timeout gap."
---

The usual timeout settings of RestTemplate cover the connect timeout, the request timeout, and the response timeout, but there is often no simple way to set a DNS resolution timeout. This post shows how to set the DNS resolution timeout. The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log)

<blockquote class="en-abstract">
RestTemplate's built-in timeout settings cover connect, request and response timeouts, but offer no direct way to set a DNS resolution timeout. This post shows how to add one by implementing a custom <code>DnsResolver</code> on top of Apache HttpClient, with a runnable example at <a href="https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log">springcamp/spring-rest-template-log</a>.
</blockquote>

## 1. Overview

When calling remote APIs with RestTemplate in Spring, timeouts usually need to be set; otherwise, when the remote API is slow, it can easily clog up your own system. The connect timeout, the request-sending timeout, and the response-receiving timeout can all be set through direct method calls, while setting a DNS resolution timeout requires a relatively involved approach.

## 2. Implementing a Custom DnsResolver

First, configure RestTemplate to use Apache HttpClient for HTTP calls. Apache HttpClient performs DNS resolution internally through a default DnsResolver, and we can set a DNS resolution timeout by implementing our own DnsResolver.

The following code is the custom CustomDnsResolver implementing DnsResolver.

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

The DNS resolution method is resolve. Inside the resolve method, we call the system DNS resolution through CompletableFuture.supplyAsync, and then control the timeout through the CompletableFuture.get method.

## 3. Configuring Apache HttpClient to Use the CustomDnsResolver

The commonly used constructor of PoolingHttpClientConnectionManager takes only a Registry argument and cannot accept a custom DnsResolver, so we need to switch to the constructor that supports specifying a DnsResolver.

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

The sixth constructor argument is the DnsResolver. We set the timeout to 2, in seconds, when initializing the DnsResolver class. A more flexible approach would be to move this timeout parameter into a configuration file.

With the custom CustomDnsResolver class, and by passing the CustomDnsResolver object into the PoolingHttpClientConnectionManager constructor, the DNS resolution timeout can be controlled.
