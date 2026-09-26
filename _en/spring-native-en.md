---
layout: post
title:  "AOT (GraalVM Native Image) Application Development with Spring Boot 3"
date:   2022-11-26 17:50:00 +0800
lang: en
slug_zh: spring-native
tags: [spring,GraalVM Native]
categories: [spring boot]
image: assets/images/spring-native.jpg
description: "Spring Boot 3 AOT and GraalVM Native Image: hint configuration for reflection and proxies to build fast, small native executables for cloud-native apps."
---

GraalVM Native Images is a compilation tool that uses AOT (Ahead-of-Time) technology to compile Java programs directly into native executables. The resulting program no longer depends on a JRE at runtime, starts quickly, and consumes few resources — huge advantages over traditional Java programs. For cloud-native applications, programs built with GraalVM Native Images are very small and well suited to cloud-native environments, whereas traditional Java images are often criticized for having to bundle a large JRE or JDK.
Spring Boot has supported AOT since version 3.0.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-native](https://github.com/qihaiyan/springcamp/tree/main/spring-native).

## 1. Overview

Spring Boot 3.0 still supports the traditional development model, where a jar is built and executed on a JRE. On top of that, by adjusting the build, you can compile the application into a standalone native executable. The differences between Spring AOT and a traditional application include:

1. Resources that are adjusted dynamically at runtime cannot be used directly, such as reflection and dynamic proxies; they must be declared to the compiler via hints in the code
2. The application classpath is fixed at build time and cannot be changed dynamically
3. Classes are not lazily loaded; everything is loaded in one go at application startup
4. Some Java aspect (AOP) techniques are not supported

## 2. Adding Dependencies to the Project

Add the dependencies to the project's gradle build.

build.gradle:

``` groovy
plugins {
    id 'org.springframework.boot' version '3.0.0'
    id 'io.spring.dependency-management' version '1.1.0'
    id 'org.graalvm.buildtools.native' version '0.9.22'
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

Compared with a traditional Spring Boot application, the gradle file adds the org.graalvm.buildtools.native plugin; everything else is unchanged.

Since the org.graalvm.buildtools.native plugin is not published to the Gradle Plugin Portal (see [https://graalvm.github.io/native-build-tools/latest/gradle-plugin.html](https://graalvm.github.io/native-build-tools/latest/gradle-plugin.html)), you need to specify the repository address in settings.gradle:

settings.gradle

```groovy
pluginManagement {
    repositories {
        mavenCentral()
        gradlePluginPortal()
    }
}
```

## 3. Main Application Code

The example program provides a rest endpoint that reads data from a database. For demonstration purposes it uses an H2 database.

Application code:

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

DbService code:

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

Since the program does not use reflection, the code is no different from a traditional application.

## 4. Building the Native Image

Spring Boot supports two ways to build a Native Image: one builds through Docker, which requires a local Docker installation; the other uses the local build environment, which requires Visual Studio. Since the first way is simpler — nothing complicated beyond installing Docker — this article only covers the second one.

### 4.1 Installing the Build Environment

Two build tools need to be installed: GraalVM and Visual Studio.
GraalVM can be downloaded and installed directly from the [download page](https://www.graalvm.org/downloads/), or installed via [Scoop](https://scoop.sh/).
Visual Studio must be downloaded and installed; because Visual Studio is quite large, you can also install only the [Visual Studio Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe)

### 4.2 Running the Build Command

Because Windows command-line tools have a command length limit, the build command cannot be run directly in a Windows command-line tool (neither powershell nor cmd); it must be run in the installed Visual Studio command-line tool (x64 Native Tools Command Prompt for VS 2022).

Run the command

```
gradle nativeCompile
```

The built executable is in the ```build\native\nativeCompile``` directory of the project, where you will find a file named after the project with an exe extension. Run it directly and experience just how fast a Java program can start.

Traditional application startup time:
```
cn.springcamp.springnative.Application   : Started Application in 2.927 seconds (process running for 3.642)
```

Native application startup time:
```
cn.springcamp.springnative.Application   : Started Application in 0.134 seconds (process running for 0.141)
```

Startup improved from 3.642 seconds to 0.141 seconds.

Although startup is much faster, compilation takes considerably longer — a drawback.

## 5. Unit Testing

Traditional Spring Boot unit testing techniques still work. [Spring Boot unit testing](https://springcamp.cn/spring-boot-unit-test/) is covered in detail in that article. Note that Spring Native does not support JUnit4; you need to use JUnit5.

Unit test code:

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

Traditional unit tests can verify that the business logic is correct, but they cannot guarantee that the program still runs properly after being compiled to a Native Image; for that you need to go further and use Native Image unit tests.

Native Image unit tests are run with the following command:

```
gradle nativeTest
```

This command first compiles the application into a Native Image executable, then runs the unit tests. Because Native Image compilation takes much longer than a traditional build, run the traditional Spring Boot unit tests first to make sure the business logic is correct, and only then use the Native Image test command, reducing the total time of the development cycle.
