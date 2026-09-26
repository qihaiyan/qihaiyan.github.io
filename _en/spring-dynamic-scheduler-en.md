---
layout: post
title:  "Dynamically Controlling Scheduled Tasks in Spring"
date:   2024-01-07 15:30:00 +0800
lang: en
slug_zh: spring-dynamic-scheduler
tags: [spring,java]
categories: [spring boot]
image: assets/images/scheduler.jpg
description: "Control scheduled tasks dynamically in Spring with CronTask and TaskScheduler: register, stop, and reschedule jobs at runtime through REST endpoints."
---

In the Spring framework, simple scheduled tasks can be implemented with the @Scheduled annotation. In real-world projects, however, we often need to control scheduled tasks dynamically — for example, adding, starting, stopping, or deleting scheduled tasks through endpoints, or changing a task's execution time on the fly.

We can control scheduled tasks programmatically. The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-scheduler](https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-scheduler)

## 1. Overview

In Spring, scheduled tasks can be controlled dynamically with CronTask and TaskScheduler, enabling dynamic updates such as changing a task's execution time — something @Scheduled cannot do. With the programmatic approach, we can also save the dynamic task information to a database and drive the scheduled tasks from the task configuration data stored there, or control them through endpoints.

## 2. Configuring Scheduled Tasks

First, just like the @Scheduled annotation approach, dynamically controlling scheduled tasks also requires the @EnableScheduling annotation to enable the scheduling feature:

Then configure the dynamic tasks by implementing the SchedulingConfigurer interface:

``` java
@Component
public class MyScheduler implements SchedulingConfigurer {
    private ScheduledTaskRegistrar taskRegistrar;
    private final ConcurrentHashMap<Long, ScheduledFuture<?>> scheduledFutures = new ConcurrentHashMap<>();

    @Override
    public void configureTasks(@NonNull ScheduledTaskRegistrar taskRegistrar) {
        ThreadPoolTaskScheduler threadPoolTaskScheduler = new ThreadPoolTaskScheduler();
        threadPoolTaskScheduler.setPoolSize(10);// Set the pool of threads
        threadPoolTaskScheduler.setThreadNamePrefix("sys-scheduler");
        threadPoolTaskScheduler.initialize();
        this.taskRegistrar = taskRegistrar;
        this.taskRegistrar.setTaskScheduler(threadPoolTaskScheduler);
    }

    @PreDestroy
    public void destroy() {
        this.taskRegistrar.destroy();
    }
}
```

With the code above, we have enabled the basic capability for dynamic tasks and assigned a thread pool for executing them.

## 3. Dynamically Updating Scheduled Tasks

Updating a scheduled task is done through CronTask and TaskScheduler. Let's add a method for registering a scheduled task:

```java
    public void registerTask(TaskData taskData) {
        // If the configuration is unchanged, there is no need to recreate the scheduled task
        if (scheduledFutures.containsKey(taskData.getId())
                && cronTasks.get(taskData.getId()).getExpression().equals(taskData.getExpression())) {
            return;
        }
        // If the task's execution time has changed, cancel the current task
        if (scheduledFutures.containsKey(taskData.getId())) {
            scheduledFutures.remove(taskData.getId()).cancel(false);
            cronTasks.remove(taskData.getId());
        }

        CronTask task = new CronTask(taskData, taskData.getExpression());
        TaskScheduler scheduler = taskRegistrar.getScheduler();
        if (scheduler != null) {
            ScheduledFuture<?> future = scheduler.schedule(task.getRunnable(), task.getTrigger());
            if (future != null) {
                scheduledFutures.put(taskData.getId(), future);
            }
        }
    }
```

We added a registerTask method for registering scheduled tasks. The TaskData parameter holds the configuration data of the scheduled task; for simplicity, we put the configuration data and the execution code together:

```java
@Slf4j
@Data
@Entity
public class TaskData implements Runnable {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
    private String expression;

    @Transient
    @Override
    public void run() {
        log.info("{} is running with expression {}", this.getName(), this.getExpression());
    }
}
```

The core code creates a CronTask object, which takes two parameters: a Runnable method and a cron expression.
Once the CronTask object is created, the scheduled task is registered through ScheduledTaskRegistrar. After registration, the scheduled task starts running at the time points specified by the cron expression.
The code being executed is the method specified by the Runnable parameter.

## 4. Dynamically Stopping Scheduled Tasks

To be able to stop scheduled tasks dynamically, we stored the registration result in a Map when registering a task:

```java
private final ConcurrentHashMap<Long, ScheduledFuture<?>> scheduledFutures = new ConcurrentHashMap<>();

ScheduledFuture<?> future = scheduler.schedule(task.getRunnable(), task.getTrigger());
            if (future != null) {
                scheduledFutures.put(taskData.getId(), future);
            }
```

Add a method for stopping a scheduled task:

```java
public void stop(Long id) {
        if (scheduledFutures.containsKey(id)) {
            scheduledFutures.remove(id).cancel(false);
        }
    }
```

This method takes the id of the scheduled task. Since we saved the task information in the scheduledFutures Map, we can look up the corresponding task by the id parameter and call its ```cancel``` method to stop the scheduled task.

## 5. Controlling Scheduled Tasks through Endpoints

With the steps above we already have the basic capability to control scheduled tasks dynamically. Now let's add endpoints to control them:

```java
@EnableScheduling
@SpringBootApplication
@RestController
public class DemoApplication {
    @Autowired
    private MyScheduler myScheduler;
    @Autowired
    private TaskDataRepository taskDataRepository;

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }

    @RequestMapping("/register")
    public TaskData register(
            String name,
            @RequestParam(name = "expression", required = false, defaultValue = "0/1 * * * * ?") String expression
    ) {
        TaskData taskData = taskDataRepository.findOneByName(name).orElse(new TaskData());
        taskData.setName(name);
        taskData.setExpression(expression);
        taskData = taskDataRepository.save(taskData);
        myScheduler.registerTask(taskData);
        return taskData;
    }

    @RequestMapping("/stop")
    public void stop(Long id) {
        taskDataRepository.findById(id).ifPresent(taskData -> {
            myScheduler.stop(id);
        });
    }
}
```

We provide two endpoints, register and stop. When these endpoints change the dynamic task data, they first save the data to the database, persisting the scheduled tasks so that they are not lost after an application restart.

After the application starts, we first call the register endpoint to add a scheduled task:

```bash
http://localhost:8080/register?name=test
```

After the call, the logs show that the scheduled task has started running. The register endpoint can also update a task's execution time through the expression parameter:

```bash
2024-01-07T18:02:09.003+08:00  INFO 23012 --- [ sys-scheduler5] c.s.springdynamicscheduler.TaskData      : test is running with expression 0/1 * * * * ?
2024-01-07T18:02:10.005+08:00  INFO 23012 --- [ sys-scheduler3] c.s.springdynamicscheduler.TaskData      : test is running with expression 0/1 * * * * ?
2024-01-07T18:02:11.012+08:00  INFO 23012 --- [ sys-scheduler3] c.s.springdynamicscheduler.TaskData      : test is running with expression 0/1 * * * * ?
```

Then call the stop endpoint, and the logs show that the scheduled task has stopped running:

```bash
http://localhost:8080/stop?id=1
```
