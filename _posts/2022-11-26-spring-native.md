---
layout: post
title:  "Spring Boot 3的AOT（GraalVM Native Image）应用开发"
date:   2022-04-17 17:50:00 +0800
tags: [spring,GraalVM Native]
categories: [spring boot]
image: assets/images/spring-native.jpg
---

GraalVM Native Images是一个利用AOT(Ahead-of-Time)技术把java程序直接编译成可执行程序的编译工具，编译出来的程序在运行时不再依赖JRE，同时启动速度快，资源消耗低，这对传统java程序来说都是极大的优势。同时云原生应用来说，GraalVM Native Images编译生成的程序体积很小，非常适合云原生环境，目前由于传统java程序生成的镜像中需要包含一个体积很大的JRE或JDK而经常被人诟病。
Spring Boot从3.0版本开始支持AOT技术。
具体的代码参照 [示例项目 https://github.com/qihaiyan/spring-native](https://github.com/qihaiyan/spring-native)

## 一、概述

Spring Boot 3.0 仍然支持传统的开发方式，既编译生成jar包，通过JRE来执行，在此基础上，通过调整编译方式，可以编译生成直接运行的可执行程序，Sprint AOT与传统应用的区别包括：

1. 程序运行时动态调整的资源无法直接使用，例如反射、动态代理等，需要在代码中通过Hint为编译器指定
2. 应用的classpath在编译后就固定了，不能动态调整
3. 类不会延迟加载（lazy loading），应用启动时一次性加载完成
4. 部分java切面（AOP）技术不支持

## 二、项目中加入依赖

在项目的gradle中增加依赖关系。

Gradle:

``` gradle
plugins {
    id 'org.springframework.boot' version '3.0.0'
    id 'io.spring.dependency-management' version '1.1.0'
    id 'org.graalvm.buildtools.native' version '0.9.18'
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
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'com.h2database:h2'
    annotationProcessor 'org.projectlombok:lombok'
    testAnnotationProcessor 'org.projectlombok:lombok'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}

test {
    useJUnitPlatform()
}
```

与传统Spring Boot应用相比，gradle文件中增加了 org.graalvm.buildtools.native 这个plugin，其它的没有区别。

## 三、主要程序代码

示例程序提供了一个rest接口，该接口从数据库中读取数据。为了便于演示，使用H2数据库。

Application程序代码:

``` java
@RestController
@SpringBootApplication
public class Application {
    @Autowired
    private DbService dbService;

    @RequestMapping("/hello")
    public DemoData hello() {
        return dbService.hello();
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

DbService代码:

``` java
@Component
public class DbService {
    @Autowired
    private TestDataRepository testDataRepository;

    public DemoData hello() {
        DemoData demoData = new DemoData();
        demoData = testDataRepository.save(demoData);
        return demoData;
    }
}
```

由于程序中没有使用反射，所以代码跟传统程序没有什么区别。

## 三、编译 Native Image

Spring Boot 编译 Native Image 支持2种方式，一种通过Docker进行编译，需要本地安装Docker。另外一种是用本地的编译环境进行编译，需要安装Visual Studio。
由于第一种方式比较简单，除了要安装Docker外没有很复杂的操作，本文只介绍第二种方式。

### 3.1 安装编译环境

需要安装 GraalVM 和 Visual Studio 两个编译工具。
GraalVM可以直接下载安装，下载地址 https://www.graalvm.org/downloads/ ，也可以通过 [Scoop](https://scoop.sh/) 进行安装。
Visual Studio 需要下载安装，由于Visual Studio体积比较大，也可以只安装 [Visual Studio Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe)

### 3.2 执行编译命令

由于windows命令行工具有命令长度限制，因此编译命令不能在windows命令行工具中直接执行（包括powershell和cmd），需要在安装好的Visual Studio命令行工具（x64 Native Tools Command Prompt for VS 2022）中执行。

执行命令

```
gradle nativeCompile
```

编译生成的可执行程序在当前工程目录的 build\native\nativeTestCompile 目录中，可以看到一个与工程名相同的以exe后缀结尾的文件。
直接运行该文件，就能体验到java程序的启动速度竟然能如此之快。
启动速度虽然快了，但是编译耗时也多了不少，这是一个缺点。

## 四、单元测试

传统的Spring Boot单元测试技术仍然可以使用。 [Spring Boot单元测试技术](https://springcamp.cn/spring-boot-unit-test/)在这篇文章中有专门介绍。
需要注意的是 Spring Native不支持JUnit4，需要使用JUnit5。

单元测试代码：

``` java
@Slf4j
@ExtendWith(SpringExtension.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class ApplicationTest {
    @Autowired
    private TestRestTemplate testRestTemplate;

    @Test
    public void testHello() {
        String resp = testRestTemplate.getForObject("/hello", String.class);
        log.info("hello result : {}" + resp);
        assertThat(resp, is("{\"id\":1}"));
    }
}
```

通过传统单元测试技术可以验证代码业务逻辑是正常的，对于编译成 Native Image 后程序是否还能正常运行，传统单元测试技术保证不了，需要进一步使用 Native Image 单元测试。

Native Image 单元测试通过以下命令执行：

```
gradle nativeTest
```

该命令会首先把应用编译成 Native Image 可执行程序，再跑单元测试用例。由于  Native Image 编译相比传统应用耗时要长很多，所以先通过传统的Spring Boot单元测试技术保证代码业务逻辑正常后，再使用 Native Image 单元测试命令，减少整个开发流程的耗时。