---
layout: post
title:  "Implementing an MCP Server with Spring AI"
date:   2026-08-29 15:30:00 +0800
lang: en
slug_zh: spring-mcp
tags: [spring,java,ai,mcp,featured]
categories: [spring boot]
image: assets/images/spring-mcp.jpg
description: "Build an MCP Server with Spring AI: expose weather tools over SSE, register them declaratively or programmatically, and verify with the MCP Inspector."
---

MCP (Model Context Protocol) is an open protocol for connecting LLMs to external tools and data sources. Spring AI provides MCP server and client integrations, wrapping the protocol details into out-of-the-box starters. This post shows how to build an MCP Server based on Spring AI that exposes tools over SSE for MCP clients to call.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-mcp](https://github.com/qihaiyan/springcamp/tree/main/spring-mcp)

## 1. Overview

The MCP protocol defines two roles, server and client. The server provides concrete capabilities, such as querying the weather or operating on a database, while the client connects to the server and exposes the tools to the LLM; common MCP clients include Claude Desktop, Cursor, and others. Underneath, the protocol is based on JSON-RPC and abstracts over transports, with STDIO and SSE being the common ones. This example uses the SSE transport on top of WebMVC; once the server starts, clients connect through the `http://localhost:8080/sse` endpoint.

Under the MCP protocol, a server can expose three kinds of capabilities: tools, resources, and prompts, of which tools are the most commonly used. This example implements three tools: querying a weather forecast by latitude/longitude, querying weather alerts for a US state, and converting text to upper case. The weather data is randomly generated mock data, so no API key is required and there is no dependency on any external service — clone the project, start it, and it is ready to use.

## 2. Project Dependencies and Configuration

Add the Spring AI MCP server starter, implemented on top of WebMVC:

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

The starter auto-configures all the components an MCP server needs, including the SSE endpoints, the encoding and decoding of JSON-RPC messages, and tool registration and dispatch. We do not need to write any protocol-related code.

Configure the server in application.properties:

``` properties
server.port=8080
spring.ai.mcp.server.name=my-weather-server

# Server type (SYNC/ASYNC)
spring.ai.mcp.server.type=SYNC

spring.main.banner-mode=off
```

`spring.ai.mcp.server.name` is the name the server reports to the client during the handshake, and `spring.ai.mcp.server.type` selects synchronous or asynchronous mode, defaulting to SYNC. The SSE-related endpoints also have defaults: the SSE handshake endpoint is `/sse`, and after a client connects, the server announces the message endpoint and the session id through an endpoint event, defaulting to `/mcp/message`; this can be changed via `spring.ai.mcp.server.sse-message-endpoint`.

`spring.main.banner-mode=off` disables the startup banner. It is not required with the SSE transport used in this example, but with the STDIO transport the banner would be written to standard output, polluting the JSON-RPC message channel and making it unparseable for the client, so the banner must be turned off when using STDIO.

## 3. Two Ways to Register MCP Tools

Spring AI provides two ways to register Java methods as MCP tools, and the example project demonstrates both in its application class:

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

The first is declarative: `MethodToolCallbackProvider` registers WeatherService as a tool object, and Spring AI scans all methods annotated with `@Tool` in it, converting them into MCP tools automatically. This suits cases with many tool methods concentrated in one service.

The second is programmatic: `FunctionToolCallback.builder()` builds a single tool by hand, specifying in turn the tool name, the processing logic, the input type, and the description. The input type is defined with a record, from which Spring AI generates the JSON schema of the tool's arguments. This suits simple logic that does not warrant a dedicated class.

Beans registered either way are collected automatically by the starter and exposed to clients through the MCP protocol's `tools/list` and `tools/call`; clients do not need to distinguish how a tool was registered.

## 4. Implementing the Weather Query Tools

WeatherService provides two weather query tools. For ease of demonstration, the weather data is randomly generated mock data with no dependency on any external service:

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

The `@Tool` description is for the LLM: the model uses it to decide when to call the tool and what the parameters mean, so it should clearly describe the tool's purpose and parameter format.

The tool's return value is formatted plain text that is friendly to the LLM. The mock weather information includes the coordinates and state code from the input, making the tool call look more realistic. In a real project, the tool method could internally call a database, a third-party API, or any other data source — MCP only cares about the method's arguments and return value.

One easily overlooked detail: the parameter names of the `@Tool` method arguments are used to generate the JSON schema, so the `-parameters` compiler flag must be enabled to keep the method parameter names. Otherwise, the generated schema names the parameters arg0, arg1, and the model cannot pass arguments correctly. The example project enables this compiler flag globally in build.gradle:

``` groovy
tasks.withType(JavaCompile).configureEach {
    options.compilerArgs.add("-parameters")
}
```

## 5. Running and Verifying

Start the project:

``` bash
./gradlew :spring-mcp:bootRun
```

Once started, first establish an SSE connection and observe the handshake information returned by the server:

``` bash
curl -N http://localhost:8080/sse
```

The server returns something like the following; the endpoint event announces the message endpoint and the session id of this connection:

```
event: endpoint
data: /mcp/message?sessionId=6e3a1c2e-8f7b-4a5d-9c1e-2b3d4e5f6a7b
```

A more convenient way to verify the tools is the Inspector, the official MCP debugging tool:

``` bash
npx @modelcontextprotocol/inspector
```

In the Inspector UI, choose SSE as the transport type, enter `http://localhost:8080/sse` as the URL, and connect. The Tools panel then shows the three tools exposed by the server: getWeatherForecastByLocation, getAlerts, and toUpperCase. Just fill in the parameters and call them — for example, enter NY as the state and you will see the mock alert information returned by getAlerts.

Besides the MCP SSE endpoint, the example also implements a `/sse-mock` endpoint that uses an SseEmitter to push one message per second, ten messages in total, which helps you get a feel for the server-side push mechanism that MCP's SSE transport relies on:

``` bash
curl -N http://localhost:8080/sse-mock
```

With the MCP Server up and running, configure `http://localhost:8080/sse` as an SSE server in an MCP client such as Claude Desktop, and the LLM can call these weather tools during conversations.
