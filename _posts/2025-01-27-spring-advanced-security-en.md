---
layout: post
title:  "Advanced Spring Security Usage"
date:   2025-01-27 15:30:00 +0800
lang: en
slug_zh: spring-advanced-security
tags: [spring,java]
categories: [spring boot]
image: assets/images/spring-security.png
description: "Custom Spring Security for real projects: login URLs with dynamic parameters, custom authentication checks, and custom authorization via AuthorizationManager."
---

Advanced usage of Spring Security, including a loginUrl carrying custom parameters, custom authentication logic, and custom authorization logic.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-advanced-security](https://github.com/qihaiyan/springcamp/tree/main/spring-advanced-security)

 [A complete standalone example project is available at https://github.com/qihaiyan/ng-boot-oauth, with three frontend login implementations in vue/react/angular ](https://github.com/qihaiyan/ng-boot-oauth)

 ![login](../assets/images/login.png)

## 1. Overview

In real-world project development, Spring Security's default authentication and authorization logic cannot handle high business complexity. In such cases we need to customize these, including a loginUrl that carries parameters, custom authentication logic, and custom authorization logic.

## 2. Custom loginUrl with Parameters

When redirecting to the login page, Spring Security lets you specify the login url, but it cannot carry dynamic parameters in the url — for example redirecting to login?param=foo, where foo needs to change dynamically based on specific conditions. To achieve this, we need to specify a custom LoginUrlAuthenticationEntryPoint through exceptionHandling.

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

The code above defines a custom CustomLoginUrlAuthenticationEntryPoint. In the commence method we can implement our own redirect logic as the business requires, by modifying the redirectUrl.

Reference CustomLoginUrlAuthenticationEntryPoint in the Spring Security configuration through exceptionHandling:

``` java
exceptionHandling(customizer ->
                        customizer.authenticationEntryPoint(new CustomLoginUrlAuthenticationEntryPoint("/login")))
```

## 3. Custom Authentication Logic

Spring Security's default authentication logic only checks whether the username and password are valid. To add other validation logic, implement an AuthenticationProvider, then register our own AuthenticationProvider in the authenticationManager.

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

        // custom authentication check logic
        if (username.equals("need approval")) {
            log.info("invalid request is: {}", req);
            throw new AuthenticationServiceException("Your account is pending approval for access");
        }
    }
}
```

In the custom CustomAuthenticationProvider above, the custom authentication logic is implemented by overriding the additionalAuthenticationChecks method.

Then specify CustomAuthenticationProvider in the authenticationManager:

``` java
@Bean
public AuthenticationManager authenticationManager() {
    return new ProviderManager(customAuthenticationProvider);
}
```

## 4. Custom Authorization Logic

Spring Security allows fairly flexible authorization strategies through requestMatchers in the configuration, but it lacks some dynamic capabilities — for example it cannot handle rest-style urls with variables such as /foo/{param}. In this case we can implement a custom AuthorizationManager, then specify it in requestMatchers through the access method.

```java
public class MyRequestAuthorizationManager implements AuthorizationManager<RequestAuthorizationContext> {

    private final SecurityExpressionHandler<RequestAuthorizationContext> expressionHandler = new DefaultHttpSecurityExpressionHandler();

    public MyRequestAuthorizationManager() {
    }

    // custom authorization check logic
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

In MyRequestAuthorizationManager, custom authorization is implemented by overriding the check method. For rest-style urls with variables, the variable value can be obtained through the lookupVariable method of EvaluationContext.

Specify the custom AuthorizationManager:

```java
MyRequestAuthorizationManager myRequestAuthorizationManager = new MyRequestAuthorizationManager();
http
    .authorizeHttpRequests(authorize -> authorize
        .requestMatchers("/{param}").access(myRequestAuthorizationManager)
    )
```
