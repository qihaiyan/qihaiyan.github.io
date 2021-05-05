---
layout: post
title:  "springboot集成groovy脚本"
date:   2021-05-05 16:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/groovy.jpeg
---

在我们的应用中引入脚本能力，可以很好的提升灵活性，我们的核心开发工作可以集中在核心平台能力的开发上，具体场景的功能可以通过脚本来实现，例如jenkins就可以通过groovy脚本来编写pipeline，可以很灵活的定制构建过程。
spring本身提供了groovy集成的机制，分为两种方式，一种是用groovy开发程序，跟用java开发类似，需要经过编译。一种是将groovy作为脚本来执行，不需要编译。在此我们介绍的是第二种方式，将groovy作为脚本来使用。
具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-groovy](https://github.com/qihaiyan/springcamp/tree/master/spring-groovy)

## 一、概述

在spring中集成groovy脚本，主要有2种思路，一种是在groovy脚本中定义bean，这样groovy脚本就融入了整个spring的体系，跟使用普通的bean没有区别。一种是在程序中调用groovy脚本，让groovy脚本成为一个可执行的部件。下面我们分别介绍这2种方式。
在spring中声明groovy脚本中定义的bean有两种方式，一种是传统的xml，一种是spring-framework-4中引入的groovy声明方式。

## 二、在groovy中定义bean

首先我们定义一个interface：

```java
public interface MyService {
    String fun(MyDomain myDomain);
}
```

这儿提供了一种思路，我们可以用java代码编写默认的interface实现，如果默认实现不满足特定场景的要求时，配合策略模式，用groovy脚本实现特定场景，程序会变的很灵活，配合脚本的热加载机制，当处理逻辑需要变化时，在程序运行的过程中，我们可以随时调整脚本内容且能够及时生效。

在groovy脚本```MyServiceImpl.groovy```中实现这个interface：

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

下面分别介绍通过xml和groovy两种配置方式来声明bean。

### 2.1、通过xml配置的方式声明groovy中实现的bean

通过xml配置声明bean是spring传统的方法，这种方法近来已经被通过java代码声明的方式取代，但是对于声明groovy脚本中定义的bean来说还是最简单的方法。

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

以上xml代码声明了myServiceXml这个bean，```script-source```指定了这个bean的来源是```classpath:MyServiceImpl.groovy```这个脚本文件。将classpath替换为file，可以指定任一位置的脚本文件。
```refresh-check-delay```定义了脚本的刷新间隔，当脚本内容发生变化后，可以自动刷新脚本的内容。
```lang:property```这个标签可以对bean的属性进行初始化赋值。我们分别用xml和groovy两种声明bean的方式给myProp这个属性赋值不同的初始值，在后续的演示代码中可以看到。

### 2.2、通过groovy配置的方式声明groovy中实现的bean

spring-framework-4中引入了groovy声明bean的方式，我们用groovy来声明myServiceGroovy这个bean，相比于xml的方式，groovy的声明方式可读性更强一些。

详细介绍见spring的官方博文： [Groovy Bean Configuration in Spring Framework 4](https://spring.io/blog/2014/03/03/groovy-bean-configuration-in-spring-framework-4)

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

通过```GroovyScriptFactory```可以指定定义bean的groovy脚本位置。
通过```bean```的lambda表达式，可以对bean的属性进行赋值，除了我们定义的myProp这个属性外，还可以定义scope和脚本刷新时间。

### 2.3、调用groovy中实现的bean

前面我们通过xml和groovy两种方式分别声明了2个bean: ```myServiceXml```和```myServiceGroovy```，下面我们在程序中调用这2个bean。

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

首先我们通过```@ImportResource```来引入bean的声明文件，然后就是普通的bean的依赖注入和方法调用，可以看到在bean的使用上，脚本定义的bean和用程序编写的bean没有任何区别。
在run方法中，我们分别调用了myServiceXml和myServiceGroovy的这2个bean的fun方法。
执行run方法可以看到输出到结果：

```bash
MyDomain(name=test)FunBean this is xml init prop
MyDomain(name=test2)FunBean this is Bean Builder init prop
```

## 三、执行groovy脚本

除了前面提到的在groovy中实现bean以外，我们还可以通过groovy提供的GroovyScriptEngine来执行groovy脚本，这种方式不依赖于springframework，普通的java程序中也可以使用。

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

首先我们初始化GroovyScriptEngine，在构造方法中传入脚本文件的路径。

执行脚本的方法有2种，一种是获取到GroovyObject，通过invokeMethod来执行脚本中的某个方法，方法的参数通过Object数组传入。

```java
Class<GroovyObject> calcClass = engine.loadScriptByName("CalcScript.groovy");
GroovyObject calc = calcClass.newInstance();

Object result = calc.invokeMethod("calcSum", new Object[]{x, y});

```

第二种是直接运行groovy脚本，可以通过Binding将变量传递到groovy脚本中。

``` java
Binding binding = new Binding();
binding.setVariable("arg", "test");
binding.setVariable("funBean", funBean);
Object result1 = engine.run("CalcScript.groovy", binding);
```
