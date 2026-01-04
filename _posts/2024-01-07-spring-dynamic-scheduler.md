---
layout: post
title:  "spring动态控制定时任务"
date:   2024-01-07 15:30:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/scheduler.jpg
---

在spring框架中，对于简单的定时任务，可以使用 @Scheduled 注解实现，在实际项目中，经常需要动态的控制定时任务，比如通过接口增加、启动、停止、删除定时任务，动态的改变定时任务的执行时间等。

我们可以通过编码的方式动态控制定时任务，具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-scheduler](https://github.com/qihaiyan/springcamp/tree/main/spring-dynamic-scheduler)

## 一、概述

在spring框架可以通过 CronTask 和 TaskScheduler 动态控制定时任务，实现定时任务的动态更新，比如修改定时任务的执行时间，这个是 @Scheduled 无法实现的。采用编码控制动态任务的方式，我们还可以把动态任务执行信息保存到数据库中，通过数据库里的任务配置数据来动态控制定时任务，也可以通过接口来动态控制定时任务。

## 二、配置定时任务

首先，同 @Scheduled 注解的方式一样，动态控制定时任务也需要使用 @EnableScheduling 注解来开启定时任务功能：

然后通过实现 SchedulingConfigurer 接口来对动态任务进行配置：

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

通过上面的代码，我们就启用了动态任务的基本能力，为动态任务指定了执行线程池。

## 三、动态更新定时任务

更新定时任务通过 CronTask 和 TaskScheduler 来实现，我们新增一个注册定时任务的方法：

```java
    public void registerTask(TaskData taskData) {
        //如果配置一致，则不需要重新创建定时任务
        if (scheduledFutures.containsKey(taskData.getId())
                && cronTasks.get(taskData.getId()).getExpression().equals(taskData.getExpression())) {
            return;
        }
        //如果策略执行时间发生了变化，则取消当前策略的任务
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

我们新增了一个 registerTask 方法用于注册定时任务，入参中 TaskData 是定时任务的配置数据，为了简单，我们把配置数据和执行代码放到了一起：

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

核心代码是创建一个 CronTask 对象，该对象包含两个参数：Runnable 方法和 cron 表达式。
CronTask 对象创建好后，通过 ScheduledTaskRegistrar 对定时任务进行注册，注册完成后，定时任务就会在cron表达式指定的时间点开始执行了。
执行的代码就是 Runnable 参数指定的方法。

## 四、动态停止定时任务

为了能够动态停止定时任务，我们在注册定时任务时，把注册结果放到了一个Map中：

```java
private final ConcurrentHashMap<Long, ScheduledFuture<?>> scheduledFutures = new ConcurrentHashMap<>();

ScheduledFuture<?> future = scheduler.schedule(task.getRunnable(), task.getTrigger());
            if (future != null) {
                scheduledFutures.put(taskData.getId(), future);
            }
```

新增停止定时任务的方法：

```java
public void stop(Long id) {
        if (scheduledFutures.containsKey(id)) {
            scheduledFutures.remove(id).cancel(false);
        }
    }
```

该方法需要传入定时任务的id，由于我们把定时任务信息保存到了 scheduledFutures 这个Map中，所以可以根据任务id参数查找到对应的定时任务信息，然后调用对应的 ```cancel``` 方法来停止定时任务。

## 五、通过接口控制定时任务

通过上面的步骤我们已经具备了动态控制定时任务的基本能力，下面增加接口来控制定时任务：

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

我们提供了 register 和 stop 两个接口，这两个接口会在改变动态任务执行数据时，先将数据保存到数据库中，对定时任务进行持久化，避免程序重启后定时任务都丢失。

程序启动后，我们首先调用 register 接口新增一个定时任务：

```bash
http://localhost:8080/register?name=test
```

接口调用后，在日志中可以看到定时任务开始执行了，register 接口也可以通过 expression 参数更新定时任务的执行时间：

```bash
2024-01-07T18:02:09.003+08:00  INFO 23012 --- [ sys-scheduler5] c.s.springdynamicscheduler.TaskData      : test is running with expression 0/1 * * * * ?
2024-01-07T18:02:10.005+08:00  INFO 23012 --- [ sys-scheduler3] c.s.springdynamicscheduler.TaskData      : test is running with expression 0/1 * * * * ?
2024-01-07T18:02:11.012+08:00  INFO 23012 --- [ sys-scheduler3] c.s.springdynamicscheduler.TaskData      : test is running with expression 0/1 * * * * ?
```

再调用 stop 接口，通过日志可以发现定时任务停止了执行：

```bash
http://localhost:8080/stop?id=1
```