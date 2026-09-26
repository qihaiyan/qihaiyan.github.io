---
layout: post
title:  "Dynamic Backend Forwarding with Spring Cloud Gateway"
date:   2023-02-19 17:50:00 +0800
lang: en
slug_zh: spring-cloud-gateway
tags: [spring,SpringCloudGateway,featured]
categories: [spring boot]
image: assets/images/springcloudgateway.jpg
description: "How to implement dynamic routing in Spring Cloud Gateway by storing routes in a database and picking the backend service address from request headers."
---

The core function of an API gateway is to unify the traffic entry point and perform route forwarding. SpringCloudGateway is one of the technologies for building API gateways; other popular options are Kong and ApiSix, both based on the OpenResty technology stack.
Simple route forwarding can be achieved through the SpringCloudGateway configuration file, but in some business scenarios the backend service address in the route configuration needs to be replaced dynamically, which a configuration file alone cannot satisfy.
This post describes storing the route configuration in a database and dynamically reading the backend service address from the database based on specific conditions of the API request, enabling flexible forwarding.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-cloud-gateway](https://github.com/qihaiyan/springcamp/tree/main/spring-cloud-gateway)

## 1. Overview

By storing the SpringCloudGateway route configuration rules in a database, routes can be adjusted dynamically and flexibly. In the implementation described here, we select the corresponding backend service address dynamically based on a specific value in the request header.

## 2. Adding Dependencies to the Project

Add the dependencies to the project's gradle build.

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

Since SpringCloudGateway is built on Spring WebFlux, the database configuration in the dependencies needs to use r2dbc.

## 3. Configuration File

The example program first configures basic routes through a configuration file. The configuration file:

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

Two routes are configured in the file, corresponding to the endpoint paths ```/route1/**``` and ```Path=/route2/**``` respectively. The ```***``` in the path means fuzzy matching: any path with the ```/route1/``` prefix can be matched.

The backend service address is configured as a meaningless address: ```uri: no://op```, because our processing logic will dynamically replace the backend service address with the configuration read from the database.

## 4. Dynamic Route Data Storage Format

We use the ```ROUTE_FILTER_ENTITY``` database table to store the backend service configuration data. The table structure is:

```sql
CREATE TABLE "ROUTE_FILTER_ENTITY"
(
   id VARCHAR(255) PRIMARY KEY,
   route_id VARCHAR(255),  -- route ID, corresponding to the ```id``` configuration item in the configuration file
   code VARCHAR(255), -- value of the code parameter in the request header
   url VARCHAR(255) -- backend service address
);
```

When a client accesses the ```/route1/test``` endpoint, according to the route configuration in the configuration file SpringCloudGateway matches the ```id: routeOne``` route rule, whose backend service address is ```uri: no://op``` — not the real backend service address we expect.

Therefore, we need to read the real backend service address and forward the request to it. Based on the routeId and the value of the code parameter in the request header, the corresponding backend service address can be looked up in the ```url``` field of the ROUTE_FILTER_ENTITY table.

Having read the backend service address, we still need to forward the request to it. The forwarding method is described below.

## 5. Dynamic Backend Forwarding

Dynamic forwarding is implemented with a custom filter. The custom filter code is as follows:

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

By extending the AbstractGatewayFilterFactory class, we created the custom UriHostPlaceholderFilter filter.

The core logic of the code is in the apply method.

First, ```String code = exchange.getRequest().getHeaders().getOrDefault("code", new ArrayList<>()).stream().findFirst().orElse("")``` gets the value of the code parameter from the request header.

Then, ```String routeId = exchange.getAttribute(GATEWAY_PREDICATE_MATCHED_PATH_ROUTE_ID_ATTR)``` gets the routeId.

Finally, ```newurl = routeFilterRepository.findByRouteIdAndCode(routeId, code).toFuture().get().getUrl()``` reads the configured backend service address from the database.

With the backend service address in hand, calling ```exchange.getAttributes().put(GATEWAY_REQUEST_URL_ATTR, newUri);``` forwards the request to the corresponding address.

## 6. Unit Testing

In the unit test code, we preset one row of dynamic backend service configuration data:
```sql
insert into ROUTE_FILTER_ENTITY values('1','routeOne','alpha','http://httpbin.org/anything')
```

Then we simulate a request to the ```/route1/test?a=test``` endpoint; according to our configuration, the request is forwarded to ```http://httpbin.org/anything```.

After running the unit test, the logs show that the data returned by the endpoint is the data returned by the http://httpbin.org/anything backend service.

When we want to change the backend service address, we only need to change the url field of this configuration record in the ROUTE_FILTER_ENTITY table to any other service address, which greatly increases the flexibility of the program.
