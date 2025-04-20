---
layout: post
title:  "程序常驻后台运行的原理和方法"
date:   2017-06-11 21:28:00 +0800
tags: [linux,featured]
categories: [linux]
image: assets/images/sighup.png
---

linux中进程组织结构为session包含一个前台进程组及一个或多个后台进程组，一个进程组包含多个进程。

一个session可能会有一个session首进程，而一个session首进程可能会有一个控制终端。一个进程组可能会有一个进程组首进程。(
这儿是可能会有，在一定情况之下是没有的) 

进程组首进程的PID与该进程组ID相等。

与终端交互的进程是前台进程，否则便是后台进程。

SIGHUP会在以下3种情况下被发送给相应的进程：

1、终端关闭时，该信号被发送到首进程以及作为job提交的进程（即用 & 符号提交的进程）

2、session首进程退出时，该信号被发送到该session中的前台进程组中的每一个进程

3、若父进程退出导致进程组成为孤儿进程组，且该进程组中有进程处于停止状态（收到SIGSTOP或SIGTSTP信号），该信号会被发送到该进程组中的每一个进程。

<!-- more -->

系统对信号的默认处理是终止收到该信号的进程。

所以若程序中没有捕捉该信号，当收到该信号时，进程就会退出。

下面观察几种因终端关闭导致进程退出的情况，在这儿进程退出是因为收到了SIGHUP信号。

login shell是session首进程。

首先写一个测试程序，代码如下：

```c
#include <stdio.h>
#include <signal.h>

char **args;

void exithandle(int sig)
{
       printf("%s : sighupreceived\n",args[1]);
}

int main(int argc,char **argv)
{
       args=argv;
       signal(SIGHUP,exithandle);
       pause();
       return 0;
}
```

程序中捕捉SIGHUP信号后打印一条信息，pause()使程序暂停。

编译后的执行文件为sigtest

1、命令： sigtest front > tt.txt

操作： 关闭终端

结果： tt文件的内容为front: sighup received

原因：

sigtest是前台进程，终端关闭后，根据上面提到的第1种情况， loginshell作为session首进程，会收到SIGHUP信号然后退出，

根据第2种情况，sigtest作为前台进程，会收到login shell发出的SIGHUP信号。

2、命令：

sigtest back > tt.txt &

操作：

关闭终端

结果：

tt文件的内容为back: sighup received

原因：

sigtest是提交的job，根据上面提到的第1种情况，sigtest会收到SIGHUP信号

3、写一个shell，内容为

sigtest back > tt.txt &

执行该shell

操作： 关闭终端

结果： 执行`ps -ef | grep sigtest`命令，会看到该进程还在，tt文件为空

原因：

执行该shell时，sigtest作为job提交，然后该shell退出，致使sigtest变成了孤儿进程，不再是当前session的job，

因此sigtest即不是session首进程也不是job，不会收到SIGHUP。

同时孤儿进程属于后台进程，因此loginshell退出后不会发送SIGHUP给sigtest，因为它只将该信号发送给前台进程。

第3条说过若进程组变成孤儿进程组的时候，若有进程处于停止状态，也会收到SIGHUP信号，但sigtest没有处于停止状态，所以不会收到SIGHUP信号。

4、nohup sigtest > tt

操作：

关闭终端

结果： tt文件为空

原因：nohup可以防止进程收到SIGHUP信号

至此，我们就清楚了何种情况下终端关闭后进程会退出，何种情况下不会退出。

要想终端关闭后进程不退出有以下几种方法，均为通过shell的方式：

1、 编写shell，内容如下

```shell
trap "" SIGHUP  #该句的作用是屏蔽SIGHUP信号，trap可以屏蔽很多信号
sigtest
```

2、nohup sigtest可以直接在命令行执行，

若想做完该操作后继续别的操作，可以执行

```shell
nohup sigtest &
```

3、 编写shell，内容如下

```shell
sigtest &
```

总结：

可以采用任何将进程变为孤儿进程的方式，让程序常驻后台运行，包括fork后父进程马上退出，这是C语言中实现daemon程序的常用技巧。
