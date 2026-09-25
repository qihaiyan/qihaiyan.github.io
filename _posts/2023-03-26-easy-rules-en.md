---
layout: post
title:  "The Lightweight Rules Engine easy-rules"
date:   2023-03-26 17:50:00 +0800
lang: en
slug_zh: easy-rules
tags: [spring,java]
categories: [spring boot]
image: assets/images/rule_engine.png
description: "Use the lightweight easy-rules engine in Spring: business rules are externalized to config with SPEL support, so changing rules requires no code changes."
---

Using a rules engine properly can greatly reduce code complexity and improve code maintainability. The best-known open-source rules engine in the industry is Drools — feature-rich, but also quite heavy. In some simpler scenarios, a lightweight rules engine is all we need to meet the requirements.
This post introduces a small rules engine, [easy-rules](https://github.com/j-easy/easy-rules), provided as a library. It supports Spring SPEL expressions and integrates nicely into Spring projects.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-easy-rule](https://github.com/qihaiyan/springcamp/tree/main/spring-easy-rule)

## 1. Overview

Moving business rules into configuration files streamlines the code and makes it easier to maintain: when a rule changes, only the configuration file needs to be modified. easy-rules is a compact rules engine that supports Spring SPEL expressions, as well as Apache JEXL expressions and MVL expressions.

## 2. Adding the Dependencies to the Project

Add the dependencies in the project's gradle build.

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

## 3. The Configuration File

The example program puts the business rules into a configuration file. The business rule configuration file (demo-rule.yml):

``` yml
name: "age rule"
description: ""
priority: 1
condition: "#person.getAdult() == false"
actions:
  - "T(java.lang.System).out.println(\"Shop: Sorry, you are not allowed\")"
  - "#person.setAdult(true)"
  - "#person.setAge(18)"
---
name: "alcohol rule"
description: ""
priority: 1
condition: "#person.getAdult() == true"
actions:
  - "T(java.lang.System).out.println(\"Shop: you are now allowed\")"
```

Rules in the configuration file are defined through a condition; when a rule is satisfied, the actions configured in actions are invoked.
The example project uses Spring SPEL expressions for rule configuration. Two rules are configured in the file: the first rule checks whether the rule is satisfied through getAdult() on the ```person``` Spring bean, and when the rule is satisfied, three methods are invoked.

Configure the rule files in Spring Boot's own configuration file, application.yml:

``` yml
rule:
  skip-on-first-failed-rule: true
  skip-on-first-applied-rule: false
  skip-on-first-non-triggered-rule: true
  rules:
    - rule-id: "demo"
      rule-file-location: "classpath:demo-rule.yml"
```

## 4. Configuring the Rules Engine in Code

The rules engine is configured through the ```RuleEngineConfig``` Spring configuration class:

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

The configuration defines the ```ruleEngineTemplate``` Spring bean; the execution of the rules engine is triggered through ruleEngineTemplate.

## 5. Executing the Rules Engine

Once ```ruleEngineTemplate``` is configured, we can execute the rules engine in business code to process the business rules configured in the configuration file:

For demonstration, we put the rules engine execution code in the run method of Application, so the rules engine fires as soon as the program starts:

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

After the program runs, the console prints ```Shop: Sorry, you are not allowed```, which corresponds to the ```"T(java.lang.System).out.println(\"Shop: Sorry, you are not allowed\")"``` action we configured in the actions of the rule file — proof that the rule was executed successfully.
