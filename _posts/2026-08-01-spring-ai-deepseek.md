---
layout: post
title:  "Spring AI集成DeepSeek大模型"
date:   2026-08-01 15:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/spring-ai-deepseek.jpg
---

Spring AI 是spring官方提供的大模型集成框架，采用统一的抽象接口对接各类大模型，DeepSeek 是国内热门的开源大模型，本文介绍如何通过Spring AI集成DeepSeek，实现基础对话、流式响应、推理模型思维链以及Function Calling等功能。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-ai-deepseek](https://github.com/qihaiyan/springcamp/tree/main/spring-ai-deepseek)

## 一、概述

Spring AI 遵循了spring生态一贯的设计理念，通过starter自动装配的方式，把不同厂商的大模型统一封装到 ChatClient 和 ChatModel 这套抽象接口之下，开发者只需要引入对应的starter、配置api-key，就可以像调用普通bean一样调用大模型，无需关心底层的http请求和协议细节。

DeepSeek 提供了与OpenAI兼容的接口，同时具备普通对话模型和推理模型（思维链）两种能力。本示例项目基于Spring Boot 4.1.0 和 Spring AI 2.0.0，用极简的代码演示了四种典型用法：

- 基础同步对话
- 流式响应（SSE）
- 推理模型的思维链输出
- Function Calling（工具调用）

## 二、项目依赖与配置

首先引入spring-ai的deepseek starter，整个模块只需要两个依赖：

``` groovy
ext {
    set('springAiVersion', "2.0.0")
}

dependencies {
    implementation 'org.springframework.ai:spring-ai-starter-model-deepseek'
    implementation 'org.springframework.boot:spring-boot-starter-web'
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.ai:spring-ai-bom:${springAiVersion}"
    }
}
```

通过 spring-ai-bom 统一管理spring-ai相关依赖的版本，starter会自动装配好 DeepSeekChatModel 和 ChatClient.Builder，我们直接注入即可使用。

接下来在 application.properties 中配置DeepSeek的api-key和模型参数：

``` properties
server.port=8080
spring.main.banner-mode=off
logging.level.root=INFO

# DeepSeek configuration
spring.ai.deepseek.api-key=your-api-key
spring.ai.deepseek.chat.model=deepseek-chat
spring.ai.deepseek.chat.temperature=0.8
```

api-key 需要在DeepSeek开放平台（https://platform.deepseek.com）申请，示例中写死在配置文件里只是为了演示，生产环境应该通过环境变量或配置中心注入，避免泄露。

## 三、配置ChatClient

spring-ai-deepseek starter 会自动提供一个 ChatClient.Builder，我们只需要在启动类中构建出 ChatClient 这个bean：

``` java
@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Bean
    public ChatClient chatClient(ChatClient.Builder builder) {
        return builder.build();
    }
}
```

ChatClient 是spring-ai提供的模型无关的高层门面，后续的对话、流式响应、工具调用都基于它完成。

## 四、基础对话与流式响应

基础对话是调用大模型最简单的方式，通过 ChatClient 的链式api一行代码就能完成：

``` java
@GetMapping(value = "/chat")
public String chat(@RequestParam(value = "message", defaultValue = "Tell me a joke") String message) {
    return chatClient.prompt().user(message).call().content();
}
```

调用 `/ai/chat?message=讲个笑话` 接口，会同步等待大模型返回完整结果后再响应。

实际应用中，为了提升用户体验，我们通常会采用流式响应，让前端实现类似打字机的逐字输出效果：

``` java
@GetMapping(value = "/chat/stream", produces = MediaType.TEXT_PLAIN_VALUE + ";charset=UTF-8")
public Flux<String> stream(@RequestParam(value = "message", defaultValue = "Tell me a joke") String message) {
    return chatClient.prompt().user(message).stream().content();
}
```

只需要把 `call()` 换成 `stream()`，返回值由 String 变成 `Flux<String>`，spring会以SSE（Server-Sent Events）的方式把大模型逐个生成的token推送给客户端，这里显式设置了 `text/plain;charset=UTF-8`，避免中文出现乱码。

## 五、推理模型思维链

DeepSeek 的推理在给出答案之前会先输出一段思考过程，也就是思维链（Chain of Thought），这是推理模型区别于普通对话模型的关键能力。

ChatClient 是模型无关的通用接口，无法直接获取DeepSeek专属的思考过程，因此这里我们绕过ChatClient，直接注入底层的 DeepSeekChatModel：

``` java
@GetMapping("/reasoning")
public Map<String, String> reasoning(@RequestParam(value = "message", defaultValue = "9.11 和 9.8 哪个大？") String message) {
    ChatResponse response = chatModel.call(new Prompt(message));
    DeepSeekAssistantMessage output = (DeepSeekAssistantMessage) Objects.requireNonNull(response.getResult()).getOutput();
    return Map.of(
            "reasoning", output.getReasoningContent() != null ? output.getReasoningContent() : "",
            "answer", output.getText() != null ? output.getText() : ""
    );
}
```

把返回结果强转为 DeepSeekAssistantMessage 后，就可以分别通过 `getReasoningContent()` 拿到思考过程，通过 `getText()` 拿到最终答案。代码里对这两个字段都做了非空判断，因为只有推理模型才会返回 `reasoningContent`，普通对话模型这个字段为null。

需要注意的是，要真正拿到思维链需要模型具备思维能力，DeepSeek当前的两个模型（deepseek-v4-flash和deepseek-v4-pro）都具备思维能力，普通对话模型不会返回思考过程。默认示例问题"9.11 和 9.8 哪个大？"正是检验模型推理能力的经典测试题。

## 六、Function Calling

Function Calling 让大模型能够调用外部的java方法，从而获取实时数据或执行具体操作。spring-ai通过 `@Tool` 注解把一个普通的java方法声明为可被模型调用的工具，无需手写json schema。

定义一个模拟的天气查询服务：

``` java
@Service
public class WeatherService {

    private static final Map<Integer, String> CONDITIONS = Map.of(
            0, "晴", 1, "多云", 2, "小雨", 3, "小雪"
    );

    @Tool(description = "查询指定城市的当前天气情况，返回温度和天气状况")
    public String getCurrentWeather(String city) {
        int temp = ThreadLocalRandom.current().nextInt(-5, 35);
        String condition = CONDITIONS.get(ThreadLocalRandom.current().nextInt(CONDITIONS.size()));
        return String.format("%s 当前天气：%s，气温 %d°C", city, condition, temp);
    }
}
```

在调用ChatClient时，通过 `tools()` 方法把这个服务传给模型：

``` java
@GetMapping(value = "/tool")
public String tool(@RequestParam(value = "message", defaultValue = "北京和上海今天天气怎么样？") String message) {
    return chatClient.prompt().user(message).tools(weatherService).call().content();
}
```

当用户询问"北京和上海今天天气怎么样？"时，模型会自主判断需要查询天气，自动调用 `getCurrentWeather` 方法两次，分别查询北京和上海的天气，再把结果组织成自然语言返回。整个调用过程由模型决定是否调用、调用几次，这就是Function Calling的核心能力。

## 七、查看Function Calling的调用过程

上一节的 `/ai/tool` 接口只返回了模型的最终答案，但模型在背后到底调用了几次工具、每次传了什么参数、工具返回了什么，从结果里是看不出来的。实际开发和调试中，把这些调用过程暴露出来，能帮助我们观察模型的行为，判断它是否按预期调用了工具。

我们可以定义一个请求作用域的 ToolCallRecorder 来记录单次请求内的工具调用：

``` java
@Component
@RequestScope
public class ToolCallRecorder {

    private final List<ToolInvocation> invocations = new ArrayList<>();

    public record ToolInvocation(String tool, String arguments, String result) {
    }

    public void record(String tool, String arguments, String result) {
        invocations.add(new ToolInvocation(tool, arguments, result));
    }

    public List<ToolInvocation> get() {
        return Collections.unmodifiableList(invocations);
    }
}
```

这里用 `@RequestScope` 把作用域限定在单个HTTP请求内，每个请求都会创建一个独立的实例，请求结束后随之销毁。借助这种请求级别的隔离，无需 ThreadLocal 就能让不同请求的调用记录互不干扰，对虚拟线程也很友好。每条调用过程用 record 封装了工具名、入参和返回值三个字段。

接下来在 WeatherService 中注入 ToolCallRecorder，在工具方法内部把每次调用记录下来：

``` java
@Service
public class WeatherService {

    private static final Map<Integer, String> CONDITIONS = Map.of(
            0, "晴", 1, "多云", 2, "小雨", 3, "小雪"
    );

    private final ToolCallRecorder recorder;

    public WeatherService(ToolCallRecorder recorder) {
        this.recorder = recorder;
    }

    @Tool(description = "查询指定城市的当前天气情况，返回温度和天气状况")
    public String getCurrentWeather(String city) {
        int temp = ThreadLocalRandom.current().nextInt(-5, 35);
        String condition = CONDITIONS.get(ThreadLocalRandom.current().nextInt(CONDITIONS.size()));
        String result = String.format("%s 当前天气：%s，气温 %d°C", city, condition, temp);
        recorder.record("getCurrentWeather", city, result);
        return result;
    }
}
```

相比上一节，只是在方法返回前增加了一行 `recorder.record(...)`，把工具名、入参 city 和返回值记录下来。

最后改造 `/ai/tool` 接口，把返回值从 String 改为 Map，同时返回模型的最终答案和完整的工具调用过程：

``` java
@GetMapping(value = "/tool")
public Map<String, Object> tool(@RequestParam(value = "message", defaultValue = "北京和上海今天天气怎么样？") String message) {
    String answer = chatClient.prompt().user(message).tools(weatherService).call().content();
    return Map.of(
            "answer", answer != null ? answer : "",
            "toolCalls", toolCallRecorder.get()
    );
}
```

再次调用 `/ai/tool?message=北京和上海今天天气怎么样？`，返回结果里除了 answer，还多了一个 toolCalls 数组，里面记录了模型调用工具的完整过程：

``` json
{
  "answer": "北京当前多云，气温20°C；上海当前小雨，气温25°C。",
  "toolCalls": [
    {
      "tool": "getCurrentWeather",
      "arguments": "北京",
      "result": "北京 当前天气：多云，气温 20°C"
    },
    {
      "tool": "getCurrentWeather",
      "arguments": "上海",
      "result": "上海 当前天气：小雨，气温 25°C"
    }
  ]
}
```

从 toolCalls 可以清楚看到，模型针对北京和上海分别调用了一次 `getCurrentWeather`，每次的入参和返回值都被完整记录下来，这样我们就能直观地观察模型是如何使用工具的。
