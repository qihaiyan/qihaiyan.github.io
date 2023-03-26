---
layout: post
title:  "简易规则引擎 easy-rules"
date:   2023-03-26 17:50:00 +0800
tags: [spring]
categories: [spring boot]
image: assets/images/rule_engine.jpg
---

合理的使用规则引擎可以极大的减少代码复杂度，提升代码可维护性。业界知名的开源规则引擎有Drools，功能丰富，但也比较庞大。在一些简单的场景中，我们只需要简易的规则引擎就能满足要求。

本文介绍一个小巧的规则引擎 [easy-rules](https://github.com/j-easy/easy-rules)，作为一个lib库提供，支持spring的SPEL表达式，可以很好的集成在spring项目中。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-easy-rule](https://github.com/qihaiyan/springcamp/tree/master/spring-easy-rule)

## 一、概述

通过将业务规则配置的配置文件中，可以精简代码，同时已于维护，当规则修改时，只需要修改配置文件即可。easy-rules是一个小巧的规则引擎，支持spring的SPEL表达式，同时还支持 Apache JEXL 表达式和 MVL 表达式。

## 二、项目中加入依赖

在项目的gradle中增加依赖关系。

build.gradle:

``` groovy
plugins {
    id 'org.springframework.boot' version '3.0.5'
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
    implementation 'org.jeasy:easy-rules-core:4.1.0'
    implementation 'org.jeasy:easy-rules-spel:4.1.0'
    implementation 'org.jeasy:easy-rules-support:4.1.0'
    annotationProcessor 'org.projectlombok:lombok'
    testAnnotationProcessor 'org.projectlombok:lombok'
    testImplementation "org.springframework.boot:spring-boot-starter-test"
    testImplementation 'org.junit.vintage:junit-vintage-engine'
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

## 三、配置文件

示例程序将业务规则放到配置文件中，业务规则配置文件(demo-rule.yml)代码:

``` yml
name: "age rule"
description: ""
priority: 1
condition: "#person.getAdult() == false"
actions:
  - "T(java.lang.System).out.println(\"Shop: Sorry, you are not allowed to buy alcohol\")"
  - "#person.setAdult(true)"
  - "#person.setAge(18)"
---
name: "alcohol rule"
description: ""
priority: 1
condition: "#person.getAdult() == true"
actions:
  - "T(java.lang.System).out.println(\"Shop: you are now allowed to buy alcohol\")"
```

配置文件中的规则通过 condition 进行配置，当满足规则时，会调用 actions 中配置的动作。
示例项目使用了spring的SPEL表达式进行规则配置，配置文件中配置了2个规则，第一个规则通过 ```person``` 这个spring bean中的getAdult()判断是否满足规则，满足规则时调用三个方法。

在spring-boot本身的配置文件中 application.yml 配置规则文件：

``` yml
rule:
  skip-on-first-failed-rule: true
  skip-on-first-applied-rule: false
  skip-on-first-non-triggered-rule: true
  rules:
    - rule-id: "demo"
      rule-file-location: "classpath:demo-rule.yml"
```

## 四、代码中对规则引擎进行配置

通过 ```RuleEngineConfig``` 这个spring的配置类对规则引擎进行配置：

```java
@Slf4j
@EnableConfigurationProperties(RuleEngineConfigProperties.class)
@Configuration
public class RuleEngineConfig implements BeanFactoryAware {
    @Autowired(required = false)
    private List<RuleListener> ruleListeners;

    @Autowired(required = false)
    private List<RulesEngineListener> rulesEngineListeners;

    private BeanFactory beanFactory;

    @Bean
    public RulesEngineParameters rulesEngineParameters(RuleEngineConfigProperties properties) {
        RulesEngineParameters parameters = new RulesEngineParameters();
        parameters.setSkipOnFirstAppliedRule(properties.isSkipOnFirstAppliedRule());
        parameters.setSkipOnFirstFailedRule(properties.isSkipOnFirstFailedRule());
        parameters.setSkipOnFirstNonTriggeredRule(properties.isSkipOnFirstNonTriggeredRule());
        return parameters;
    }

    @Bean
    public RulesEngine rulesEngine(RulesEngineParameters rulesEngineParameters) {
        DefaultRulesEngine rulesEngine = new DefaultRulesEngine(rulesEngineParameters);
        if (!CollectionUtils.isEmpty(ruleListeners)) {
            rulesEngine.registerRuleListeners(ruleListeners);
        }
        if (!CollectionUtils.isEmpty(rulesEngineListeners)) {
            rulesEngine.registerRulesEngineListeners(rulesEngineListeners);
        }
        return rulesEngine;
    }

    @Bean
    public BeanResolver beanResolver() {
        return new BeanFactoryResolver(beanFactory);
    }

    @Bean
    public RuleEngineTemplate ruleEngineTemplate(RuleEngineConfigProperties properties, RulesEngine rulesEngine) {
        RuleEngineTemplate ruleEngineTemplate = new RuleEngineTemplate();
        ruleEngineTemplate.setBeanResolver(beanResolver());
        ruleEngineTemplate.setProperties(properties);
        ruleEngineTemplate.setRulesEngine(rulesEngine);
        return ruleEngineTemplate;
    }

    @Bean
    public RuleListener defaultRuleListener() {
        return new RuleListener() {
            @Override
            public boolean beforeEvaluate(Rule rule, Facts facts) {
                return true;
            }

            @Override
            public void afterEvaluate(Rule rule, Facts facts, boolean b) {
                log.info("-----------------afterEvaluate-----------------");
                log.info(rule.getName() + rule.getDescription() + facts.toString());
            }

            @Override
            public void beforeExecute(Rule rule, Facts facts) {
                log.info("-----------------beforeExecute-----------------");
                log.info(rule.getName() + rule.getDescription() + facts.toString());
            }

            @Override
            public void onSuccess(Rule rule, Facts facts) {
                log.info("-----------------onSuccess-----------------");
                log.info(rule.getName() + rule.getDescription() + facts.toString());
            }

            @Override
            public void onFailure(Rule rule, Facts facts, Exception e) {
                log.info("-----------------onFailure-----------------");
                log.info(rule.getName() + "----------" + rule.getDescription() + facts.toString() + e.toString());
            }
        };
    }

    @Override
    public void setBeanFactory(BeanFactory beanFactory) throws BeansException {
        this.beanFactory = beanFactory;
    }
}
```

配置文件中配置了 ```ruleEngineTemplate``` 这个spring bean，通过ruleEngineTemplate触发规则引擎的执行。

## 五、执行规则引擎

```ruleEngineTemplate``` 配置好后，我们可以在业务代码中执行规则引擎，处理配置文件中配置的业务规则：

最为演示，我们将规则引擎的执行代码放到了 Application 的 run 方法中，程序启动后立即执行规则引擎：

```java
@SpringBootApplication
public class Application implements CommandLineRunner {

    @Autowired
    RuleEngineTemplate ruleEngineTemplate;

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Override
    public void run(String... args) {
        Person person = new Person();
        Facts facts = new Facts();
        facts.put("person", person);
        ruleEngineTemplate.fire("demo", facts);

    }
}
```

程序执行后可以看到控制台里打印了 ```Shop: Sorry, you are not allowed to buy alcohol```，这个内容对应的是我们在规则文件中的actions中配置的 ```"T(java.lang.System).out.println(\"Shop: Sorry, you are not allowed to buy alcohol\")"``` ，说明规则成功执行了。
