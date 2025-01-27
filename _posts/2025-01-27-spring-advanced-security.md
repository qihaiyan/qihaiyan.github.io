---
layout: post
title:  "SpringSecurity高级用法"
date:   2025-01-27 15:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/spring-security.png
---

SpringSecurity的高级用法，包括自定义loginUrl携带参数，自定义认证校验逻辑，自定义权限校验逻辑。 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-advanced-security](https://github.com/qihaiyan/springcamp/tree/master/spring-advanced-security)

## 一、概述

在项目实际开发过程中，SpringSecurity默认的认证和权限校验逻辑不能实现很高的业务复杂度，这种情况下我们需要自定义这些逻辑，包括自定义loginUrl携带参数，自定义认证校验逻辑，自定义权限校验逻辑。

## 二、自定义loginUrl携带参数

SpringSecurity在跳转login页面时，虽然可以指定login的url，但是无法让url中携带动态参数，不如跳转到login?param=foo，其中foo需要根据特定条件动态变化，要实现这种效果，我们需要通过exceptionHandling指定自定义LoginUrlAuthenticationEntryPoint。

``` java
public class CustomLoginUrlAuthenticationEntryPoint extends LoginUrlAuthenticationEntryPoint {
    private final RedirectStrategy redirectStrategy = new DefaultRedirectStrategy();

    public CustomLoginUrlAuthenticationEntryPoint(String loginFormUrl) {
        super(loginFormUrl);
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response, AuthenticationException authException)
            throws IOException, ServletException {
        if (!super.isUseForward()) {
            String redirectUrl = this.buildRedirectUrlToLoginPage(request, response, authException);
            // change login url
            redirectUrl = redirectUrl + "?param=test";
            this.redirectStrategy.sendRedirect(request, response, redirectUrl);
        } else {
            String redirectUrl = null;
            if (super.isForceHttps() && "http".equals(request.getScheme())) {
                redirectUrl = this.buildHttpsRedirectUrlForRequest(request);
            }

            if (redirectUrl != null) {
                this.redirectStrategy.sendRedirect(request, response, redirectUrl);
            } else {
                String loginForm = this.determineUrlToUseForThisRequest(request, response, authException);
                RequestDispatcher dispatcher = request.getRequestDispatcher(loginForm);
                dispatcher.forward(request, response);
            }
        }
    }
}
```

以上代码自定义CustomLoginUrlAuthenticationEntryPoint，在commence方法中我们可以按照业务需要实现自己的跳转逻辑，通过修改redirectUrl实现。

在SpringSecurity配置中通过exceptionHandling引用CustomLoginUrlAuthenticationEntryPoint：

``` java
exceptionHandling(customizer ->
                        customizer.authenticationEntryPoint(new CustomLoginUrlAuthenticationEntryPoint("/login")))
```

## 三、自定义认证校验逻辑

SpringSecurity默认的认证逻辑是校验用户名密码是否合法，如果想增加其它的校验逻辑，需要实现AuthenticationProvider，然后在authenticationManager中指定我们自己实现的AuthenticationProvider。

```java
public class CustomAuthenticationProvider extends DaoAuthenticationProvider {
    @Autowired
    private CustomUserDetailsService customUserDetailsService;

    @PostConstruct
    public void init() {
        this.setUserDetailsService(customUserDetailsService);
    }

    @Override
    protected void additionalAuthenticationChecks(UserDetails userDetails, UsernamePasswordAuthenticationToken authentication) {
        super.additionalAuthenticationChecks(userDetails, authentication);
        HttpServletRequest req = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getRequest();
        String username = userDetails.getUsername();

        // 自定义认证校验逻辑
        if (username.equals("need approval")) {
            log.info("invalid request is: {}", req);
            throw new AuthenticationServiceException("Your account is pending approval for access");
        }
    }
}
```

在上面自定义的CustomAuthenticationProvider中，通过重写additionalAuthenticationChecks方法进行自定义认证逻辑的实现。

然后在authenticationManager中指定CustomAuthenticationProvider：

``` java
@Bean
public AuthenticationManager authenticationManager() {
    return new ProviderManager(customAuthenticationProvider);
}
```

## 四、自定义权限校验逻辑

SpringSecurity可以通过在配置中通过requestMatchers指定较为灵活的权限校验策略，但是缺少一些动态特性，比如对 /foo/{param} 这种rest风格的带变量的url就处理不了，
这种情况我们可以通过自定义AuthorizationManager来实现，然后在requestMatchers中通过access方法来指定我们自定义的AuthorizationManager。

```java
public class MyRequestAuthorizationManager implements AuthorizationManager<RequestAuthorizationContext> {

    private final SecurityExpressionHandler<RequestAuthorizationContext> expressionHandler = new DefaultHttpSecurityExpressionHandler();

    public MyRequestAuthorizationManager() {
    }

    // 自定义授权校验逻辑
    @Override
    public AuthorizationDecision check(Supplier<Authentication> authentication, RequestAuthorizationContext context) {
        EvaluationContext ctx = this.expressionHandler.createEvaluationContext(authentication, context);
        String checkParam = Optional.ofNullable(ctx.lookupVariable("param")).map(String::valueOf).orElse(null);

        // the '/public' url doesn't need authentication
        if (checkParam != null && (checkParam.equals("public"))) {
            return new AuthorizationDecision(true);
        }
        return new AuthorizationDecision(!ObjectUtils.isEmpty(authentication.get().getCredentials()));
    }
}
```

在MyRequestAuthorizationManager中通过重写check方法来实现自定义权限校验，rest风格的带变量的url中的变量，可以通过EvaluationContext的lookupVariable方法获取变量值。

指定自定义AuthorizationManager:

```java
MyRequestAuthorizationManager myRequestAuthorizationManager = new MyRequestAuthorizationManager();
http
    .authorizeHttpRequests(authorize -> authorize
        .requestMatchers("/{param}").access(myRequestAuthorizationManager)
    )
```
