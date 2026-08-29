---
layout: post
title:  "Spring AI实现MCP Server"
date:   2026-08-29 15:30:00 +0800
tags: [spring,java,ai,mcp]
categories: [spring boot]
image: assets/images/spring-mcp.jpg
---

MCP（Model Context Protocol）是一个开放协议，用于让大模型连接外部的工具和数据源，Spring AI提供了MCP的server和client集成，把协议细节封装成开箱即用的starter，本文介绍如何基于Spring AI开发一个MCP Server，通过SSE对外暴露工具，供MCP客户端调用。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-mcp](https://github.com/qihaiyan/springcamp/tree/main/spring-mcp)

## 一、概述

MCP协议定义了server和client两种角色，server负责提供具体的能力，比如查询天气、操作数据库，client负责连接server并把工具暴露给大模型使用，常见的MCP客户端有Claude Desktop、Cursor等。协议底层基于JSON-RPC，对传输方式做了抽象，常用的有STDIO和SSE两种，本示例基于webmvc使用SSE传输，server启动后通过 `http://localhost:8080/sse` 端点接入。

在MCP协议中，server可以对外提供tools、resources、prompts三类能力，其中tools是最常用的一类，本示例实现了三个工具：根据经纬度查询天气预报、查询美国某个州的气象预警、把文本转换为大写。其中天气数据为随机生成的mock数据，不需要申请api-key，不依赖任何外部服务，整个项目克隆下来启动即可使用。

## 二、项目依赖与配置

引入spring-ai的mcp server starter，基于webmvc实现：

``` groovy
ext {
    set('springAiVersion', "2.0.0")
}

dependencies {
    implementation 'org.springframework.ai:spring-ai-starter-mcp-server-webmvc'
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.ai:spring-ai-bom:${springAiVersion}"
    }
}
```

starter会自动配置好MCP server所需的全部组件，包括SSE端点、JSON-RPC消息的编解码和工具的注册分发，我们不需要编写任何协议相关的代码。

在application.properties中对server进行配置：

``` properties
server.port=8080
spring.ai.mcp.server.name=my-weather-server

# Server type (SYNC/ASYNC)
spring.ai.mcp.server.type=SYNC

spring.main.banner-mode=off
```

`spring.ai.mcp.server.name` 是server在握手时上报给客户端的名称，`spring.ai.mcp.server.type` 指定同步还是异步模式，默认为SYNC。SSE相关的端点也有默认值，SSE握手端点为 `/sse`，客户端建立连接后，server会通过endpoint事件告知消息端点及会话id，默认为 `/mcp/message`，可以通过 `spring.ai.mcp.server.sse-message-endpoint` 修改。

`spring.main.banner-mode=off` 关闭启动banner，在示例的SSE传输下不是必须的，但如果使用STDIO传输，banner会输出到标准输出，污染JSON-RPC消息通道，导致客户端无法解析，所以使用STDIO时必须关闭banner。

## 三、注册MCP Tool的两种方式

spring-ai提供了两种把java方法注册为MCP工具的方式，示例项目在启动类中同时演示了这两种方式：

``` java
@SpringBootApplication
public class McpServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(McpServerApplication.class, args);
    }

    @Bean
    public ToolCallbackProvider weatherTools(WeatherService weatherService) {
        return MethodToolCallbackProvider.builder().toolObjects(weatherService).build();
    }

    public record TextInput(String input) {
    }

    @Bean
    public ToolCallback toUpperCase() {
        return FunctionToolCallback.builder("toUpperCase", (TextInput input) -> input.input().toUpperCase())
                .inputType(TextInput.class)
                .description("Put the text to upper case")
                .build();
    }
}
```

第一种是声明式，通过 `MethodToolCallbackProvider` 把 WeatherService 注册为工具对象，spring-ai会扫描其中所有带 `@Tool` 注解的方法，自动转换为MCP工具，适合工具方法比较多、集中在一个service中的场景。

第二种是编程式，通过 `FunctionToolCallback.builder()` 手工构造单个工具，依次指定工具名、处理逻辑、输入类型和描述，输入类型用一个record定义，spring-ai会根据它生成工具入参的json schema，适合逻辑简单、不值得单独建一个类的场景。

两种方式注册的bean都会被starter自动收集，通过MCP协议的 `tools/list` 和 `tools/call` 暴露给客户端，客户端无需区分工具是用哪种方式注册的。

## 四、实现天气查询工具

WeatherService 提供了两个天气查询工具，为了便于演示，天气数据使用mock数据随机生成，不依赖任何外部服务：

``` java
@Service
public class WeatherService {

    private static final String[] CONDITIONS = {"晴", "多云", "小雨", "小雪"};
    private static final String[] WIND_DIRECTIONS = {"东风", "南风", "西风", "北风"};
    private static final String[] ALERT_EVENTS = {"暴雨橙色预警", "高温黄色预警", "大风蓝色预警", "寒潮蓝色预警"};
    private static final String[] SEVERITIES = {"低", "中等", "高", "严重"};

    @Tool(description = "Get weather forecast for a specific latitude/longitude")
    public String getWeatherForecastByLocation(double latitude, double longitude) {
        StringBuilder forecast = new StringBuilder(String.format("坐标（%s, %s）未来三天预报：\n", latitude, longitude));
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int day = 1; day <= 3; day++) {
            forecast.append(String.format("""
                    第%d天:
                    温度: %d°C
                    风力: %d级 %s
                    天气: %s
                    """, day, random.nextInt(-5, 36), random.nextInt(1, 9),
                    WIND_DIRECTIONS[random.nextInt(WIND_DIRECTIONS.length)],
                    CONDITIONS[random.nextInt(CONDITIONS.length)]));
        }
        return forecast.toString();
    }

    @Tool(description = "Get weather alerts for a US state. Input is Two-letter US state code (e.g. CA, NY)")
    public String getAlerts(String state) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        String event = ALERT_EVENTS[random.nextInt(ALERT_EVENTS.length)];
        return String.format("""
                Event: %s
                Area: %s
                Severity: %s
                Description: %s 生效中，请注意防范。
                """, event, state, SEVERITIES[random.nextInt(SEVERITIES.length)], event);
    }
}
```

`@Tool` 的description是给大模型看的，模型根据它来判断什么时候该调用这个工具、参数是什么含义，所以要描述清楚工具的用途和参数格式。

工具的返回值是对大模型友好的格式化纯文本，mock数据生成的天气信息会带上入参中的坐标和州代码，让工具调用看起来更加真实。在实际项目中，工具方法内部可以是调用数据库、第三方接口等任意数据源，MCP只关心方法的入参和返回值。

还有一个容易被忽略的细节，`@Tool` 方法入参的参数名会用于生成json schema，编译时需要开启 `-parameters` 参数保留方法参数名，否则生成的schema里参数名会变成arg0、arg1，模型无法正确传参。示例项目在build.gradle中全局开启了这个编译参数：

``` groovy
tasks.withType(JavaCompile).configureEach {
    options.compilerArgs.add("-parameters")
}
```

## 五、运行与验证

启动项目：

``` bash
./gradlew :spring-mcp:bootRun
```

启动后先建立一个SSE连接，观察server返回的握手信息：

``` bash
curl -N http://localhost:8080/sse
```

server会返回类似下面的内容，endpoint事件告知了消息端点和本次会话的id：

```
event: endpoint
data: /mcp/message?sessionId=6e3a1c2e-8f7b-4a5d-9c1e-2b3d4e5f6a7b
```

验证工具更方便的方式是使用MCP官方提供的调试工具Inspector：

``` bash
npx @modelcontextprotocol/inspector
```

在Inspector的界面中，Transport类型选择SSE，URL填写 `http://localhost:8080/sse`，连接后可以在Tools面板中看到server暴露的三个工具：getWeatherForecastByLocation、getAlerts和toUpperCase，直接填入参数调用即可，比如state填入NY，就能看到getAlerts返回的模拟预警信息。

除了MCP的SSE端点，示例中还实现了一个 `/sse-mock` 接口，用SseEmitter每秒推送一条消息，共推送10条，可以用来直观了解MCP的SSE传输所依赖的服务端推送机制：

``` bash
curl -N http://localhost:8080/sse-mock
```

搭建好MCP Server后，在Claude Desktop等MCP客户端中以SSE方式配置 `http://localhost:8080/sse`，大模型就可以在对话中调用这些天气工具了。
