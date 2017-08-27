---
layout: post
title:  "OAuth 2.0 教程"
date:   2017-06-11 20:22:00 +0800
tags: [oauth2]
categories: [oauth2]
---

（原文：/oauth2/index.html）

[demo: https://github.com/qihaiyan/ng-boot-oauth](https://github.com/qihaiyan/ng-boot-oauth)

## OAuth 2.0 教程

OAuth 2.0 是一个开放的标准协议，允许应用程序访问其它应用的用户授权的数据。例如：一个游戏可以获取Facebook中的用户信息，或者是一个地理位置程序可以获取Foursquare的用户信息等。
这儿是一个示例图：

![oauth2 introduce](/images/oauth2-intro.png)

首先用户进入游戏的web应用，该应用要求用户通过Facebook账户登录，并定向到Facebook的登录界面，用户登录Facebook后，会重定向到之前的游戏应用。此时该应用就获取到了用户在Facebook的用户数据以及授权信息。

### OAuth 2.0 用例

<!-- more -->

OAuth 2.0既可以用于在某个应用内访问其它应用的用户信息，又可以提供用户授权服务供其它应用调用。
OAuth 2.0是OAuth 1.0的替代，因为OAuth 1.0太复杂了，比如OAuth 1.0要求使用证书等。OAuth 2.0更加简单，不要求使用证书，仅使用SSL/TLS。

### OAuth 2.0 规范

这个教程的目的是提供一个OAuth 2.0协议的概览以帮助理解，而不是涵盖此协议的所有细节。
如果你计划实现一个OAuth 2.0协议，最好是去阅读规范的详细内容，规范的地址：[http://tools.ietf.org/html/draft-ietf-oauth-v2-23](http://tools.ietf.org/html/draft-ietf-oauth-v2-23)

## OAuth 2.0 概述

在之前的介绍中我们提到，OAuth 2.0是一个开放标准，其允许应用程序访问其它应用的用户授权的数据。现在我们来介绍这个协议是如何工作的，以及规范中提到的各种概念。
OAuth 2.0	提供了不同的方式去获取权限用语访问资源服务器中的资源。现在介绍其中最安全和最常用的使用方式：一个web应用如何请求访问另一个web应用的访问权限。
下面的示例图描述了整个处理过程：
![Alt text](/images/oauth2/overview-1.png)
首先用户访问客户端应用，在这个应用中会有一个“通过Facebook登录”的按钮。
第二步，当用户点击这个按钮时，用户被重定向到认证服务器（Facebook）。然后用户开始登录，登录成功后会被询问客户端应用是否可以使用他的用户信息。用户点击确认按钮。
第三步，认证服务器将用户重定向到客户端应用提供的URL。这个重定向URL一般会在认证服务器中进行注册，注册是由客户端应用的所有者进行的。注册完成后，认证服务器会生成一个client id和client password。重定向后的URL会有一个code参数，该参数是此次认证的一个标识。
第四步，重定向完成后，用户会进入重定向后的页面，同时客户端应用会在后台与认证服务器进行通讯，发送client id,client password和上一步获取到的code参数到认证服务器，认证服务器返回access token给客户端应用。
一旦客户端应用拿到了access token，就可以用这个token去访问Facebook提供的相关资源。

## OAuth 2.0 应用角色

OAuth 2.0定义了以下应用角色：

    Resource Owner （资源所有者）
    Resource Server （资源服务器）
    Client Application （客户端应用）
    Authorization Server （认证服务器）
![Alt text](/images/oauth2/overview-roles.png)
Resrouce Owner（资源所有者）是数据的所有者。例如：Facebook或Google上的一个用户就是一个Resrouce Owner。他们所拥有的资源就是用户数据。示例图中的那个用户的图标代表的就是Resrouce Owner。Resrouce Owner也可以是一个应用程序。

Resource Server（资源服务器）是存放资源的服务，例如Facebook或Google就是Resource Server。

Client Application（客户端应用）会请求访问存放在资源服务器上的资源，这些资源是属于Resource Owner（资源所有者）的。

Authorization Server（认证服务器）对Client Application（客户端应用）进行授权，授权通过后客户端应用才可以访问资源服务器上的资源。认证服务器和资源服务器可以是同一个应用，也可以分开独立部署。
## OAuth 2.0 客户端类型
OAuth 2.0规范定义了2种客户端类型：

* 私密型
* 公开型

私密型客户端会保存client password。认证服务器会给每一个客户端应用生成一个client password，认证服务器通过该client password来识别该客户端应用是一个注册过的应用，而不是其它的欺诈程序。一个web应用可以是私密性客户端，只有系统管理员可以登录这个应用的服务器和查看client password。

公开型客户端不会保存client password。例如移动APP或桌面程序，如果client password被保存在此类应用中，就可以通过破解手段拿到client password，这是非常不安全的。

### 客户端应用表现形式

*    Web Application （web应用）
*    User Agent （富web客户端）
*    Native （原生应用）

#### Web Application（web应用）

web程序运行在web服务器上。web应用做认证时用到的client password是保存在服务器上的，因此是私密的。下面是一个web应用的示例图：

![Alt text](/images/oauth2/overview-client-types-1.png)
#### User Agent Application（富web客户端）
富web客户端应用是指由javascript构建的web应用，浏览器是客户端代理。这类应用的特点是，程序是存放在web服务器上的，但是运行时，浏览器下载javascript程序到本地，直接在浏览器中执行，例如那些用javascript开发的网页版游戏。下面是一个富web客户端的示例图：

![Alt text](/images/oauth2/overview-client-types-2.png)
#### Native（原生应用）
（注：这里指没有后端服务器的应用，一次所有的数据和配置只能存放在客户端程序中）
原生应用包括移动APP和桌面程序。原生应用直接安装在用户的设备上（电脑或手机、平板），client password会保存在用户的设备里。下面是一个原生应用的示例图：
![Alt text](/images/oauth2/overview-client-types-3.png)
#### Hybrid（混合应用）
这类应用通常是将原生应用和web应用的开发技术混合在一起，也会有对应的后端服务器。OAuth 2.0规范中并没有提及此类应用，此类应用可以灵活选用上述三种认证类型中的任何一种。
##OAuth 2.0 认证

*    Client ID, Client Secret and Redirect URI
*    Authorization Grant
*    Authorization Code
*    Implicit
*    Resource Owner Password Credentials
*    Client Credentials

当一个客户端应用要访问资源服务器上的资源时，需要先获取到认证授权。

### Client ID, Client Secret and Redirect URI
客户端应用需要在认证服务器上注册，注册完成后，认证服务器会生成这个应用的client id和client password。client_id和client_password在同一个认证服务器中是唯一的，不会重复。客户端应用可以在多个认证服务器中进行注册（如分别在Facebook和Google中注册），不同的认证服务器会为客户端应用生成不同的client_id和client_password。
当客户端应用需要访问资源服务器上的资源时，首选要通过认证服务器进行认证，认证时要发送对应的client_id和client_password到认证服务器。
客户端应用在认证服务器进行注册时，需要填写一个重定向URL。当资源所有者对客户端应用进行授权成功后，资源所有者（可简单理解为系统用户）会被重定向到重定向URL所指定的页面。
#### 认证授权
资源所有者会给客户端应用认证授权，认证授权时需要认证服务器和资源服务器进行配合。

OAuth 2.0规范列举了4中认证授权方式，每种方式都有不同的安全特点：

*    Authorization Code（授权码模式）
*    Implicit（简化模式）
*    Resource Owner Password Credentials（用户密码模式）
*    Client Credentials

下面来对每一种授权方式进行解释。
#### Authorization Code（授权码模式）
Authorization Code（授权码）的认证过程如下：

1. 资源所有者（用户）进入客户端应用。
2. 客户端应用让用户通过认证服务器进行登录。
3. 登录之前，客户端应用会把用户重定向到认证服务器的登录页面，同时把client id发送到认证服务器，这样认证服务器就知道是哪一个客户端应用在请求认证授权。
4. 用户在认证服务器上进行登录，登录成功后，会提示用户是否要对客户端应用进行授权，用户选择同意后，会被重定向回客户端应用。
5. 当重定向回客户端应用时，使用的是客户端应用在认证服务器上注册时填写的重定向URL，同时认证服务器会发送一个代表此次认证过程的一个授权码。
6. 当成功重定向到客户端应用后，客户端应用会在后台与认证服务器进行交互，将上个步骤中获取到的授权码，连同client id,client password发送给认证服务器。
7. 认证服务器对收到的数据进行校验，通过后发送access token给客户端应用。
8. 这时客户端应用就可以用接收到的access token去资源服务器访问相关资源。下面是一个示例图：

![Alt text](/images/oauth2/authorization-auth-code.png)
#### Implicit（简化模式）
Implicit（简化模式）与Authorization Code（授权码模式）类似，区别仅在于当用户成功登录之后，重定向到客户端应用时，access token会直接返回给客户端应用。
这意味着access token在客户端应用中是可见的。而Authorization Code（授权码模式），access token是在web服务器中的，对客户端来说不可见。这是这两种模式的最大区别。
并且，客户端应用只发送client id到认证服务器。如果连同client password一起发送的话，client password需要存储在客户端应用中，这会是一个安全隐患，很容易通过破解手段拿到存放在客户端应用程序中的client password。下面是一个示例图：

![Alt text](/images/oauth2/authorization-implicit.png)
#### Resource Owner Password Credentials（用户密码模式）
Resource Owner Password Credentials（密码模式）允许客户端应用直接使用用户的用户名和密码。例如用户可以直接在客户端应用中录入Twitter的用户名和密码。
只有在充分信任客户端应用的情况下，才能使用密码模式。（因为用户名和密码是在客户端应用中录入的，因此客户端应用可以获取并保存用户的用户名和密码）。
密码模式一般在富web客户端应用和原生应用中使用。
#### Client Credentials
Client Credentials默认用户访问跟用户无关的资源，因此不需要用户授权。
## OAuth 2.0 节点
OAuth 2.0定义了节点集合。一个节点一般是web服务器上的一个URL。具体包括：

*    认证节点
*    Token节点
*    重定向节点

认证节点和Token节点在认证服务器上，重定向节点在客户端应用上。示例图如下：

![Alt text](/images/oauth2/endpoints.png)

OAuth 2.0规范并没有对节点的URL做出明确的定义，不同的实现会提供不同的URL。
### 认证节点
认证节点是用户进行登录操作的地址。
### Token节点
Token节点是认证服务器提供的，让客户端应用获取access token的地址。
### 重定向节点
重定向节点在客户端应用中，用户成功登录后，会被重定向到此地址。
## OAuth 2.0 请求和响应
当客户端应用请求access token时，会发送http请求到认证服务器。不同的认证授权类型会有不同的请求和响应内容。认证授权类型有4种：

*    Authorization Code（授权码模式）
*    Implicit（简化模式）
*    Resource Owner Password Credentials（用户密码模式）
*    Client Credentials

每种类型的请求和响应内容会在后续的内容中详细解释。
## OAuth 2.0 Authorization Code（授权码模式）的请求和响应

授权码模式有2个请求和2个响应：

* 认证请求＋响应
* access token请求＋响应。

### 授权请求
授权请求发送到认证服务器，然后会获取到一个授权码。

```
response_type 	必选项，固定值为 "code"
client_id 	必选项, 客户端应用在认证服务器注册时生成的client id.
redirect_uri 	可选项. T客户端应用在认证服务器注册时填写的重定向URL地址.
scope 	可选项. 请求的权限范围.
state 	可选项 (建议提供). 客户端应用的请求URL中的参数，可以是任意值.
```
### 授权响应
授权响应含有授权码，这个授权码在后续获取access token时需要提供。

```
code 	必选项. 认证服务器返回的授权码.
state 	必选项, 如果客户端应用的请求中有这个参数，既为这个参数的值.
```
### 授权错误响应
授权错误的情形有2种。

第一种是客户端应用验证失败，例如授权请求中发送的重定向URL与客户端应用在认证服务器中注册时填写的URL不一致。

第二种是产生了其它错误，此时下面的错误信息会返回给客户端应用：

```
error 	Required. Must be one of a set of predefined error codes. See the specification for the codes and their meaning.
error_description 	Optional. A human-readable UTF-8 encoded text describing the error. Intended for a developer, not an end user.
error_uri 	Optional. A URI pointing to a human-readable web page with information about the error.
state 	Required, if present in authorization request. The same value as sent in the state parameter in the request.
```
### Token请求
客户端应用获取到授权码后，可以用此授权码去获取access token。请求参数如下：

```
client_id 	Required. The client application's id.
client_secret 	Required. The client application's client secret .
grant_type 	Required. Must be set to authorization_code .
code 	Required. The authorization code received by the authorization server.
redirect_uri 	Required, if the request URI was included in the authorization request. Must be identical then.
```
### Token 响应
access token的响应内容是json格式的：

```
{ "access_token"  : "...",
  "token_type"    : "...",
  "expires_in"    : "...",
  "refresh_token" : "...",
}
```
access_token  : 访问令牌,
token_type    : 令牌类型，一般是bearer,
expires_in    : 以秒为单位的令牌失效时间,
refresh_token : 当访问令牌失效时，可以用更新令牌获取一个新的访问令牌
## OAuth 2.0 简化模式的请求和响应
简化模式只有一个请求和一个响应。
### 简化模式授权请求
该请求的参数如下：

```
response_type 	Required. Must be set to token .
client_id 	Required. The client identifier as assigned by the authorization server, when the client was registered.
redirect_uri 	Optional. The redirect URI registered by the client.
scope 	Optional. The possible scope of the request.
state 	Optional (recommended). Any client state that needs to be passed on to the client request URI.
```
### 简化模式授权响应
响应包含以下参数，注意该响应的格式不是json的。

```
access_token 	Required. The access token assigned by the authorization server.
token_type 	Required. The type of the token
expires_in 	Recommended. A number of seconds after which the access token expires.
scope 	Optional. The scope of the access token.
state 	Required, if present in the autorization request. Must be same value as state parameter in request.
```
### 简化模式错误响应
有2种情况会导致错误：
第一种是客户端应用验证失败，例如授权请求中发送的重定向URL与客户端应用在认证服务器中注册时填写的URL不一致。

第二种是产生了其它错误，此时下面的错误信息会返回给客户端应用：

```
error 	Required. Must be one of a set of predefined error codes. See the specification for the codes and their meaning.
error_description 	Optional. A human-readable UTF-8 encoded text describing the error. Intended for a developer, not an end user.
error_uri 	Optional. A URI pointing to a human-readable web page with information about the error.
state 	Required, if present in authorization request. The same value as sent in the state parameter in the request.
```
## 用户密码模式的请求和响应
用户密码模式只有一个请求和响应。
### 用户密码模式的请求
请求包含以下参数：

```
grant_type 	必选项. 固定值 "password"
username 	必选项. UTF-8编码的用户名.
password 	必选项. UTF-8编码的密码.
scope 	可选项. 请求的权限范围.
```
### 用户密码模式的响应
响应的内容是json格式：

```
{ "access_token"  : "...",
  "token_type"    : "...",
  "expires_in"    : "...",
  "refresh_token" : "...",
}
```
access_token  : 访问令牌,
token_type    : 令牌类型,
expires_in    : 以秒为单位的令牌失效时间,
refresh_token : 当访问令牌失效时，可以用更新令牌获取一个新的访问令牌
## 客户端模式的请求和响应
### 客户端模式的请求
请求包含以下参数：

```
grant_type 	必选项. 固定值 "client_credentials". 
scope 	可选项. 请求的权限范围.
```
### 客户端模式的响应
响应包含以下参数：

```
{ "access_token"  : "...",
  "token_type"    : "...",
  "expires_in"    : "...",
}
```
access_token  : 访问令牌,
token_type    : 令牌类型,
expires_in    : 以秒为单位的令牌失效时间,
注意，此种授权类型没有refresh_token
