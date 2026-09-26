---
layout: post
title:  "How Programs Keep Running in the Background: Principles and Methods"
date:   2017-06-11 21:28:00 +0800
lang: en
slug_zh: sighup-term
tags: [linux]
categories: [linux]
image: assets/images/sighup.png
description: "How SIGHUP makes processes exit on terminal close, why orphaned background processes survive, and shell techniques like nohup and trap to keep them running."
---

In Linux, processes are organized into sessions: a session contains one foreground process group and one or more background process groups, and a process group contains multiple processes.

A session may have a session leader, and a session leader may have a controlling terminal. A process group may have a process group leader. (Note the word "may" — in some cases there is none.)

The PID of the process group leader equals the process group ID.

A process that interacts with the terminal is a foreground process; otherwise it is a background process.

SIGHUP is sent to the corresponding processes in the following three situations:

1. When the terminal is closed, the signal is sent to the session leader and to processes submitted as jobs (i.e., processes started with the & symbol)

2. When the session leader exits, the signal is sent to every process in the foreground process group of that session

3. If the exit of the parent process turns the process group into an orphaned process group, and some process in the group is in a stopped state (having received SIGSTOP or SIGTSTP), the signal is sent to every process in that group.

<!-- more -->

The system's default handling of a signal is to terminate the process that receives it.

So if the program does not catch the signal, the process exits when it receives it.

Below we observe several cases where closing the terminal causes a process to exit; here the process exits because it received the SIGHUP signal.

The login shell is the session leader.

First, write a test program with the following code:

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

The program catches the SIGHUP signal and prints a message, and pause() suspends the program.

The compiled executable is sigtest.

1. Command: sigtest front > tt.txt

Action: close the terminal

Result: the tt file contains front: sighup received

Reason:

sigtest is a foreground process. When the terminal is closed, according to case 1 above, the login shell, as the session leader, receives the SIGHUP signal and then exits,

According to case 2, sigtest, being a foreground process, receives the SIGHUP signal sent by the login shell.

2. Command:

sigtest back > tt.txt &

Action:

Close the terminal

Result:

the tt file contains back: sighup received

Reason:

sigtest was submitted as a job, so according to case 1 above it receives the SIGHUP signal.

3. Write a shell script with the following content:

sigtest back > tt.txt &

Run the script.

Action: close the terminal

Result: running `ps -ef | grep sigtest` shows the process is still there, and the tt file is empty

Reason:

When the script runs, sigtest is submitted as a job; then the script exits, which turns sigtest into an orphaned process that is no longer a job of the current session,

Therefore sigtest is neither the session leader nor a job, and does not receive SIGHUP.

Also, an orphaned process belongs to the background, so the login shell does not send SIGHUP to sigtest when it exits, because it only sends the signal to the foreground process group.

Case 3 said that if a process group becomes orphaned and has a process in a stopped state, that process also receives the SIGHUP signal; but sigtest is not in a stopped state, so it does not receive SIGHUP.

4. nohup sigtest > tt

Action:

Close the terminal

Result: the tt file is empty

Reason: nohup prevents the process from receiving the SIGHUP signal.

At this point it is clear in which cases a process exits when the terminal is closed and in which cases it does not.

To keep a process from exiting when the terminal is closed, you can use the following methods, all via the shell:

1. Write a shell script with the following content

```shell
trap "" SIGHUP  # this line blocks the SIGHUP signal; trap can block many signals
sigtest
```

2. nohup sigtest can be executed directly on the command line.

If you want to continue with other work afterwards, run

```shell
nohup sigtest &
```

3. Write a shell script with the following content

```shell
sigtest &
```

Summary:

Any method that turns the process into an orphaned process can keep the program running in the background, including forking and having the parent exit immediately — a common technique for implementing daemon programs in C.
