---
layout: post
title:  "SpringAI+TanStack AI实现流式AI聊天"
description: "介绍如何用 Spring AI 实现 AG-UI 协议的后端，与 TanStack AI（@tanstack/ai-react）前端对接，实现流式输出的 AI 聊天界面：多轮对话、中断生成、新会话，服务端无状态。"
date:   2026-10-29 15:30:00 +0800
tags: [spring,java,ai,react]
categories: [spring boot]
image: assets/images/spring-ai-tanstack-chat.png
---

之前的一篇文章介绍过用[htmx + Thymeleaf](https://springcamp.cn/spring-ai-htmx-chat/)实现流式聊天界面，全程不写前端框架、不做npm构建。如果想用React这样的主流前端栈，可以了解一下TanStack AI——TanStack团队（React Query、TanStack Table背后的团队）推出的AI应用前端框架，提供```useChat```等hook处理聊天状态，客户端与后端之间走AG-UI协议。本文介绍如何用Spring AI实现AG-UI协议的后端，与```@tanstack/ai-react```配合，实现与htmx版本相同的流式聊天效果。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-ai-tanstack-chat](https://github.com/qihaiyan/springcamp/tree/main/spring-ai-tanstack-chat)

## 一、概述

TanStack AI是TanStack团队推出的AI应用开发框架，```@tanstack/ai-react```是它的React绑定。它与后端通信的标准线协议是AG-UI（Agent-User Interaction Protocol），一个事件驱动的流式协议：一轮对话（run）由一组带类型的JSON事件描述，默认通过SSE传输。

```
data:{"type":"RUN_STARTED","threadId":"...","runId":"..."}
data:{"type":"TEXT_MESSAGE_START","messageId":"...","role":"assistant"}
data:{"type":"TEXT_MESSAGE_CONTENT","messageId":"...","delta":"你"}
data:{"type":"TEXT_MESSAGE_CONTENT","messageId":"...","delta":"好"}
data:{"type":"TEXT_MESSAGE_END","messageId":"..."}
data:{"type":"RUN_FINISHED","threadId":"...","runId":"..."}
```

每个token就是一条```TEXT_MESSAGE_CONTENT```事件，前端的```useChat```把delta增量拼进消息内容，React状态驱动渲染出逐字打字效果。后端只需要实现一个接口：解析请求、调用大模型的流式接口、把token包装成AG-UI事件返回。

与htmx版本相比，两个方案实现了同样的交互，但架构上有几处有意思的对比：

- **数据通道**：htmx版在SSE里传HTML片段，前端直接换入DOM；AG-UI版传结构化的JSON事件，前端自己渲染，前后端彻底解耦
- **会话记忆**：htmx版用Spring AI的ChatMemory在服务端记忆对话，是有状态的；AG-UI协议规定客户端每轮POST完整对话历史，服务端无状态，可以随意水平扩展
- **更新方式**：htmx版每个token推送累积全文做整段替换，天然免疫消息乱序；AG-UI版按delta增量拼接，消息量更小

实现的功能包括：

- AI回答通过SSE逐token流入气泡，带打字动画
- 多轮对话带上下文，客户端带回历史、服务端无状态
- 流式过程中可随时"停止"
- 一键新建会话
- 内置demo模式的本地假模型，无需API Key即可体验完整流程

技术栈版本：Spring Boot 4.1.1、Spring AI 2.0.1、```@tanstack/ai-react``` 1.0、React 19、Vite 8。

<!-- more -->

## 二、项目依赖与配置

后端只有两个依赖，deepseek starter和web starter：

``` groovy
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

模型配置与之前的spring-ai-deepseek示例一致，api-key支持通过环境变量注入：

``` properties
spring.ai.deepseek.api-key=${DEEPSEEK_API_KEY:<your-api-key>}
spring.ai.deepseek.chat.model=deepseek-v4-flash
spring.ai.deepseek.chat.temperature=0.7
```

前端是一个标准的Vite + React工程，依赖```@tanstack/ai-react```：

``` json
"dependencies": {
    "@tanstack/ai": "^1.0.0",
    "@tanstack/ai-react": "^1.0.0",
    "react": "^19.3.1",
    "react-dom": "^19.3.1"
}
```

开发阶段通过vite的proxy把```/api```代理到Spring后端，前端同源调用，不需要处理CORS：

``` typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
```

## 三、配置ChatClient：服务端无状态

htmx版本的多轮对话依靠服务端的ChatMemory，每次提问由advisor自动组装历史消息。AG-UI协议下不需要了——协议规定客户端每轮都会携带完整对话历史，服务端只要把历史原样转给大模型即可，因此ChatClient上没有任何记忆相关的配置：

``` java
@Bean
public ChatClient chatClient(ChatClient.Builder builder, Environment env) {
    // AG-UI 协议下每轮请求都会带上完整对话历史（messages 字段），服务端无需再维护 ChatMemory
    ChatClient.Builder target = env.acceptsProfiles(Profiles.of("demo"))
            ? ChatClient.builder(demoChatModel())   // demo 模式：无需 API Key 的本地假模型
            : builder;
    return target
            .defaultSystem("你是 springcamp 示例项目的 AI 助手，请用简洁准确的中文回答问题。")
            .build();
}
```

服务端无状态带来一个实际的好处：部署多个实例时不需要粘性会话，任何实例都能处理任何一轮请求。

demo模式的假模型与htmx版本完全相同：把一段固定回复按码点逐字吐出，每个字间隔40毫秒，模拟真实的流式输出，在demo profile下替换掉真实的DeepSeek模型。这样体验完整交互流程不需要API Key，本文不再重复这段代码。

## 四、单接口实现AG-UI事件流

整个聊天只有一个接口，POST /api/chat，返回值是SSE流。请求体是AG-UI规范的```RunAgentInput```结构，用两个record定义：

``` java
record RunAgentInput(String threadId, String runId, List<WireMessage> messages) {
    record WireMessage(String id, String role, String content) {
    }
}
```

处理过程分三段：先发```RUN_STARTED```和```TEXT_MESSAGE_START```两条头事件，然后把大模型的token流逐个包装成```TEXT_MESSAGE_CONTENT```事件，最后补上```TEXT_MESSAGE_END```和```RUN_FINISHED```两条尾事件：

``` java
@PostMapping(value = "/api/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<String>> chat(@RequestBody RunAgentInput input) {
    String messageId = "msg-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

    Flux<ServerSentEvent<String>> header = Flux.just(
            event(AgUiEvent.runStarted(input.threadId(), input.runId())),
            event(AgUiEvent.textMessageStart(messageId)));

    Flux<ServerSentEvent<String>> tokens = chatClient.prompt()
            .messages(toSpringMessages(input.messages()))
            .stream()
            .content()
            .map(delta -> event(AgUiEvent.textMessageContent(messageId, delta)));

    Flux<ServerSentEvent<String>> tail = Flux.just(
            event(AgUiEvent.textMessageEnd(messageId)),
            event(AgUiEvent.runFinished(input.threadId(), input.runId())));

    // 中途出错时补一个 RUN_ERROR 终止事件，客户端据此结束本轮并展示错误
    return Flux.concat(header, tokens, tail)
            .onErrorResume(ex -> Flux.just(event(AgUiEvent.runError(rootMessage(ex)))));
}
```

客户端送来的消息是AG-UI的wire格式（id/role/content），转换成Spring AI的```Message```时只保留user和assistant两种角色，并且只回看最近20条，防止超长对话把prompt无限撑大：

``` java
static List<Message> toSpringMessages(List<RunAgentInput.WireMessage> messages) {
    if (messages == null) {
        return List.of();
    }
    return messages.stream()
            .skip(Math.max(0, messages.size() - 20))
            .map(m -> "assistant".equals(m.role())
                    ? (Message) new AssistantMessage(m.content())
                    : (Message) new UserMessage(m.content()))
            .toList();
}
```

AG-UI事件的JSON字段都是短字符串，手写拼接反而让线格式一目了然，唯一要注意的是必须对token做JSON转义，引号、换行这些字符不转义会直接破坏SSE消息的结构：

``` java
static String textMessageContent(String messageId, String delta) {
    return "{\"type\":\"TEXT_MESSAGE_CONTENT\",\"messageId\":\"" + esc(messageId)
            + "\",\"delta\":\"" + esc(delta) + "\"}";
}

private static String esc(String s) {
    return s == null ? "" : s.replace("\\", "\\\\").replace("\"", "\\\"")
            .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
}
```

出错处理上，大模型调用失败时通过```onErrorResume```补发一条```RUN_ERROR```事件，```rootMessage```沿着异常链取根因信息。客户端收到后结束本轮并在界面上展示错误，SSE流正常收尾，不会把连接挂死。

## 五、前端：useChat与React渲染

前端的核心是```useChat```这个hook，通过```fetchServerSentEvents```连接后端接口：

``` typescript
const { messages, sendMessage, isLoading, stop, error } = useChat({
  connection: fetchServerSentEvents('/api/chat'),
  threadId,
})
```

```useChat```返回的```messages```是UI消息数组，发送消息调用```sendMessage(text)```，它会把用户消息和完整对话历史按AG-UI协议POST给后端；响应流里的```TEXT_MESSAGE_CONTENT```事件被自动增量拼进最后一条assistant消息的parts，React状态更新，气泡内容逐字增长——全程没有任何手工操作DOM的代码。```isLoading```在流式期间为true，此时输入框锁定、"发送"按钮切换为"停止"，点击调用```stop()```中断请求。

消息气泡的渲染就是把parts里的text段拼接出来：

``` typescript
function MessageBubble({ message }: { message: UIMessage }) {
  const text = message.parts.map((part) => (part.type === 'text' ? part.content : '')).join('')
  const isUser = message.role === 'user'
  // assistant 消息已开始但第一个 token 未到时，气泡内先显示打字动画
  const showTyping = !isUser && !text

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="avatar">{isUser ? '我' : 'AI'}</div>
      <div className="bubble">
        {text}
        {showTyping && (
          <span className="typing-dots"><i /><i /><i /></span>
        )}
      </div>
    </div>
  )
}
```

"新建会话"利用了```threadId```：```useChat```按threadId维护独立的会话状态，换一个threadId即是一段全新的对话。实现上把threadId放在state里，用它作为组件的key触发重挂载：

``` typescript
const [threadId, setThreadId] = useState(() => crypto.randomUUID())

return (
  <Chat key={threadId} threadId={threadId}
        onNewThread={() => setThreadId(crypto.randomUUID())} />
)
```

与htmx版本对比一下很有意思：htmx版新建会话时要调DELETE接口清空服务端记忆，AG-UI版什么都不用做——服务端本来就没有状态，换掉threadId客户端消息列表清空即可。

## 六、运行与测试

体验完整交互不需要API Key，使用demo模式启动后端：

``` bash
./gradlew :spring-ai-tanstack-chat:bootRun --args='--spring.profiles.active=demo'
```

接入真实的大模型时，配置好api-key后正常启动，然后另开一个终端启动前端：

``` bash
cd spring-ai-tanstack-chat/frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 ，输入任意问题，可以看到回答逐字流入气泡；连续追问"我刚才问了什么"，模型能正确回答上文内容——上下文来自客户端每轮带回的历史，说明AG-UI的多轮机制生效；流式过程中点击"停止"，回答立即中断；点击"新建会话"后开始一段全新的对话。

后端测试同样不需要真实API Key，用```@MockitoBean```替换```DeepSeekChatModel```，重点验证三件事：一是事件顺序符合协议约定（```RUN_STARTED```在```TEXT_MESSAGE_START```之前、结尾有```RUN_FINISHED```）；二是多轮历史被完整转发给大模型（捕获传给```stream```的```Prompt```，断言非system消息正好是请求里的3条）；三是上游异常时客户端能收到```RUN_ERROR```事件而不是挂起的连接：

``` java
@MockitoBean
DeepSeekChatModel chatModel;

@Test
void chatStreamsAgUiEvents() {
    when(chatModel.stream(any(Prompt.class))).thenReturn(Flux.just(
            chatResponse("你好"), chatResponse("，世界")));

    client.post().uri("/api/chat")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue("""
                    {"threadId":"t1","runId":"r1","messages":[
                      {"id":"m1","role":"user","content":"你好"}]}
                    """)
            .exchange()
            .expectStatus().isOk()
            .expectHeader().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM)
            .expectBody(String.class)
            .value(body -> {
                assertThat(body.indexOf("RUN_STARTED")).isLessThan(body.indexOf("TEXT_MESSAGE_START"));
                assertThat(body).contains("\"delta\":\"你好\"");
                assertThat(body).contains("TEXT_MESSAGE_END");
                assertThat(body).contains("RUN_FINISHED");
            });
}
```

整个前后端链路（协议事件序列、多轮上下文、异常路径）都能在CI中验证，不依赖任何外部服务。
