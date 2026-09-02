{% raw %}
# SpringCamp 🏕️

> 30+ 个**可独立运行的 Spring Boot 实战示例**，每个模块配套中文技术博客 [springcamp.cn](https://springcamp.cn)。
> 不是文档堆，是能直接跑起来抄的作业。

[![Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/qihaiyan/springcamp/tree/main/LICENSE)
![GitHub stars](https://img.shields.io/github/stars/qihaiyan/springcamp)

## 这是什么

SpringCamp 把 Spring 生态里那些"看文档半天、搜博客一堆、真上手还是不会"的场景，做成**最小可运行示例**：clone 下来、跑起来、改两行就懂。
覆盖 Spring AI、Spring Security / OAuth2、Spring Cloud、Data、消息、缓存、并发等方向。

## 为什么用

- **能跑**：每个模块都是独立 Spring Boot 工程，不是代码片段。
- **有文**：每个示例都对应一篇 springcamp.cn 实战文章，代码+原理一起看。
- **够新**：紧跟 Spring Boot 新特性（HTTP Interface、RestClient、Spring AI、MCP 等）。

## 怎么跑

```bash
git clone https://github.com/qihaiyan/springcamp.git
cd springcamp/<模块目录>
./gradlew bootRun        # 按模块 README 的说明运行
````

## 模块索引

| 模块                                                                   | 功能                                               | 配套博客                                                               |
| -------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------ |
| [spring-ai-deepseek](https://github.com/qihaiyan/springcamp/tree/main/spring-ai-deepseek)                             | Spring AI 集成 DeepSeek（对话/流式/推理/Function Calling） | [文章](https://springcamp.cn/spring-ai-deepseek/)                    |
| [spring-mcp](https://github.com/qihaiyan/springcamp/tree/main/spring-mcp)                                             | Spring MCP（模型上下文协议）集成示例                          | —                                                                  |
| [spring-advanced-security](https://github.com/qihaiyan/springcamp/tree/main/spring-advanced-security)                 | Spring Security 高级用法（自定义登录/鉴权）                   | [文章](https://springcamp.cn/spring-advanced-security/)              |
| [spring-cloud-gateway](https://github.com/qihaiyan/springcamp/tree/main/spring-cloud-gateway)                         | Spring Cloud Gateway 网关示例                        | [文章](https://springcamp.cn/spring-cloud-gateway/)                  |
| [spring-kafka](https://github.com/qihaiyan/springcamp/tree/main/spring-kafka)                                         | Spring Kafka 消息示例                                | [文章](https://springcamp.cn/spring-kafka/)                          |
| [spring-cache](https://github.com/qihaiyan/springcamp/tree/main/spring-cache)                                         | Spring Cache 缓存抽象                                | [文章](https://springcamp.cn/spring-data-cache/)                     |
| [spring-aop](https://github.com/qihaiyan/springcamp/tree/main/spring-aop)                                             | Spring AOP 切面编程                                  | [文章](https://springcamp.cn/spring-boot-aop/)                       |
| [spring-data-flex-query](https://github.com/qihaiyan/springcamp/tree/main/spring-data-flex-query)                     | Spring Data 灵活查询（防 SQL 注入）                       | [文章](https://springcamp.cn/spring-data-flex-query/)                |
| [spring-data-jpa-multisource](https://github.com/qihaiyan/springcamp/tree/main/spring-data-jpa-multisource)           | Spring Data JPA 多数据源                             | [文章](https://springcamp.cn/spring-jpa-multi-datasource/)           |
| [spring-dynamic-datasource](https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-datasource)               | 动态数据源切换                                          | [文章](https://springcamp.cn/spring-dynamic-datasource/)             |
| [spring-dynamic-scheduler](https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-scheduler)                 | 动态定时任务管控                                         | [文章](https://springcamp.cn/spring-dynamic-scheduler/)              |
| [spring-http-interface](https://github.com/qihaiyan/springcamp/tree/main/spring-http-interface)                       | Spring Boot 3.2 HTTP Interface 声明式调用             | [文章](https://springcamp.cn/spring-boot-http-interface/)            |
| [spring-rest-client](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-client)                             | Spring Boot 3.2 RestClient                       | [文章](https://springcamp.cn/spring-boot-rest-client/)               |
| [spring-rest-template-log](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-template-log)                 | RestTemplate 调用与 DNS 超时配置                        | [文章](https://springcamp.cn/spring-resttemplate-dns-timeout/)       |
| [spring-rest-log-request-response](https://github.com/qihaiyan/springcamp/tree/main/spring-rest-log-request-response) | REST 请求/响应日志                                     | [文章](https://springcamp.cn/spring-rest-log-request-response/)      |
| [spring-modify-request-body](https://github.com/qihaiyan/springcamp/tree/main/spring-modify-request-body)             | 统一修改 RequestBody                                 | [文章](https://springcamp.cn/spring-controller-modify-request-body/) |
| [spring-sse](https://github.com/qihaiyan/springcamp/tree/main/spring-sse)                                             | Server-Sent Events 服务端推送                         | —                                                                  |
| [spring-native](https://github.com/qihaiyan/springcamp/tree/main/spring-native)                                       | Spring Native 原生镜像                               | [文章](https://springcamp.cn/spring-native/)                         |
| [spring-data-envers-conditional](https://github.com/qihaiyan/springcamp/tree/main/spring-data-envers-conditional)     | 条件化审计日志                                          | [文章](https://springcamp.cn/spring-data-conditional-auditing/)      |
| [spring-data-jdbc-client](https://github.com/qihaiyan/springcamp/tree/main/spring-data-jdbc-client)                   | Spring Data JDBC Client                          | [文章](https://springcamp.cn/spring-boot-jdbc-client/)               |
| [spring-easy-rule](https://github.com/qihaiyan/springcamp/tree/main/spring-easy-rule)                                 | Easy Rules 规则引擎                                  | [文章](https://springcamp.cn/easy-rules/)                            |
| [spring-groovy](https://github.com/qihaiyan/springcamp/tree/main/spring-groovy)                                       | 集成 Groovy 动态脚本                                   | [文章](https://springcamp.cn/spring-groovy/)                         |
| [spring-redis-resolver](https://github.com/qihaiyan/springcamp/tree/main/spring-redis-resolver)                       | 基于 Redis 的解析器                                    | [文章](https://springcamp.cn/spring-redis-resolver/)                 |
| [spring-localdatetime-epoch](https://github.com/qihaiyan/springcamp/tree/main/spring-localdatetime-epoch)             | LocalDateTime 与 Epoch 互转                         | [文章](https://springcamp.cn/spring-localdatetime-epoch/)            |
| [spring-taskexecutor-block](https://github.com/qihaiyan/springcamp/tree/main/spring-taskexecutor-block)               | TaskExecutor 阻塞行为                                | [文章](https://springcamp.cn/java-concurrent-thread-block/)          |
| [spring-unit-test](https://github.com/qihaiyan/springcamp/tree/main/spring-unit-test)                                 | Spring 单元测试                                      | [文章](https://springcamp.cn/spring-boot-unit-test/)                 |
| [elasticsearch-javaclient](https://github.com/qihaiyan/springcamp/tree/main/elasticsearch-javaclient)                 | Elasticsearch Java 客户端                           | [文章](https://springcamp.cn/elasticsearch-javaclient/)              |
| [java-concurrency](https://github.com/qihaiyan/springcamp/tree/main/java-concurrency)                                 | Java 并发编程                                        | [文章](https://springcamp.cn/java-concurrency/)                      |
| [utils](https://github.com/qihaiyan/springcamp/tree/main/utils)                                                       | 通用工具类                                            | —                                                                  |

> 完整文章列表见 [springcamp.cn](https://springcamp.cn)。


![Alt](https://repobeats.axiom.co/api/embed/f7755d6c54108961b98e66b3e26aa12467444763.svg "Repobeats analytics image")

### Supported by

[JetBrains](https://jb.gg/OpenSourceSupport)

![JetBrains Logo (Main) logo](https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.svg)
{% endraw %}
