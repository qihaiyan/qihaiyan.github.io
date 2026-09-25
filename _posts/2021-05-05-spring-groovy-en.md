---
layout: post
title:  "Integrating Groovy Scripts in Spring Boot"
date:   2021-05-05 16:20:00 +0800
lang: en
slug_zh: spring-groovy
tags: [spring,java]
categories: [spring boot]
image: assets/images/groovy.jpeg
description: "Two ways to integrate Groovy scripts in Spring: defining script-based beans in the Spring context, and executing scripts directly for flexible business logic."
---

Introducing scripting capability into our application can greatly improve flexibility: core development work can focus on building core platform capabilities, while functionality for specific scenarios can be implemented with scripts. For example, jenkins lets you write pipelines in groovy scripts, allowing the build process to be customized with great flexibility.
Spring itself provides a mechanism for groovy integration in two flavors: one is developing programs in groovy, similar to developing in java, which requires compilation; the other is executing groovy as a script, with no compilation needed. This post covers the second approach, using groovy as a script.
The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-groovy](https://github.com/qihaiyan/springcamp/tree/main/spring-groovy)

## 1. Overview

There are two main approaches to integrating groovy scripts in spring: one is to define beans in the groovy script, so the script becomes part of the whole spring system and is no different from using ordinary beans; the other is to call the groovy script from the program, making it an executable component. We introduce both approaches below.
There are two ways to declare a bean defined in a groovy script in spring: the traditional xml way, and the groovy declaration style introduced in spring-framework-4.

## 2. Defining Beans in Groovy

First we define an interface:

```java
public interface MyService {
    String fun(MyDomain myDomain);
}
```

This suggests an approach: we can write the default implementation of the interface in java, and when the default implementation does not meet the requirements of a specific scenario, combined with the strategy pattern, implement that scenario with a groovy script so the program becomes very flexible. Together with the script hot-reload mechanism, when the processing logic needs to change, we can adjust the script content at any time while the program is running and it takes effect immediately.

Implement this interface in the groovy script ```MyServiceImpl.groovy```:

```groovy
class MyServiceImpl implements MyService {
    @Autowired
    FunBean useBean;

    String myProp;

    String fun(MyDomain myDomain) {
        return myDomain.toString() + useBean.getFunName() + myProp;
    }
}
```

Below we introduce the xml and groovy configuration approaches for declaring the bean.

### 2.1. Declaring a Bean Implemented in Groovy via XML Configuration

Declaring beans via xml configuration is the traditional spring approach. It has recently been superseded by declaring beans in java code, but for declaring beans defined in groovy scripts it is still the simplest method.

``` xml
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:lang="http://www.springframework.org/schema/lang"
       xsi:schemaLocation="
        http://www.springframework.org/schema/beans https://www.springframework.org/schema/beans/spring-beans.xsd
        http://www.springframework.org/schema/lang https://www.springframework.org/schema/lang/spring-lang.xsd">
    <lang:groovy id="myServiceXml" script-source="classpath:MyServiceImpl.groovy" refresh-check-delay="10000" >
        <lang:property name="myProp" value=" this is xml init prop" />
    </lang:groovy>
</beans>
```

The xml above declares the bean myServiceXml; ```script-source``` specifies that the bean comes from the script file ```classpath:MyServiceImpl.groovy```.
Replacing classpath with file allows pointing to a script file at any location.

```refresh-check-delay``` defines the script refresh interval; when the script content changes, the script is refreshed automatically.

The property tag initializes the bean's properties. We assign different initial values to the myProp property through the xml and groovy declaration styles respectively, as shown in the demonstration code later.

### 2.2. Declaring a Bean Implemented in Groovy via Groovy Configuration

spring-framework-4 introduced declaring beans with groovy. We declare the myServiceGroovy bean with groovy; compared with xml, the groovy style is more readable.

For details, see the official spring blog post: [Groovy Bean Configuration in Spring Framework 4](https://spring.io/blog/2014/03/03/groovy-bean-configuration-in-spring-framework-4)

``` groovy
import org.springframework.scripting.groovy.GroovyScriptFactory
import org.springframework.scripting.support.ScriptFactoryPostProcessor

beans {
    scriptFactoryPostProcessor(ScriptFactoryPostProcessor) {
        defaultRefreshCheckDelay = 10000
    }
    myServiceGroovy(GroovyScriptFactory, 'classpath:MyServiceImpl.groovy') {
        bean ->
            bean.scope = "prototype"
            myProp = ' this is Bean Builder init prop'
            bean.beanDefinition.setAttribute(ScriptFactoryPostProcessor.REFRESH_CHECK_DELAY_ATTRIBUTE, 6000)
    }
}
```

```GroovyScriptFactory``` specifies the location of the groovy script that defines the bean.
Through the ```bean``` lambda expression you can assign the bean's properties; besides our custom myProp property, you can also define the scope and the script refresh delay.

### 2.3. Invoking Beans Implemented in Groovy

Above we declared two beans via xml and groovy respectively: ```myServiceXml``` and ```myServiceGroovy```. Now we call these two beans in the program.

```java
@SpringBootApplication
@ImportResource({"classpath:xml-bean-config.xml", "classpath:BeanBuilder.groovy"})
public class Application implements CommandLineRunner {

    @Autowired
    private MyService myServiceXml;
    @Autowired
    private MyService myServiceGroovy;

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Override
    public void run(String... args) throws ScriptException, ResourceException, IllegalAccessException, InstantiationException {
        MyDomain myDomain = new MyDomain();
        myDomain.setName("test");
        System.out.println(myServiceXml.fun(myDomain));
        myDomain.setName("test2");
        System.out.println(myServiceGroovy.fun(myDomain));
    }
}
```

First we import the bean declaration files with ```@ImportResource```; from then on it is ordinary bean dependency injection and method calls. As you can see, in terms of usage there is no difference between a script-defined bean and a bean written in code.
In the run method, we call the fun method of the two beans myServiceXml and myServiceGroovy.
Running the run method produces the following output:

```bash
MyDomain(name=test)FunBean this is xml init prop
MyDomain(name=test2)FunBean this is Bean Builder init prop
```

## 3. Executing Groovy Scripts

Besides implementing beans in groovy as described above, we can also execute groovy scripts with the GroovyScriptEngine provided by groovy. This approach does not depend on springframework and can also be used in plain java programs.

``` java
@Component
public class MyEngine {
    private final GroovyScriptEngine engine;

    @Autowired
    private FunBean funBean;

    public MyEngine() throws IOException {

        engine = new GroovyScriptEngine(ResourceUtils.getFile("classpath:scripts/").getAbsolutePath()
                , this.getClass().getClassLoader());
    }

    public void runScript(int x, int y) throws IllegalAccessException,
            InstantiationException, ResourceException, ScriptException {
        Class<GroovyObject> calcClass = engine.loadScriptByName("CalcScript.groovy");
        GroovyObject calc = calcClass.newInstance();

        Object result = calc.invokeMethod("calcSum", new Object[]{x, y});
        System.out.println("Result of CalcScript.calcSum() method is " + result);

        Binding binding = new Binding();
        binding.setVariable("arg", "test");
        binding.setVariable("funBean", funBean);
        Object result1 = engine.run("CalcScript.groovy", binding);
        System.out.println("Result of CalcScript.groovy is " + result1);
    }
}
```

First we initialize GroovyScriptEngine, passing the script file path in the constructor.

There are two ways to execute a script. One is to obtain the GroovyObject and invoke a method in the script via invokeMethod, passing the method arguments as an Object array.

```java
Class<GroovyObject> calcClass = engine.loadScriptByName("CalcScript.groovy");
GroovyObject calc = calcClass.newInstance();

Object result = calc.invokeMethod("calcSum", new Object[]{x, y});

```

The second is to run the groovy script directly; variables can be passed into the script through a Binding.

``` java
Binding binding = new Binding();
binding.setVariable("arg", "test");
binding.setVariable("funBean", funBean);
Object result1 = engine.run("CalcScript.groovy", binding);
```
