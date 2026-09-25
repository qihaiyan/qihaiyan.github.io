---
layout: post
title:  "Securing WeChat Mini Programs with Spring Authorization Server"
date:   2026-08-22 15:30:00 +0800
lang: en
slug_zh: spring-oauth-wechat-miniprogram
tags: [spring,java,oauth2,wechat,featured]
categories: [spring boot]
image: assets/images/spring-oauth-wechat-miniprogram.jpg
description: "Add a custom wechat-code grant type via Spring Authorization Server, exchanging wx.login codes for standard OAuth2 tokens to secure backend resources."
---

WeChat mini programs are a typical native client application: there is no browser address bar, so the redirect interactions that the OAuth2 authorization code flow relies on cannot happen; the code package can be decompiled and the client has no secure place to store secrets, so the standard authorization code flow does not apply directly. This post describes how to use the extension grant mechanism of Spring Authorization Server to define a custom `wechat-code` grant type for mini programs, exchanging the code produced by `wx.login()` for standard OAuth2 tokens and achieving unified authorization protection for backend resources.

The complete code is available in the example project [https://github.com/qihaiyan/ng-boot-oauth](https://github.com/qihaiyan/ng-boot-oauth).

WeChat login on the web: [Xiaoji](https://xj.hiease.cn)

Scan the QR code below to view the corresponding mini program demo

![gh_fdd613f3b7e0_258.jpg](../assets/images/gh_fdd613f3b7e0_258.jpg)

## 1. Overview

Securing WeChat mini programs involves several special problems:

1. **No redirects**: the authorization code flow requires the client to send the user's browser to the authorization server, but mini programs run inside WeChat's container with no standard browser environment (embedded `web-view` pages offer a poor experience and many restrictions).
2. **No confidentiality**: the mini program package is distributed with the installation and can be decompiled, so any secret hard-coded into it would leak; a mini program can therefore only act as a public client.
3. **WeChat login is not API protection**: `wx.login()` only solves the "WeChat identity" problem; access control for your own backend APIs, token lifecycle management, and unified authentication across clients still require a standard OAuth2 token system.

The approach in this post: use WeChat's official `wx.login()` for user authentication, and use Spring Authorization Server's **extension grant** mechanism to define a custom `wechat-code` grant type for token issuance. The overall flow:

- The mini program calls `wx.login()` to obtain a one-time temporary code;
- The mini program submits the code to the authorization server's `/oauth2/token` endpoint (grant_type is the custom `wechat-code`);
- The authorization server calls WeChat's `jscode2session` API with the code to obtain the `openid`, then loads (or auto-registers) the corresponding user;
- The authorization server issues a standard `access_token` (JWT) and `refresh_token`;
- Subsequent mini program requests carry the `Bearer` token to the resource server, which validates the JWT locally — completely stateless.

This decouples WeChat login from the token system: the resource server knows nothing about WeChat and remains standard OAuth2 protection.

## 2. Core Interaction Flow

```
WeChat Mini Program          Authorization Server authserver     WeChat Open Platform
    |                                  |                                |
    |--- wx.login() to get temporary code ---------------------------->|
    |<-- code ---------------------------------------------------------|
    |                                  |                                |
    |--- POST /oauth2/token --------->|                                |
    |    grant_type=wechat-code       |--- jscode2session ------------->|
    |    client_id=miniapp-client     |    (appid, secret, code)       |
    |    code=xxx                     |<-- openid / session_key --------|
    |                                  |                                |
    |                                  |  load (or register) user by     |
    |                                  |  openid, generate access_token  |
    |                                  |  and refresh_token              |
    |<-- access_token / refresh_token |                                |
    |                                  |                                |
    |--- GET /api/messages ---------->|  resource server validates JWT  |
    |    Authorization: Bearer xxx    |  locally                        |

 After access_token expires:
    |--- POST /oauth2/token --------->|  standard refresh_token grant   |
    |<-- new access_token / refresh_token ------------------------------|
```

Key points in this flow:

- WeChat's code is **one-time** and valid for about 5 minutes, which inherently prevents replay;
- `appid` and `secret` are stored only on the authserver side; the mini program holds no secrets;
- `access_token` is a self-contained JWT, so the resource server can validate it without querying the database or calling the authserver;
- When the token expires, the standard `refresh_token` grant is used for renewal; Spring Authorization Server automatically rotates the refresh_token on refresh.

## 3. authserver Side: Implementing the Extension Grant Type

Spring Authorization Server is a development library rather than an out-of-the-box service. It natively supports the standard grant types — authorization code, client credentials, and refresh token — and provides an extension mechanism: by defining a custom `AuthenticationConverter` and `AuthenticationProvider`, you can plug your own grant type into the standard `/oauth2/token` endpoint.

### 1. Defining the Grant Type

The grant_type uses the URN format recommended by RFC to avoid conflicts with standard types:

``` java
public final class WechatGrantTypes {

    /**
     * WeChat mini program login grant type
     */
    public static final String WECHAT_CODE = "urn:springcamp:params:oauth:grant-type:wechat-code";

    private WechatGrantTypes() {
    }
}
```

### 2. Custom Authentication Token

Extend `OAuth2AuthorizationGrantAuthenticationToken` and store the WeChat code as an explicit field:

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

### 3. Converter: Extracting Parameters from the Request

When the token endpoint receives a request, the `AuthenticationConverter` first converts the HTTP request into the Authentication from the previous step. Note that it must return `null` when `grant_type` does not match, so the framework keeps trying other converters and the standard authorization code and refresh token flows are not affected:

``` java
public class WechatCodeGrantAuthenticationConverter implements AuthenticationConverter {

    @Override
    public Authentication convert(HttpServletRequest request) {
        String grantType = request.getParameter(OAuth2ParameterNames.GRANT_TYPE);
        if (!WechatGrantTypes.WECHAT_CODE.equals(grantType)) {
            return null;
        }

        // clientPrincipal is the client identity authenticated by the ClientAuthenticationFilter
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

### 4. Calling the WeChat API to Validate the Code

The authserver uses `RestClient` to call WeChat's `jscode2session` API; `appid` and `secret` are injected through configuration and used only on the server side:

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
            // Common errors: 40029 invalid code, 45011 rate limit
            String errmsg = session == null ? "empty response" : session.getErrmsg();
            throw new OAuth2AuthenticationException(
                    new OAuth2Error(OAuth2ErrorCodes.INVALID_GRANT, "微信登录失败: " + errmsg, null));
        }
        return session;
    }
}
```

The data structure returned by WeChat:

``` java
public class WechatSession {
    private String openid;       // unique identifier of the user under the current mini program
    private String session_key;  // session key, used only on the server side, must never be sent to the mini program
    private String unionid;      // unified identifier under the same Open Platform account
    private Integer errcode;
    private String errmsg;
    // getters/setters omitted
}
```

### 5. Provider: Core Authentication Logic

The `AuthenticationProvider` is the core of the entire extension grant. It is responsible for: checking whether the client is allowed to use the grant type, exchanging the code for an openid, loading the user, and generating and saving the tokens:

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

        // the client must have the wechat-code grant type registered
        if (!registeredClient.getAuthorizationGrantTypes()
                .contains(new AuthorizationGrantType(WechatGrantTypes.WECHAT_CODE))) {
            throw new OAuth2AuthenticationException(OAuth2ErrorCodes.UNAUTHORIZED_CLIENT);
        }

        // 1. Call the WeChat API to validate the code and exchange it for an openid
        WechatSession session = wechatApiService.code2Session(wechatGrant.getCode());

        // 2. Load the user by openid, auto-registering on first login
        UserDetails userDetails = userDetailsService.loadUserByWechatOpenid(session.getOpenid());
        Authentication principal = UsernamePasswordAuthenticationToken.authenticated(
                userDetails, null, userDetails.getAuthorities());

        // 3. Generate the access_token (grants all scopes registered for the client by default)
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

        // issue a refresh_token when the client is also registered with the refresh_token grant type
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

        // 4. Save the authorization for later refresh_token, revocation and introspection
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

The user loading logic is simple: on first login, a user is automatically registered with the openid:

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

### 6. Registering the Mini Program Client

The mini program is registered as a public client (`ClientAuthenticationMethod.NONE`) that holds no secret — its credential is the one-time WeChat code. The `refresh_token` grant type is registered as well, so tokens can be renewed after they expire:

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

### 7. Wiring into the Token Endpoint

Register the Converter and Provider through the `tokenEndpoint` customizer of the `AuthorizationServerConfigurer`, and the `/oauth2/token` endpoint supports both standard and custom grant types:

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

### 8. Carrying openid in the JWT

Define a custom `OAuth2TokenCustomizer` to write the openid into the access_token claims, so the resource server can read the WeChat identity directly from the token without querying the database:

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

## 4. Mini Program Side Implementation

### 1. Logging In and Obtaining Tokens

Wrap `wx.request` into a Promise; when logging in, first call `wx.login()` to get a code, then request tokens from the authserver:

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

### 2. Request Wrapper and Automatic Token Refresh

Attach the `Bearer` token when calling protected APIs; a 401 means the access_token has expired — refresh it with the refresh_token and retry once:

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

Two things to note:

- When concurrent requests receive 401 at the same time, multiple refreshes are triggered. Spring Authorization Server rotates the refresh_token by default (the old token becomes invalid immediately), so a lock is needed to ensure only one refresh request runs at a time; if the refresh fails (the refresh_token has expired too), fall back to `login()`;
- `login()` should run once when the app starts (e.g. in `App.onLaunch`), and must handle the fact that "a code can only be used once": if silent login fails, prompt the user.

### 3. Calling Protected APIs

``` javascript
requestWithAuth({
  url: 'https://api.example.com/messages',
  method: 'GET'
}).then(data => {
  console.log('openid:', data.openid, 'messages:', data.messages)
})
```

## 5. Resource Server Protection

The resource server uses standard JWT validation configuration. It only needs to know the authserver's issuer address; it automatically fetches the public key (JWKS) at startup and verifies signatures locally:

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

In business code, the `Jwt` is available directly through `@AuthenticationPrincipal`, and the openid can be read from it:

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

## 6. Verification and Testing

The code can only be obtained from a real mini program runtime. Once you have a code, you can use curl directly to simulate the token request:

``` bash
curl -X POST http://localhost:9000/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=urn:springcamp:params:oauth:grant-type:wechat-code" \
  -d "client_id=miniapp-client" \
  -d "code=0c3lxY000xxxxxx1"
```

A successful call returns the standard OAuth2 token response:

``` json
{
  "access_token": "eyJraWQiOiJ3ZWMta2V5IiwiYWxnIjoiUlMyNTYifQ...",
  "refresh_token": "RIbbJH4qSMewx8yXkCs6vhXl0kvBNnsO...",
  "scope": "openid message.read",
  "token_type": "Bearer",
  "expires_in": 299
}
```

Call the resource API with the token:

``` bash
curl http://localhost:8081/messages \
  -H "Authorization: Bearer eyJraWQiOiJ3ZWMta2V5IiwiYWxnIjoiUlMyNTYifQ..."
```

Response:

``` json
{
  "openid": "oX7t85Z0xxxxxxxxxxxx",
  "messages": ["Hello WeChat Mini Program"]
}
```

For local development and debugging, if you do not have a real mini program account, you can add a switch in `WechatApiService` to return a mock openid instead of calling `jscode2session`, and use the mock when verifying the entire authorization chain. If you get a real mini program later, you can change it to connect to the real WeChat environment.

## 7. Security Considerations

- **Secrets stay on the server**: `appid`/`secret` are injected into the authserver via environment variables or a configuration center; they must never be bundled into the mini program package (the package can be decompiled);
- **Public client**: the mini program client uses `ClientAuthenticationMethod.NONE` with no client_secret; its credential is the one-time WeChat code;
- **The code is inherently replay-resistant**: valid for 5 minutes and usable only once; a replay attack gets a 40029 error;
- **Short-lived tokens plus rotation**: keep the access_token short-lived (e.g. 5 minutes) and rotate the refresh_token automatically on refresh, so the exposure window after a leak is small;
- **session_key never sent to the client**: session_key is used only on the server side (e.g. to decrypt phone numbers) and must never be returned to the mini program;
- **HTTPS end to end**: in production both the authserver and the resource server must enable HTTPS, and the valid request domains must be configured in the WeChat Official Platform console;
- **Stateless resource services**: the JWT is self-contained, resource servers share no session state, and can scale horizontally at will.

## 8. Summary

Although a WeChat mini program cannot use the standard authorization code flow, with Spring Authorization Server's extension grant mechanism you only need to implement one Converter and one Provider to bring WeChat login via `wx.login()` into a standard OAuth2 token system: the mini program, as a public client, exchanges the code for a JWT; the resource server validates the Bearer token in the standard way; and the WeChat identity is isolated on the authserver side.

The value of this approach is that the authorization server can serve multiple client types at the same time — Web (authorization code + PKCE) and mini programs (wechat-code) — with token issuance, refresh, and revocation all implemented as unified logic, while business resource servers are completely unaware of client differences. The example project also includes the Web-side authorization code flow configuration, so both client types can share the same authserver.
