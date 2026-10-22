---
layout: post
title:  "Securing Spring Boot APIs with JWT Authorization"
date:   2017-06-11 21:28:00 +0800
lang: en
slug_zh: secure-spring-boot-APIs-with-JWT
tags: [spring,jwt]
categories: [spring boot]
image: assets/images/jwt.png
description: "How to secure Spring Boot 3.x/4.x RESTful APIs with JWT: integrating Spring Security 6/7 and JJWT 0.12+, plus custom filters for token validation, with a full example project."
---
### Overview

[Example](https://github.com/qihaiyan/jwt-boot-auth) https://github.com/qihaiyan/jwt-boot-auth (the example code has been updated to match the current versions used in this article)

This article was first written in 2017 and has been fully updated for Spring Boot 3.x/4.x + Spring Security 6/7: the security configuration now uses a SecurityFilterChain bean with lambda DSL, the JWT library has been upgraded to JJWT 0.12+, and the servlet APIs have moved to jakarta.

Spring Boot makes it very convenient to develop RESTful APIs. In production, it is essential to protect the published APIs with authorization. In this article we will look at how to use JWT to add authorization to an API, ensuring that only authorized users can access it.

### Building a Simple API

Spring provides a [web page](https://start.spring.io/) for conveniently generating a Spring Boot project.

As shown in the image below, select H2, Web, Security, and JPA under "Search for dependencies"; these dependencies are used in our example project.

<!-- more -->


![spring-boot-starter-jwt](/images/spring-boot-starter-jwt.png)

Click the Generate Project button and download the file to your local machine.

Add a method to JwtauthApplication.java:

``` java
@RequestMapping("/hello")
@ResponseBody
public String hello(){
  return "hello";
}
```

With that, a simple RESTful API is ready.

Now let's run the application to see the result. Open a command line tool and run:

``` shell
cd jwtauth
gradle bootRun
```

Once the application has started, you can simply call the API with curl:

``` shell
curl http://localhost:8080/hello
```

At this point our API is complete. However, it has no authorization protection at all — anyone can access it, which is insecure. Next we will add an authorization mechanism.

### Adding User Registration

First, add an entity class MyUser:

``` java
package com.example.jwtauth;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class MyUser {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private long id;
    private String username;
    private String password;

    public long getId() {
        return id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPassword() {
        return password;
    }

    public void setPassword(String password) {
        this.password = password;
    }
}
```

Then add a repository interface MyUserRepository for reading and saving user information:

``` java
package com.example.jwtauth;

import org.springframework.data.jpa.repository.JpaRepository;

public interface MyUserRepository extends JpaRepository<MyUser, Long> {
    MyUser findByUsername(String username);
}
```

Thanks to Spring Data JPA, simply defining an interface gives us full CRUD capability for our data. Since we included H2 in build.gradle, we also have a local database — no configuration is needed and Spring Boot uses it automatically. Spring Boot really does take a huge amount of work off the developer's hands.

Next, add a UserController class that implements the user registration endpoint:

``` java
package com.example.jwtauth;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/users")
public class UserController {

    private MyUserRepository applicationUserRepository;
    private BCryptPasswordEncoder bCryptPasswordEncoder;

    public UserController(MyUserRepository myUserRepository,
                          BCryptPasswordEncoder bCryptPasswordEncoder) {
        this.applicationUserRepository = myUserRepository;
        this.bCryptPasswordEncoder = bCryptPasswordEncoder;
    }

    @PostMapping("/signup")
    public void signUp(@RequestBody MyUser user) {
        user.setPassword(bCryptPasswordEncoder.encode(user.getPassword()));
        applicationUserRepository.save(user);
    }
}
```

The

``` java
@PostMapping("/signup")
```

annotation defines the user registration endpoint and specifies the URL as /users/signup. Since the class is annotated with @RequestMapping("/users"), the URLs of all methods in the class get the /users prefix, so the method only needs to specify the /signup sub-path.

Passwords are encrypted with BCryptPasswordEncoder, so we add the BCryptPasswordEncoder bean definition in the Application class.

``` java
@SpringBootApplication
@RestController
public class JwtauthApplication {
	@Bean
	public BCryptPasswordEncoder bCryptPasswordEncoder() {
		return new BCryptPasswordEncoder();
	}
  // ...
```

### Adding JWT Authentication

After a user enters a username and password, they are compared against the user information stored in the database; if they match, authentication succeeds. The traditional approach is to create a session after successful authentication and return a cookie to the client. Here we use JWT to handle username and password authentication instead. The difference is that after successful authentication, the server generates a token and returns it to the client, and every subsequent request from the client must carry that token in the HTTP header. When the server receives a request, it verifies the token's validity. Verification includes:

1. Checking that the content is a valid JWT

2. Verifying the signature

3. Verifying the claims

4. Checking the permissions

Now let's start the implementation. We use the JJWT library to generate and validate tokens; add the following dependencies to build.gradle (Gradle now uses implementation to declare dependencies — the old compile configuration has been deprecated):

``` groovy
dependencies {
    implementation 'io.jsonwebtoken:jjwt-api:0.12.6'
    implementation 'io.jsonwebtoken:jjwt-impl:0.12.6'
    implementation 'io.jsonwebtoken:jjwt-jackson:0.12.6'
}
```

The HS512 algorithm requires a key of at least 64 bytes; if the key is too short, a WeakKeyException is thrown when issuing a token. We configure a sufficiently long secret (Base64-encoded, 65 bytes after decoding) in application.yml:

``` yaml
jwt:
  secret: Y2hhbmdlLXRoaXMtc2VjcmV0LWluLXByb2R1Y3Rpb24taXQtbXVzdC1iZS1sb25nLWVub3VnaC1mb3ItaHM1MTI=
```

#### Handling Login

Create a class JWTLoginFilter. Its core job is to generate a token after the username and password are verified, and return the token to the client:

``` java
package com.example.jwtauth;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.crypto.SecretKey;
import java.io.IOException;
import java.util.Date;

public class JWTLoginFilter extends OncePerRequestFilter {

    private static final long EXPIRATION = 24 * 60 * 60 * 1000;

    private final AuthenticationManager authenticationManager;
    private final SecretKey secretKey;

    public JWTLoginFilter(AuthenticationManager authenticationManager, String secret) {
        this.authenticationManager = authenticationManager;
        this.secretKey = Keys.hmacShaKeyFor(Decoders.BASE64.decode(secret));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        if (!"POST".equals(request.getMethod()) || !"/login".equals(request.getServletPath())) {
            filterChain.doFilter(request, response);
            return;
        }

        try {
            MyUser user = new ObjectMapper()
                    .readValue(request.getInputStream(), MyUser.class);

            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            user.getUsername(),
                            user.getPassword()));

            String token = Jwts.builder()
                    .subject(authentication.getName())
                    .expiration(new Date(System.currentTimeMillis() + EXPIRATION))
                    .signWith(secretKey)
                    .compact();
            response.addHeader("Authorization", "Bearer " + token);
        } catch (AuthenticationException e) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        }
    }
}
```

This class extends OncePerRequestFilter, which guarantees that each request passes through the filter exactly once. In the doFilterInternal method, we first check whether the request is a POST to /login; if not, it is not a login request and is simply handed over to the following filters.

For a login request, the username and password are parsed from the request body and passed to `authenticationManager.authenticate`. The AuthenticationManager calls the UserDetailsService to load the user from the database and verifies the password with BCryptPasswordEncoder. Once authentication succeeds, we generate the token in this method: the subject is the username and the token is valid for 24 hours. `signWith(secretKey)` automatically selects the signature algorithm based on the key length; our key satisfies the HS512 requirement, so HS512 is used. The generated token is returned to the client in the `Authorization: Bearer` header; if authentication fails, a 401 is returned.

#### Token Verification

Once the user logs in successfully, they receive a token, and every subsequent request carries it; the server verifies the token's validity.

Create a JwtAuthenticationFilter class in which we implement the token validation logic.

``` java
package com.example.jwtauth;

import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.crypto.SecretKey;
import java.io.IOException;
import java.util.List;

public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final SecretKey secretKey;

    public JwtAuthenticationFilter(String secret) {
        this.secretKey = Keys.hmacShaKeyFor(Decoders.BASE64.decode(secret));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");

        if (header == null || !header.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        UsernamePasswordAuthenticationToken authentication =
                getAuthentication(header.replace("Bearer ", ""));

        if (authentication != null) {
            SecurityContextHolder.getContext().setAuthentication(authentication);
        }
        filterChain.doFilter(request, response);
    }

    private UsernamePasswordAuthenticationToken getAuthentication(String token) {
        try {
            // parse the token.
            String user = Jwts.parser()
                    .verifyWith(secretKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload()
                    .getSubject();

            if (user != null) {
                return new UsernamePasswordAuthenticationToken(user, null, List.of());
            }
        } catch (JwtException | IllegalArgumentException e) {
            // invalid or expired token; ignore it, the request will be rejected by the authorization check
        }
        return null;
    }
}
```

This class also extends OncePerRequestFilter. In the doFilterInternal method, it reads the token from the `Authorization` entry of the HTTP header and then validates the token's validity with the methods provided by the Jwts library: `parseSignedClaims` checks the signature and expiration and parses out the claims. If validation passes, the authentication information is stored in the SecurityContextHolder, and the following authorization checks treat the request as an authorized, legitimate request. If the token is invalid or expired, `parseSignedClaims` throws a JwtException; we simply ignore it here, and the request is rejected by the following authorization checks.

#### Spring Security Configuration

The Spring Security configuration wires the pieces above together.

In Spring Security 6.0, the once-ubiquitous WebSecurityConfigurerAdapter has been removed, and the antMatchers and and() chained style has been deprecated along with it. The current approach is to define a SecurityFilterChain bean and configure everything with the lambda DSL (the replacement for antMatchers is requestMatchers).

``` java
package com.example.jwtauth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import static org.springframework.security.config.Customizer.withDefaults;

@Configuration
@EnableWebSecurity
public class MyWebSecurityConfig {

    @Bean
    public UserDetailsService userDetailsService(MyUserRepository myUserRepository) {
        return username -> {
            MyUser myUser = myUserRepository.findByUsername(username);
            if (myUser == null) {
                throw new UsernameNotFoundException("User not found: " + username);
            }
            return User.withUsername(myUser.getUsername())
                    .password(myUser.getPassword())
                    .roles("USER")
                    .build();
        };
    }

    @Bean
    public AuthenticationManager authenticationManager(
            AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                   AuthenticationManager authenticationManager,
                                                   @Value("${jwt.secret}") String secret) throws Exception {
        http
                .cors(withDefaults())
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session ->
                        session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(HttpMethod.POST, "/users/signup").permitAll()
                        .anyRequest().authenticated())
                .addFilterBefore(new JWTLoginFilter(authenticationManager, secret),
                        UsernamePasswordAuthenticationFilter.class)
                .addFilterBefore(new JwtAuthenticationFilter(secret),
                        UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
```

The configuration class defines three beans:

1. UserDetailsService: loads users from the database. With this bean in place, together with the BCryptPasswordEncoder bean defined earlier, Spring Security automatically builds a DaoAuthenticationProvider from them to handle username and password authentication — this replaces the old configure(AuthenticationManagerBuilder) override.

2. AuthenticationManager: obtained from the AuthenticationConfiguration and exposed as a bean, for the login filter to use.

3. SecurityFilterChain: puts the configuration above together. Note these two lines

``` 
.addFilterBefore(new JWTLoginFilter(authenticationManager, secret), UsernamePasswordAuthenticationFilter.class)
.addFilterBefore(new JwtAuthenticationFilter(secret), UsernamePasswordAuthenticationFilter.class)
```

which add the JWT filters we defined to the Spring Security processing flow. Since JWT is stateless, the session creation policy is also set to STATELESS here.

Now let's do a simple verification of our application:

``` shell
# Request the hello endpoint; a 403 error is returned
curl http://localhost:8080/hello

# Register a new user
curl -H "Content-Type: application/json" -X POST -d '{
    "username": "admin",
    "password": "password"
}' http://localhost:8080/users/signup

# Log in; a token is returned. In the HTTP header, the part after "Authorization: Bearer" is the token
curl -i -H "Content-Type: application/json" -X POST -d '{
    "username": "admin",
    "password": "password"
}' http://localhost:8080/login

# Request the hello endpoint again with the token obtained from the successful login
# Replace XXXXXX in the request with the token you obtained
# This time the call succeeds
curl -H "Content-Type: application/json" \
-H "Authorization: Bearer XXXXXX" \
"http://localhost:8080/hello"

```

### Summary

That's it — JWT authentication for a Spring Boot API is now in place. The process is not complicated: it mainly comes down to writing two Spring Security filters, one to generate and one to validate the JWT token.

As a stateless authentication and authorization technology, JWT is a great fit for distributed system architectures: the server does not need to store user state, so there is no need to use technologies such as Redis to share session data between service nodes.
