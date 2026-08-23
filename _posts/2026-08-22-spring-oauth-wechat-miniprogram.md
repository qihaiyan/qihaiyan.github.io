---
layout: post
title:  "通过Spring Authorization Server对微信小程序应用进行授权防护"
date:   2026-08-22 15:30:00 +0800
tags: [spring,java,oauth2,wechat]
categories: [spring boot]
image: assets/images/spring-oauth-wechat-miniprogram.jpg
---

微信小程序是一种典型的原生客户端应用：没有浏览器地址栏，无法完成 OAuth2 授权码流程所依赖的重定向交互；代码包可以被反编译，客户端没有安全存放密钥的地方，标准的授权码流程并不能直接套用。本文介绍如何利用 Spring Authorization Server 的扩展授权类型（Extension Grant）机制，为小程序定制一个 `wechat-code` 授权模式，用 `wx.login()` 产生的 code 换取标准的 OAuth2 令牌，实现对后端资源的统一授权防护。

具体的代码参照 [示例项目 https://github.com/qihaiyan/ng-boot-oauth](https://github.com/qihaiyan/ng-boot-oauth)

## 一、概述

微信小程序的授权防护面临几个特殊问题：

1. **无法重定向**：授权码流程要求客户端引导用户浏览器跳转到授权服务器，而小程序运行在微信的容器里，没有标准的浏览器环境（`web-view` 内嵌页面体验差且限制多）。
2. **无法保密**：小程序代码包随安装分发，可以被反编译，任何写死在代码里的 secret 都会泄露，所以小程序只能作为公开客户端（public client）。
3. **微信登录不等于接口防护**：`wx.login()` 只解决"微信身份"问题，自己的后端接口的访问控制、令牌生命周期管理、多端统一认证，仍然需要一套标准的 OAuth2 令牌体系。

本文的方案是：用微信官方的 `wx.login()` 完成用户认证，用 Spring Authorization Server 的**扩展授权类型**机制定制一个 `wechat-code` 授权模式完成令牌签发。整体思路：

- 小程序调用 `wx.login()` 拿到一次性临时 code；
- 小程序把 code 提交到授权服务器的 `/oauth2/token` 端点（grant_type 为自定义的 `wechat-code`）；
- 授权服务器拿着 code 调用微信的 `jscode2session` 接口换取 `openid`，加载（或自动注册）对应的用户；
- 授权服务器签发标准的 `access_token`（JWT）和 `refresh_token`；
- 小程序后续请求携带 `Bearer` 令牌访问资源服务器，资源服务器本地校验 JWT，完全无状态。

这样微信登录与令牌体系解耦，资源服务器不感知微信，仍然是标准的 OAuth2 防护。

## 二、核心交互流程

```
微信小程序                      授权服务器 authserver               微信开放平台
    |                                  |                                |
    |--- wx.login() 获取临时 code ------------------------------------->|
    |<-- code ---------------------------------------------------------|
    |                                  |                                |
    |--- POST /oauth2/token --------->|                                |
    |    grant_type=wechat-code       |--- jscode2session ------------->|
    |    client_id=miniapp-client     |    (appid, secret, code)       |
    |    code=xxx                     |<-- openid / session_key --------|
    |                                  |                                |
    |                                  |  根据 openid 加载(或注册)用户     |
    |                                  |  生成 access_token/refresh_token|
    |<-- access_token / refresh_token |                                |
    |                                  |                                |
    |--- GET /api/messages ---------->|  资源服务器本地校验 JWT           |
    |    Authorization: Bearer xxx    |                                |

 access_token 过期后：
    |--- POST /oauth2/token --------->|  标准的 refresh_token 授权       |
    |<-- 新的 access_token / refresh_token ------------------------------|
```

流程中的几个关键点：

- 微信的 code 是**一次性**的，有效期约 5 分钟，天然防重放；
- `appid` 和 `secret` 只保存在 authserver 端，小程序不持有任何密钥；
- `access_token` 是自包含的 JWT，资源服务器不查库、不调 authserver，即可完成校验；
- token 过期后走标准的 `refresh_token` 授权续期，Spring Authorization Server 刷新时会自动轮换（rotation）refresh_token。

## 三、authserver端：实现扩展授权类型

Spring Authorization Server 是一个开发库而不是开箱即用的服务，它原生支持授权码、客户端凭证、刷新令牌这几个标准授权类型，同时提供了扩展机制：通过自定义 `AuthenticationConverter` 和 `AuthenticationProvider`，就能增加自己的授权类型，接入 `/oauth2/token` 这个标准端点。

### 1. 定义授权类型

grant_type 采用 RFC 推荐的 URN 格式，避免与标准类型冲突：

``` java
public final class WechatGrantTypes {

    /**
     * 微信小程序登录授权类型
     */
    public static final String WECHAT_CODE = "urn:springcamp:params:oauth:grant-type:wechat-code";

    private WechatGrantTypes() {
    }
}
```

### 2. 自定义 Authentication 令牌

继承 `OAuth2AuthorizationGrantAuthenticationToken`，把微信 code 作为显式字段保存：

``` java
public class WechatCodeGrantAuthenticationToken extends OAuth2AuthorizationGrantAuthenticationToken {

    private final String code;

    public WechatCodeGrantAuthenticationToken(String code, Authentication clientPrincipal,
            Map<String, Object> additionalParameters) {
        super(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE), clientPrincipal, additionalParameters);
        this.code = code;
    }

    public String getCode() {
        return this.code;
    }
}
```

### 3. Converter：从请求中提取参数

token 端点收到请求后，先由 `AuthenticationConverter` 把 HTTP 请求转换成上一步的 Authentication。注意 `grant_type` 不匹配时要返回 `null`，这样框架会继续尝试其它转换器，不影响标准的授权码、刷新令牌流程：

``` java
public class WechatCodeGrantAuthenticationConverter implements AuthenticationConverter {

    @Override
    public Authentication convert(HttpServletRequest request) {
        String grantType = request.getParameter(OAuth2ParameterNames.GRANT_TYPE);
        if (!WechatGrantTypes.WECHAT_CODE.equals(grantType)) {
            return null;
        }

        // clientPrincipal 是 ClientAuthenticationFilter 认证后的客户端身份
        Authentication clientPrincipal = SecurityContextHolder.getContext().getAuthentication();

        Map<String, Object> additionalParameters = new HashMap<>();
        request.getParameterNames().forEach(parameter -> {
            if (!parameter.equals(OAuth2ParameterNames.GRANT_TYPE)
                    && !parameter.equals(OAuth2ParameterNames.CLIENT_ID)
                    && !parameter.equals(OAuth2ParameterNames.CODE)) {
                additionalParameters.put(parameter, request.getParameter(parameter));
            }
        });

        String code = request.getParameter(OAuth2ParameterNames.CODE);
        if (!StringUtils.hasText(code)) {
            throw new OAuth2AuthenticationException(
                    new OAuth2Error(OAuth2ErrorCodes.INVALID_REQUEST, "code 参数缺失", null));
        }

        return new WechatCodeGrantAuthenticationToken(code, clientPrincipal, additionalParameters);
    }
}
```

### 4. 调用微信接口校验 code

authserver 使用 `RestClient` 调用微信的 `jscode2session` 接口，`appid` 和 `secret` 通过配置注入，只在服务端使用：

``` java
@Service
public class WechatApiService {

    @Value("${wechat.appid}")
    private String appid;

    @Value("${wechat.secret}")
    private String secret;

    private final RestClient restClient = RestClient.create();

    public WechatSession code2Session(String jsCode) {
        WechatSession session = restClient.get()
                .uri("https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code",
                        appid, secret, jsCode)
                .retrieve()
                .body(WechatSession.class);

        if (session == null || session.getErrcode() != null && session.getErrcode() != 0) {
            // 常见错误：40029 code 无效、45011 频率限制
            String errmsg = session == null ? "empty response" : session.getErrmsg();
            throw new OAuth2AuthenticationException(
                    new OAuth2Error(OAuth2ErrorCodes.INVALID_GRANT, "微信登录失败: " + errmsg, null));
        }
        return session;
    }
}
```

微信返回的数据结构：

``` java
public class WechatSession {
    private String openid;       // 用户在当前小程序下的唯一标识
    private String session_key;  // 会话密钥，仅服务端使用，不能下发给小程序
    private String unionid;      // 同一开放平台账号下的统一标识
    private Integer errcode;
    private String errmsg;
    // getter/setter 省略
}
```

### 5. Provider：核心认证逻辑

`AuthenticationProvider` 是整个扩展授权的核心，负责：校验客户端是否允许使用该授权类型、用 code 换 openid、加载用户、生成并保存令牌：

``` java
public class WechatCodeGrantAuthenticationProvider implements AuthenticationProvider {

    private final WechatApiService wechatApiService;
    private final CustomUserDetailsService userDetailsService;
    private final OAuth2AuthorizationService authorizationService;
    private final OAuth2TokenGenerator<? extends OAuth2Token> tokenGenerator;

    public WechatCodeGrantAuthenticationProvider(WechatApiService wechatApiService,
            CustomUserDetailsService userDetailsService,
            OAuth2AuthorizationService authorizationService,
            OAuth2TokenGenerator<? extends OAuth2Token> tokenGenerator) {
        this.wechatApiService = wechatApiService;
        this.userDetailsService = userDetailsService;
        this.authorizationService = authorizationService;
        this.tokenGenerator = tokenGenerator;
    }

    @Override
    public Authentication authenticate(Authentication authentication) throws AuthenticationException {
        WechatCodeGrantAuthenticationToken wechatGrant = (WechatCodeGrantAuthenticationToken) authentication;

        OAuth2ClientAuthenticationToken clientPrincipal = getAuthenticatedClientElseThrowInvalidClient(wechatGrant);
        RegisteredClient registeredClient = clientPrincipal.getRegisteredClient();

        // client 必须注册了 wechat-code 授权类型
        if (!registeredClient.getAuthorizationGrantTypes()
                .contains(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE))) {
            throw new OAuth2AuthenticationException(OAuth2ErrorCodes.UNAUTHORIZED_CLIENT);
        }

        // 1. 调用微信接口校验 code，换取 openid
        WechatSession session = wechatApiService.code2Session(wechatGrant.getCode());

        // 2. 根据 openid 加载用户，首次登录自动注册
        UserDetails userDetails = userDetailsService.loadUserByWechatOpenid(session.getOpenid());
        Authentication principal = UsernamePasswordAuthenticationToken.authenticated(
                userDetails, null, userDetails.getAuthorities());

        // 3. 生成 access_token（默认授予 client 注册的全部 scope）
        Set<String> authorizedScopes = registeredClient.getScopes();

        OAuth2TokenContext tokenContext = DefaultOAuth2TokenContext.builder()
                .registeredClient(registeredClient)
                .principal(principal)
                .authorizationServerContext(AuthorizationServerContextHolder.getContext())
                .authorizedScopes(authorizedScopes)
                .authorizationGrantType(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE))
                .authorizationGrant(wechatGrant)
                .tokenType(OAuth2TokenType.ACCESS_TOKEN)
                .build();

        OAuth2AccessToken accessToken = this.tokenGenerator.generate(tokenContext);
        if (accessToken == null) {
            throw new OAuth2AuthenticationException(
                    new OAuth2Error(OAuth2ErrorCodes.SERVER_ERROR, "令牌生成失败", null));
        }

        // client 同时注册了 refresh_token 授权类型时，签发 refresh_token
        OAuth2RefreshToken refreshToken = null;
        if (registeredClient.getAuthorizationGrantTypes().contains(AuthorizationGrantType.REFRESH_TOKEN)) {
            OAuth2TokenContext refreshContext = DefaultOAuth2TokenContext.builder()
                    .registeredClient(registeredClient)
                    .principal(principal)
                    .authorizationServerContext(AuthorizationServerContextHolder.getContext())
                    .authorizedScopes(authorizedScopes)
                    .authorizationGrantType(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE))
                    .authorizationGrant(wechatGrant)
                    .tokenType(OAuth2TokenType.REFRESH_TOKEN)
                    .build();
            refreshToken = (OAuth2RefreshToken) this.tokenGenerator.generate(refreshContext);
        }

        // 4. 保存授权信息，供后续 refresh_token、撤销、内省使用
        OAuth2Authorization.Builder builder = OAuth2Authorization.withRegisteredClient(registeredClient)
                .principalName(principal.getName())
                .authorizationGrantType(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE))
                .authorizedScopes(authorizedScopes)
                .attribute(Principal.class.getName(), principal)
                .attribute(OAuth2Authorization.AUTHORIZED_SCOPE_ATTRIBUTE_NAME, authorizedScopes);

        if (accessToken instanceof ClaimAccessor claimAccessor) {
            builder.token(accessToken, metadata ->
                    metadata.put(OAuth2Authorization.Token.CLAIMS_METADATA_NAME, claimAccessor.getClaims()));
        }
        else {
            builder.accessToken(accessToken);
        }

        this.authorizationService.save(builder.build());

        return new OAuth2AccessTokenAuthenticationToken(
                registeredClient, clientPrincipal, accessToken, refreshToken, Map.of());
    }

    @Override
    public boolean supports(Class<?> authentication) {
        return WechatCodeGrantAuthenticationToken.class.isAssignableFrom(authentication);
    }

    private static OAuth2ClientAuthenticationToken getAuthenticatedClientElseThrowInvalidClient(
            Authentication authentication) {
        OAuth2ClientAuthenticationToken clientPrincipal = null;
        if (OAuth2ClientAuthenticationToken.class
                .isAssignableFrom(authentication.getPrincipal().getClass())) {
            clientPrincipal = (OAuth2ClientAuthenticationToken) authentication.getPrincipal();
        }
        if (clientPrincipal != null && clientPrincipal.isAuthenticated()) {
            return clientPrincipal;
        }
        throw new OAuth2AuthenticationException(OAuth2ErrorCodes.INVALID_CLIENT);
    }
}
```

用户加载的逻辑很简单，首次登录用 openid 自动注册一个用户：

``` java
@Service
public class CustomUserDetailsService implements UserDetailsService {

    public UserDetails loadUserByWechatOpenid(String openid) {
        User user = userRepository.findByOpenid(openid)
                .orElseGet(() -> userRepository.createByOpenid(openid));
        return new WechatUserDetails(user);
    }

    @Override
    public UserDetails loadUserByUsername(String username) {
        throw new UnsupportedOperationException("仅支持微信登录");
    }
}
```

### 6. 注册小程序 client

小程序注册为公开客户端（`ClientAuthenticationMethod.NONE`），不持有 secret，身份凭证就是那个一次性的微信 code。同时注册 `refresh_token` 授权类型，令牌过期后才能续期：

``` java
RegisteredClient miniappClient = RegisteredClient.withId(UUID.randomUUID().toString())
        .clientId("miniapp-client")
        .clientAuthenticationMethod(ClientAuthenticationMethod.NONE)
        .authorizationGrantType(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE))
        .authorizationGrantType(AuthorizationGrantType.REFRESH_TOKEN)
        .scope(OidcScopes.OPENID)
        .scope("message.read")
        .build();
```

### 7. 接入 token 端点

通过 `AuthorizationServerConfigurer` 的 `tokenEndpoint` 把 Converter 和 Provider 注册进去，`/oauth2/token` 端点就同时支持标准和自定义授权类型了：

``` java
@Configuration
@EnableWebSecurity
public class AuthorizationServerConfig {

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE)
    public SecurityFilterChain authorizationServerSecurityFilterChain(
            HttpSecurity http,
            WechatApiService wechatApiService,
            CustomUserDetailsService userDetailsService,
            OAuth2AuthorizationService authorizationService,
            OAuth2TokenGenerator<?> tokenGenerator) throws Exception {

        OAuth2AuthorizationServerConfigurer authorizationServerConfigurer =
                OAuth2AuthorizationServerConfigurer.authorizationServer();

        http
            .securityMatcher(authorizationServerConfigurer.getEndpointsMatcher())
            .with(authorizationServerConfigurer, authorizationServer -> authorizationServer
                .oidc(Customizer.withDefaults())
                .tokenEndpoint(tokenEndpoint -> tokenEndpoint
                    .accessTokenRequestConverter(new WechatCodeGrantAuthenticationConverter())
                    .authenticationProvider(new WechatCodeGrantAuthenticationProvider(
                            wechatApiService, userDetailsService, authorizationService, tokenGenerator))))
            .authorizeHttpRequests(authorize -> authorize.anyRequest().authenticated())
            .exceptionHandling(exceptions -> exceptions
                .defaultAuthenticationEntryPointFor(
                    new LoginUrlAuthenticationEntryPoint("/login"),
                    new MediaTypeRequestMatcher(MediaType.TEXT_HTML)));

        return http.build();
    }
}
```

### 8. JWT 中携带 openid

自定义 `OAuth2TokenCustomizer`，把 openid 写进 access_token 的 claims，资源服务器就能直接从令牌里拿到微信身份，不需要查库：

``` java
@Bean
public OAuth2TokenGenerator<?> tokenGenerator(JWKSource<SecurityContext> jwkSource) {
    JwtGenerator jwtGenerator = new JwtGenerator(new NimbusJwtEncoder(jwkSource));
    jwtGenerator.setJwtCustomizer(tokenCustomizer());
    OAuth2AccessTokenGenerator accessTokenGenerator = new OAuth2AccessTokenGenerator();
    OAuth2RefreshTokenGenerator refreshTokenGenerator = new OAuth2RefreshTokenGenerator();
    return new DelegatingOAuth2TokenGenerator(
            jwtGenerator, accessTokenGenerator, refreshTokenGenerator);
}

private OAuth2TokenCustomizer<JwtEncodingContext> tokenCustomizer() {
    return context -> {
        if (OAuth2TokenType.ACCESS_TOKEN.equals(context.getTokenType())
                && context.getPrincipal().getPrincipal() instanceof WechatUserDetails wechatUser) {
            context.getClaims().claim("openid", wechatUser.getOpenid());
        }
    };
}
```

## 四、小程序端实现

### 1. 登录并获取令牌

把 `wx.request` 封装成 Promise，登录时先调 `wx.login()` 拿 code，再向 authserver 申请令牌：

``` javascript
const AUTH_SERVER = 'https://auth.example.com'

function wxRequest(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      ...options,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(res)
      },
      fail: reject
    })
  })
}

function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: async (res) => {
        if (!res.code) {
          reject(new Error('wx.login 获取 code 失败'))
          return
        }
        const tokenResp = await wxRequest({
          url: `${AUTH_SERVER}/oauth2/token`,
          method: 'POST',
          header: { 'content-type': 'application/x-www-form-urlencoded' },
          data: {
            grant_type: 'urn:springcamp:params:oauth:grant-type:wechat-code',
            client_id: 'miniapp-client',
            code: res.code
          }
        })
        saveTokens(tokenResp)
        resolve(tokenResp)
      },
      fail: reject
    })
  })
}

function saveTokens(tokenResp) {
  wx.setStorageSync('access_token', tokenResp.access_token)
  if (tokenResp.refresh_token) {
    wx.setStorageSync('refresh_token', tokenResp.refresh_token)
  }
}
```

### 2. 请求封装与令牌自动刷新

访问受保护接口时带上 `Bearer` 令牌，收到 401 说明 access_token 过期，用 refresh_token 刷新后重试一次：

``` javascript
async function requestWithAuth(options) {
  const accessToken = wx.getStorageSync('access_token')
  try {
    return await wxRequest({
      ...options,
      header: { ...options.header, Authorization: `Bearer ${accessToken}` }
    })
  } catch (resp) {
    if (resp.statusCode === 401) {
      await refreshToken()
      return wxRequest({
        ...options,
        header: {
          ...options.header,
          Authorization: `Bearer ${wx.getStorageSync('access_token')}`
        }
      })
    }
    throw resp
  }
}

async function refreshToken() {
  const tokenResp = await wxRequest({
    url: `${AUTH_SERVER}/oauth2/token`,
    method: 'POST',
    header: { 'content-type': 'application/x-www-form-urlencoded' },
    data: {
      grant_type: 'refresh_token',
      client_id: 'miniapp-client',
      refresh_token: wx.getStorageSync('refresh_token')
    }
  })
  saveTokens(tokenResp)
}
```

注意两点：

- 并发请求同时收到 401 时会触发多次刷新，而 Spring Authorization Server 默认轮换 refresh_token（旧令牌随即失效），所以需要加一把锁保证同一时刻只有一个刷新请求，刷新失败（refresh_token 也过期了）则重新走 `login()`；
- `login()` 应该在 app 启动时（如 `App.onLaunch`）执行一次，并处理"code 只能用一次"的问题：静默登录失败时提示用户。

### 3. 调用受保护接口

``` javascript
requestWithAuth({
  url: 'https://api.example.com/messages',
  method: 'GET'
}).then(data => {
  console.log('openid:', data.openid, 'messages:', data.messages)
})
```

## 五、资源服务器防护

资源服务器是标准的 JWT 校验配置，只需要知道 authserver 的签发地址，启动时自动获取公钥（JWKS）并在本地验签：

``` properties
spring.security.oauth2.resourceserver.jwt.issuer-uri=http://localhost:9000
```

``` java
@Configuration
@EnableWebSecurity
public class ResourceServerConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(authorize -> authorize.anyRequest().authenticated())
            .oauth2ResourceServer(resourceServer -> resourceServer.jwt(Customizer.withDefaults()));
        return http.build();
    }
}
```

业务代码里通过 `@AuthenticationPrincipal` 直接拿到 `Jwt`，读取其中的 openid：

``` java
@RestController
public class MessageController {

    @GetMapping("/messages")
    public Map<String, Object> messages(@AuthenticationPrincipal Jwt jwt) {
        return Map.of(
                "openid", jwt.getClaimAsString("openid"),
                "messages", List.of("Hello WeChat Mini Program"));
    }
}
```

## 六、验证与测试

code 只能从小程序运行环境中真实获取，拿到 code 后可以直接用 curl 模拟令牌申请：

``` bash
curl -X POST http://localhost:9000/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:springcamp:params:oauth:grant-type:wechat-code" \
  -d "client_id=miniapp-client" \
  -d "code=0c3lxY000xxxxxx1"
```

正常返回标准的 OAuth2 令牌响应：

``` json
{
  "access_token": "eyJraWQiOiJ3ZWMta2V5IiwiYWxnIjoiUlMyNTYifQ...",
  "refresh_token": "RIbbJH4qSMewx8yXkCs6vhXl0kvBNnsO...",
  "scope": "openid message.read",
  "token_type": "Bearer",
  "expires_in": 299
}
```

携带令牌访问资源接口：

``` bash
curl http://localhost:8081/messages \
  -H "Authorization: Bearer eyJraWQiOiJ3ZWMta2V5IiwiYWxnIjoiUlMyNTYifQ..."
```

返回：

``` json
{
  "openid": "oX7t85Z0xxxxxxxxxxxx",
  "messages": ["Hello WeChat Mini Program"]
}
```

本地开发调试时，如果没有真实的小程序账号，可以在 `WechatApiService` 里加一个开关，用 mock 的 openid 代替 `jscode2session` 调用，验证整个授权链路时使用mock，后续如果有真实的小程序可以修改为接真实的微信环境。

## 七、安全要点

- **secret 只在服务端**：`appid`/`secret` 通过环境变量或配置中心注入 authserver，绝不能打进小程序包（小程序包可被反编译）；
- **公开客户端**：小程序 client 使用 `ClientAuthenticationMethod.NONE`，不使用 client_secret，身份凭证就是一次性的微信 code；
- **code 天然防重放**：5 分钟有效、一次性使用，重放攻击会得到 40029 错误；
- **令牌短生命周期 + 轮换**：access_token 保持短有效期（如 5 分钟），refresh_token 刷新时自动轮换，泄露后的影响窗口很小；
- **session_key 不下发**：session_key 只在服务端使用（如解密手机号），绝不能返回给小程序端；
- **全链路 HTTPS**：生产环境 authserver 和资源服务器必须启用 HTTPS，并在微信公众平台配置 request 合法域名；
- **无状态资源服务**：JWT 自包含，资源服务器不共享任何会话状态，可以随意水平扩展。

## 八、总结

微信小程序虽然不能走标准的授权码流程，但借助 Spring Authorization Server 的扩展授权类型机制，只需要实现一个 Converter 和一个 Provider，就能把 `wx.login()` 的微信登录接入标准 OAuth2 令牌体系：小程序作为公开客户端用 code 换 JWT，资源服务器按标准方式校验 Bearer 令牌，微信身份被隔离在 authserver 一侧。

这个方案的价值在于：授权服务器同时服务 Web（授权码 + PKCE）和小程序（wechat-code）等多种客户端形态，令牌签发、刷新、撤销全部作为统一逻辑实现，业务资源服务器则完全不感知客户端差异。示例项目里也包含了 Web 端授权码流程的配置，两种客户端可以共用同一个 authserver。
