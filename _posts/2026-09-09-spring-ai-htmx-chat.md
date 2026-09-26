---
layout: post
title:  "SpringAI+DeepSeek+HTMX实现AI Agent"
date:   2026-09-09 15:30:00 +0800
tags: [spring,java,ai,htmx]
categories: [spring boot]
image: assets/images/spring-ai-htmx-chat.jpg
---

实现一个AI Agent界面，常见的做法是前端用React或Vue搭建工程，通过npm构建打包，再对接后端的流式接口。其实借助htmx和Thymeleaf，不写前端框架、不做npm构建，纯服务端渲染HTML片段也能实现类ChatGPT的逐字打字效果。本文介绍如何用Spring AI结合HTMX和Alpine.js实现一个带多轮对话记忆的流式聊天界面。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-ai-htmx-chat](https://github.com/qihaiyan/springcamp/tree/main/spring-ai-htmx-chat)

## 一、概述

htmx是一个通过HTML属性完成ajax请求和局部HTML交换的轻量库，htmx 4基于fetch重写，自带的sse扩展可以直接消费普通请求返回的 `text/event-stream` 响应，把每条SSE消息当作一次局部HTML交换，这个特性正好契合大模型的流式输出。Alpine.js是一个声明式的轻量前端库，负责输入框、按钮状态这类纯客户端的交互逻辑。

整个项目的职责划分非常清晰：htmx负责数据通道，Alpine.js负责客户端状态，Thymeleaf负责HTML片段渲染，Spring AI负责模型调用与会话记忆，四个关注点互不耦合。实现的功能包括：

- AI回答通过SSE逐token流入页面，带打字动画
- 多轮对话带上下文记忆，按会话id隔离
- 一键新建会话，同时清空服务端记忆
- 内置demo模式的本地假模型，无需API Key即可体验完整流程

## 二、项目依赖与配置

引入spring-ai的deepseek starter和thymeleaf starter，整个模块只有三个依赖：

``` groovy
dependencies {
    implementation 'org.springframework.ai:spring-ai-starter-model-deepseek'
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-thymeleaf'
}
```

thymeleaf starter在这里的作用不只是渲染页面，控制器还会直接注入 TemplateEngine 在接口内部渲染HTML片段，作为SSE消息的内容返回。

模型配置与之前的spring-ai-deepseek示例一致，api-key支持通过环境变量注入：

``` properties
spring.ai.deepseek.api-key=${DEEPSEEK_API_KEY:<your-api-key>}
spring.ai.deepseek.chat.model=deepseek-v4-flash
spring.ai.deepseek.chat.temperature=0.7
```

前端资源方面，htmx和Alpine.js都走CDN引入，不依赖任何npm构建，样式是一个手写的CSS文件，整个static目录没有一行自定义JS。

## 三、配置ChatClient与会话记忆

多轮对话的关键在于服务端要记住之前的对话内容，spring-ai提供了 ChatMemory 抽象，我们使用内存版的滑动窗口实现，每个会话保留最近20条消息：

``` java
@Bean
public ChatMemory chatMemory() {
    return MessageWindowChatMemory.builder().maxMessages(20).build();
}

@Bean
public ChatClient chatClient(ChatClient.Builder builder, ChatMemory chatMemory, Environment env) {
    ChatClient.Builder target = env.acceptsProfiles(Profiles.of("demo"))
            ? ChatClient.builder(demoChatModel())
            : builder;
    return target
            .defaultSystem("你是 springcamp 示例项目的 AI 助手，请用简洁准确的中文回答问题。")
            .defaultAdvisors(MessageChatMemoryAdvisor.builder(chatMemory).build())
            .build();
}
```

在ChatClient上通过 `defaultAdvisors` 挂载 MessageChatMemoryAdvisor 后，记忆能力对所有请求全局生效，每次提问advisor会自动把该会话的历史消息组装进prompt，模型的回答也会自动存回记忆。

为了让项目在没有API Key的情况下也能跑通完整流程，我们实现了一个demo模式的假模型，在demo profile下替换掉真实的DeepSeek模型：

``` java
@Override
public Flux<ChatResponse> stream(Prompt prompt) {
    String reply = demoReply(prompt);
    return Flux.fromStream(reply.codePoints().mapToObj(cp -> new String(Character.toChars(cp))))
            .delayElements(Duration.ofMillis(40))
            .map(ChatConfig::chatResponse);
}
```

假模型把一段固定回复按码点逐字吐出，每个字间隔40毫秒，模拟真实的逐token流式输出。按码点而不是按字符拆分是为了中文安全，不会把emoji等增补字符拆出乱码。

## 四、单接口实现流式聊天

整个聊天只有一个接口，POST /chat 的返回值是一个SSE流，同时承担了两种职责：第一条消息是页面的HTML片段，之后每条消息是AI回答的token：

``` java
@PostMapping(produces = MediaType.TEXT_EVENT_STREAM_VALUE)
@ResponseBody
public Flux<ServerSentEvent<String>> chat(@RequestParam String message, @RequestParam String conversationId) {
    String answerId = "ans-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

    Context context = new Context(null, Map.of("message", message, "answerId", answerId));
    String skeleton = templateEngine.process("fragments/chat", Set.of("div.exchange"), context);

    StringBuilder answer = new StringBuilder();
    return Flux.concat(
            Flux.just(textEvent(skeleton)),
            chatClient.prompt()
                    .user(message)
                    .advisors(a -> a.param(ChatMemory.CONVERSATION_ID, conversationId))
                    .stream()
                    .content()
                    .map(ChatController::escapeHtml)
                    .onErrorResume(ex -> Flux.just("\n\n⚠️ AI 调用失败：" + escapeHtml(rootMessage(ex))))
                    .doOnNext(answer::append)
                    .map(token -> partialEvent(answerId, answer.toString())));
}
```

这个接口的返回值用 `Flux.concat` 拼接了两段流。第一段只有一条消息，内容是用 TemplateEngine 渲染的一轮对话骨架，`process` 方法的第二个参数传入了markup selector，可以直接按css选择器渲染 fragments/chat.html 中指定的片段，不需要走控制器返回视图名那套路由。

第二段是大模型的流式输出，有几个值得注意的细节。会话id通过 `ChatMemory.CONVERSATION_ID` 参数按请求传入，同一个 ChatMemory Bean就能按id隔离多个会话。由于SSE的data会被htmx当作HTML换入页面，模型输出的每个token都要先经过 `escapeHtml` 转义，而且转义发生在 `doOnNext(answer::append)` 之前，保证累积下来的文本也是转义后的。调用出错时通过 `onErrorResume` 把根因错误信息追加进流内，错误也会渲染到聊天气泡里。

后续每条SSE消息的内容是一个 `<hx-partial>` 片段：

``` java
private static ServerSentEvent<String> partialEvent(String answerId, String html) {
    return ServerSentEvent.<String>builder()
            .data("<hx-partial hx-target=\"#" + answerId + "\" hx-swap=\"innerHTML\">" + html + "</hx-partial>")
            .build();
}
```

`hx-partial` 是htmx 4新增的元素，可以在SSE流内做定向替换，这里指定替换目标为AI气泡的id。注意每个token推送的都是累积后的全文，整段替换而不是增量拼接，天然免疫SSE消息乱序或丢失的问题。

另外接口还提供了DELETE方法，按会话id清空服务端记忆，配合前端的"新建会话"功能：

``` java
@DeleteMapping
@ResponseBody
public void clear(@RequestParam String conversationId) {
    chatMemory.clear(conversationId);
}
```

## 五、页面与交互

聊天页面的核心是这个表单，htmx负责发请求，Alpine.js负责交互状态：

``` html
<form class="composer" hx-ext="sse" hx-post="/chat" hx-target="#messages" hx-swap="beforeend"
      @htmx:before:request="start()"
      @htmx:finally:request="sent()"
      @htmx:sse:error.window="busy = false">
    <input type="hidden" name="conversationId" :value="conversationId">
    <textarea name="message" x-ref="input" x-model="input" rows="1"
              placeholder="输入消息，Enter 发送…" @keydown.enter="onEnter($event)"></textarea>
    <button type="submit" class="btn-send" :disabled="!canSend" :class="{ sending: busy }">
        <span x-text="busy ? '回答中…' : '发送'">发送</span>
    </button>
</form>
```

表单上 `hx-ext="sse"` 启用sse扩展，`hx-post` 提交表单，响应作为SSE流消费。会话id在浏览器端用 `crypto.randomUUID()` 生成，通过隐藏域随表单提交。

一轮对话的骨架片段定义在 fragments/chat.html 中，就是第4节里接口渲染的那段模板：

``` html
<div th:fragment="exchange(message, answerId)" class="exchange">
    <div class="message user">
        <div class="bubble" th:text="${message}">用户消息</div>
    </div>
    <div class="message assistant">
        <div class="bubble">
            <span class="bubble-text" th:id="${answerId}">
                <span class="typing-dots"><i></i><i></i><i></i></span>
            </span>
        </div>
    </div>
</div>
```

用户气泡通过 `th:text` 输出，天然防XSS。AI气泡初始内容是三个点的打字动画，并且带有服务端生成的唯一id，第一个token到达时会被 `hx-partial` 的innerHTML替换掉，打字动画自然消失，不需要任何额外的JS控制。

Alpine.js组件监听htmx的事件来驱动UI状态：

``` javascript
function chatApp() {
    return {
        busy: false,
        input: '',
        conversationId: crypto.randomUUID(),

        start() {
            this.busy = true;    // 锁定发送按钮
            this.input = '';     // 清空输入框
        },
        sent() {
            this.busy = false;   // SSE流结束后才解锁
        },
        scrollBottom() {
            const box = document.getElementById('messages');
            box.scrollTo({ top: box.scrollHeight, behavior: 'instant' });
        },
        newChat() {
            const old = this.conversationId;
            this.conversationId = crypto.randomUUID();
            this.count = 0;
            this.busy = false;
            this.input = '';
            document.querySelectorAll('#messages .message').forEach(n => n.remove());
            fetch('/chat?conversationId=' + encodeURIComponent(old), { method: 'DELETE' });
        }
    }
}
```

这里有个htmx 4的细节，默认配置下SSE响应要等到流彻底结束才触发 `htmx:finally:request` 事件，所以busy锁天然覆盖整个回答过程，流式期间无法重复提交，不需要手动管理连接的开关。

## 六、运行与验证

体验完整交互不需要API Key，使用demo模式启动，界面上AI的回答由内置假模型逐字吐出：

``` bash
./gradlew :spring-ai-htmx-chat:bootRun --args='--spring.profiles.active=demo'
```

接入真实的大模型时，配置好api-key后正常启动即可：

``` bash
./gradlew :spring-ai-htmx-chat:bootRun
```

浏览器打开 http://localhost:8080 ，输入任意问题，可以看到回答像打字一样逐字流出；连续追问"我刚才问了什么"，模型能正确回答上文内容，说明多轮记忆生效；点击"新建会话"后，上下文被清空，开始一段全新的对话。

项目的测试同样不需要真实API Key，集成测试中用 `@MockitoBean` 替换 DeepSeekChatModel，把流式输出桩成两段固定内容，然后断言SSE响应中依次包含对话骨架和逐token累积的 `hx-partial` 片段，整个前后端交互链路都能在CI中验证。
