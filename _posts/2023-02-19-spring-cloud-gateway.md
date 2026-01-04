---
layout: post
title:  "SpringCloudGateway 动态转发后端服务"
date:   2023-02-19 17:50:00 +0800
tags: [spring,SpringCloudGateway]
categories: [spring boot]
image: assets/images/springcloudgateway.jpg
---

API网关的核心功能是统一流量入口，实现路由转发，SpringCloudGateway是API网关开发的技术之一，此外比较流行的还有Kong和ApiSix，这2个都是基于OpenResty技术栈。
简单的路由转发可以通过SpringCloudGateway的配置文件实现，在一些业务场景种，会需要动态替换路由配置中的后端服务地址，单纯靠配置文件无法满足这种需求。
本文介绍一种将路由配置保存到数据库中，可以根据接口请求的特定条件，从数据库中动态读取后端服务地址，实现灵活转发。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-cloud-gateway](https://github.com/qihaiyan/springcamp/tree/main/spring-cloud-gateway)

## 一、概述

通过把SpringCloudGateway的相关路由配置规则保存到数据库中，可以动态的灵活调整路由。在本文的实现中，我们通过请求header中的特定值，动态选择对应的后端服务地址。

## 二、项目中加入依赖

在项目的gradle中增加依赖关系。

build.gradle:

``` groovy
plugins {
    id 'org.springframework.boot' version '3.0.2'
    id 'io.spring.dependency-management' version '1.1.0'
    id 'java'
}

group = 'cn.springcamp'
version = '0.0.1-SNAPSHOT'
sourceCompatibility = '17'

configurations {
    compileOnly {
        extendsFrom annotationProcessor
    }
    testCompileOnly {
        extendsFrom testAnnotationProcessor
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation "org.springframework.boot:spring-boot-starter-json"
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    implementation 'org.springframework.boot:spring-boot-starter-data-r2dbc'
    implementation 'org.springframework.cloud:spring-cloud-starter-gateway'
    runtimeOnly 'com.h2database:h2'
    runtimeOnly 'io.r2dbc:r2dbc-h2'
    annotationProcessor 'org.projectlombok:lombok'
    testAnnotationProcessor 'org.projectlombok:lombok'
    testImplementation "org.springframework.boot:spring-boot-starter-test"
    testImplementation 'org.junit.vintage:junit-vintage-engine'
    testImplementation 'io.projectreactor:reactor-test'
    testImplementation 'com.h2database:h2'
    testImplementation 'io.r2dbc:r2dbc-h2'
    testImplementation 'org.junit.vintage:junit-vintage-engine'
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.cloud:spring-cloud-dependencies:2022.0.1"
    }
}

test {
    useJUnitPlatform()
}
```

由于SpringCloudGateway基于SpringWebFlux技术构建，所以依赖中的数据库配置需要使用r2dbc 。

## 三、配置文件

示例程序首选通过配置文件对路由进行基本配置，配置文件代码:

``` yml
spring:
  r2dbc:
    url: r2dbc:h2:mem:///testdb?options=DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
    username: sa
    password:
  cloud:
    gateway:
      routes:
        - id: routeOne
          predicates:
            - Path=/route1/**
          uri: no://op
          filters:
            - UriHostPlaceholderFilter=10001
        - id: routeTwo
          predicates:
            - Path=/route2/**
          uri: no://op
          filters:
            - UriHostPlaceholderFilter=10001
```

配置文件中配置了2个路由，对应的接口地址路径分别是 ```/route1/**``` 和 ```Path=/route2/**``` ，路径中的 ```***``` 表示模糊匹配，只要是以 ```/route1/``` 为前缀的路径都可以被访问到。

后端服务地址配置了一个无意的地址: ```uri: no://op``` ，因为我们的处理逻辑会通过从数据库中读取配置来动态替换后端服务地址。

## 四、动态路由数据存储格式

我们通过 ```ROUTE_FILTER_ENTITY``` 这个数据库表来存储接口后端服务配置数据。表结构为：

```sql
CREATE TABLE "ROUTE_FILTER_ENTITY"
(
   id VARCHAR(255) PRIMARY KEY,
   route_id VARCHAR(255),  -- 路由ID，对应配置文件中的 ```id``` 配置项
   code VARCHAR(255), -- 接口请求header中的code参数的值
   url VARCHAR(255) -- 后端服务地址
);
```

当客户端访问 ```/route1/test``` 接口时，根据配置文件的路由配置，SpringCloudGateway 会命中 ```id: routeOne``` 这个路由规则，这个规则对应的后端服务地址是 ```uri: no://op``` ，并不是我们期望的真实后端服务地址。

因此，我们需要读取到真实的后端服务地址，并将请求转发到这个地址。跟据 routeId 和 接口请求header中的code参数的值，就可以从 ROUTE_FILTER_ENTITY 表中查到对应的后端服务地址 ```url``` 这个字段的值。

我们已经读取到了后端服务地址，还需要将请求转发到这个地址，下面介绍转发的方法。

## 五、后端服务动态转发

动态转发通过自定义 filter 的方式实现，自定义 filter 代码如下：

```java
@Component
public class UriHostPlaceholderFilter extends AbstractGatewayFilterFactory<UriHostPlaceholderFilter.Config> {
    @Autowired
    private RouteFilterRepository routeFilterRepository;

    public UriHostPlaceholderFilter() {
        super(Config.class);
    }

    @Override
    public List<String> shortcutFieldOrder() {
        return Collections.singletonList("order");
    }

    @Override
    public GatewayFilter apply(Config config) {
        return new OrderedGatewayFilter((exchange, chain) -> {
            String code = exchange.getRequest().getHeaders().getOrDefault("code", new ArrayList<>()).stream().findFirst().orElse("");
            String routeId = exchange.getAttribute(GATEWAY_PREDICATE_MATCHED_PATH_ROUTE_ID_ATTR);
            if (StringUtils.hasText(code)) {
                String newurl;
                try {
                    newurl = routeFilterRepository.findByRouteIdAndCode(routeId, code).toFuture().get().getUrl();
                } catch (InterruptedException | ExecutionException e) {
                    throw new RuntimeException(e);
                }
                if (StringUtils.hasText(exchange.getRequest().getURI().getQuery())) {
                    newurl = newurl + "?" + exchange.getRequest().getURI().getQuery();
                }
                URI newUri = null;
                try {
                    newUri = new URI(newurl);
                } catch (URISyntaxException e) {
                    log.error("uri error", e);
                }

                exchange.getAttributes().put(GATEWAY_REQUEST_URL_ATTR, newUri);
            }
            return chain.filter(exchange);
        }, config.getOrder());
    }

    @Data
    @NoArgsConstructor
    public static class Config {
        private int order;

        public Config(int order) {
            this.order = order;
        }
    }
}
```

通过扩展 AbstractGatewayFilterFactory 类，我们自定义了 UriHostPlaceholderFilter 这个 filter 。

代码的核心逻辑在 apply 方法中。

首先通过 ```String code = exchange.getRequest().getHeaders().getOrDefault("code", new ArrayList<>()).stream().findFirst().orElse("")``` 可以获取到接口请求 header 中 code 这个参数的值。

再通过 ```String routeId = exchange.getAttribute(GATEWAY_PREDICATE_MATCHED_PATH_ROUTE_ID_ATTR)``` 可以获取到 routeId 。

最后通过 ```newurl = routeFilterRepository.findByRouteIdAndCode(routeId, code).toFuture().get().getUrl()``` 就可以从数据库中读取到配置好的后端服务地址。

拿到后端服务地址后， 通过调用 ```exchange.getAttributes().put(GATEWAY_REQUEST_URL_ATTR, newUri);``` 将请求转发到对应的地址。

## 六、单元测试

在单元测试代码中，我们预置了一条后端服务动态配置数据：
```sql
insert into ROUTE_FILTER_ENTITY values('1','routeOne','alpha','http://httpbin.org/anything')
```

然后模拟请求 ```/route1/test?a=test``` 这个接口，根据我们的配置，请求会被转发到 ```http://httpbin.org/anything``` 。

执行单元测试后，可以从日志中发现，接口返回的数据是 http://httpbin.org/anything 这个后端服务返回的数据。

当我们希望调整后端服务地址时，只需要把 ROUTE_FILTER_ENTITY 表中的这条配置数据中的 url 字段改成其它的任何服务地址即可，大大增加了程序的灵活度。