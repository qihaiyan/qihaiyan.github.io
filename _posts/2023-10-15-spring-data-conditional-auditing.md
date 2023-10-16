---
layout: post
title:  "Spring Data Envers 支持有条件变动纪录的保存和查询"
date:   2023-10-15 16:20:00 +0800
tags: [spring,java]
categories: [spring boot]
image: assets/images/data-audit.jpg
---

数据审计是业务系统的一个基本能力，需要系统能够将关键数据的变动纪录都保存下来，并支持变动纪录的查询。

通过spring-data-envers可以很容易的实现数据变动纪录的保存和查询。

有些情况下，我们需要只保存满足特定条件的数据变动纪录，不满足条件的变动纪录不进行保存，例如只保存某个字段有值的变动纪录。

本文介绍支持有条件变动纪录的保存和查询的方法。

具体的代码参照 [示例项目 https://github.com/qihaiyan/springcamp/tree/master/spring-data-envers-conditional](https://github.com/qihaiyan/springcamp/tree/master/spring-data-envers-conditional)

## 一、概述

可以通过 spring-data-envers 很容易的实现变动纪录的保存和查询，只需要增加几个注解就可以。但是要实现有条件的变动纪录的保存和查询就需要进行一些复杂的处理。

## 二、使用 spring-data-envers

首先引入 spring-data-envers 依赖。

在 build.gradle 中增加一行代码:

``` groovy
implementation 'org.springframework.data:spring-data-envers'
```

在实体类上增加 Audited 注解：

``` java
@Data
@Entity
@Audited
public class MyData {
    @Id
    @GeneratedValue
    private Long id;

    private String author;
}
```

Repository 扩展 RevisionRepository 方法：

``` java
public interface MyDataRepository extends JpaRepository<MyData, Long>, RevisionRepository<MyData, Long, Integer> {
}
```

通过以上3步操作，就添加好了变动纪录的保存功能，我们可以通过调用变动纪录查询方法确认变动纪录保存成功。

当 Repository 扩展 RevisionRepository 方法后，会有一个默认实现的 findRevisions 方法，我们可以直接调用：

``` java
public Revisions<Integer, MyData> findRevisions(Long id) {
        return myDataRepository.findRevisions(id);
}
```

最后我们可以执行完整的主体数据的保存，在控制台中打印变动纪录：

``` java
@Override
public void run(String... args) {
        MyData myData = new MyData();
        myData.setId(1L);
        myData.setAuthor("test");
        dbService.saveData(myData);
        dbService.findRevisions(myData.getId()).forEach(r -> System.out.println("revision: " + r.toString()));


        myData.setAuthor("newAuthor");
        dbService.saveData(myData);
        dbService.findRevisions(myData.getId()).forEach(r -> System.out.println("revision: " + r.toString()));
}
```

执行完程序后，可以看到两次保存数据的操作都可以查询到对应的变动纪录，并且变动纪录还通过 revisionType 显示了是插入还是更新操作：

```
revision: Revision 1 of entity MyData(id=1, author=test) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 1, revisionDate = Oct 15, 2023, 11:41:15 AM), revisionType=INSERT}
revision: Revision 2 of entity MyData(id=1, author=newAuthor) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 2, revisionDate = Oct 15, 2023, 11:41:16 AM), revisionType=UPDATE}
```

## 三、通过自定义 Event Listener 实现有条件的变动纪录的保存

在进行数据变动时， Envers 通过监听事件来进行对应的处理，总共有以下几个监听事件：

``` java
EventType.POST_INSERT
EventType.PRE_UPDATE
EventType.POST_UPDATE
EventType.POST_DELETE
EventType.POST_COLLECTION_RECREATE
EventType.PRE_COLLECTION_REMOVE
EventType.PRE_COLLECTION_UPDATE
```

每个监听事件都对应着特定的 Listener ，在本文实例中，我们期望当 author 的值被更新为空时，不保存变动纪录，我们可以通过自定义 PRE_UPDATE 和 POST_UPDATE 的Listener来实现。

因为框架提供了默认的Listener，因此自定义 Listener 只需要扩展默认的Listener，并加入我们自己的特有逻辑就可以。

MyEnversPostUpdateEventListenerImpl ：

``` java
public class MyEnversPreUpdateEventListenerImpl extends EnversPreUpdateEventListenerImpl {

    public MyEnversPreUpdateEventListenerImpl(EnversService enversService) {
        super(enversService);
    }

    @Override
    public boolean onPreUpdate(PreUpdateEvent event) {
        if (event.getEntity() instanceof MyData
                && ((MyData) event.getEntity()).getAuthor() == null) {
            return false;
        }

        return super.onPreUpdate(event);
    }

}
```

MyEnversPostUpdateEventListenerImpl: 

``` java
public class MyEnversPostUpdateEventListenerImpl extends EnversPostUpdateEventListenerImpl {

    public MyEnversPostUpdateEventListenerImpl(EnversService enversService) {
        super(enversService);
    }

    @Override
    public void onPostUpdate(PostUpdateEvent event) {
        if (event.getEntity() instanceof MyData && ((MyData) event.getEntity()).getAuthor() == null) {
            return;
        }

        super.onPostUpdate(event);
    }
}
```

在自定义 Listener 中，我们增加了 对于 author 字段是否为空的判断逻辑。

## 四、自定义 Event Listener 注册到系统中

自定义 Event Listener 完成后，我们还需要让框架执行我们自定义的 Listener， 而不是用默认的 Listener。

框架通过 EnversIntegrator 类注册的 Listener, 我们要做的是重新实现 EnversIntegrator , 在本实例中重新实现的类为 MyEnversIntegrator :

```java
public class MyEnversIntegrator implements Integrator {
    @Override
    public void integrate(Metadata metadata,
                          BootstrapContext bootstrapContext,
                          SessionFactoryImplementor sessionFactory) {

        final ServiceRegistry serviceRegistry = sessionFactory.getServiceRegistry();
        final EnversService enversService = serviceRegistry.getService(EnversService.class);

        final EventListenerRegistry listenerRegistry = serviceRegistry.getService(EventListenerRegistry.class);
        listenerRegistry.addDuplicationStrategy(EnversListenerDuplicationStrategy.INSTANCE);

        if (enversService.getEntitiesConfigurations().hasAuditedEntities()) {
            listenerRegistry.appendListeners(
                    EventType.POST_DELETE,
                    new EnversPostDeleteEventListenerImpl(enversService)
            );
            listenerRegistry.appendListeners(
                    EventType.POST_INSERT,
                    new EnversPostInsertEventListenerImpl(enversService)
            );
            listenerRegistry.appendListeners(
                    EventType.PRE_UPDATE,
                    new MyEnversPreUpdateEventListenerImpl(enversService)
            );
            listenerRegistry.appendListeners(
                    EventType.POST_UPDATE,
                    new MyEnversPostUpdateEventListenerImpl(enversService)
            );
            listenerRegistry.appendListeners(
                    EventType.POST_COLLECTION_RECREATE,
                    new EnversPostCollectionRecreateEventListenerImpl(enversService)
            );
            listenerRegistry.appendListeners(
                    EventType.PRE_COLLECTION_REMOVE,
                    new EnversPreCollectionRemoveEventListenerImpl(enversService)
            );
            listenerRegistry.appendListeners(
                    EventType.PRE_COLLECTION_UPDATE,
                    new EnversPreCollectionUpdateEventListenerImpl(enversService)
            );
        }
    }

    @Override
    public void disintegrate(SessionFactoryImplementor sessionFactory, SessionFactoryServiceRegistry serviceRegistry) {
        // nothing to do
    }
}
```

通过代码可以发现，我们只是修改了 PRE_UPDATE 和 POST_UPDATE 注册的 Listener , 其它事件的 Listener 仍然用框架默认的。

最后我们需要把我们实现的 MyEnversIntegrator 放到 META-INF/services/org.hibernate.integrator.spi.Integrator 这个配置文件中。

```
cn.springcamp.springdata.envers.MyEnversIntegrator
```

## 五、确认有条件变动纪录的保存是否生效

最后我们修改控制台打印程序，将 author 字段更新为 null 并保存，查看变动纪录里是否有这个更新操作的纪录。

增加保存代码 :

``` java
// won't generate audit record when author is null
myData.setAuthor(null);
dbService.saveData(myData);
dbService.findRevisions(myData.getId()).forEach(r -> System.out.println("revision: " + r.toString()));
```

执行程序并观察控制台打印内容：

```
revision: Revision 1 of entity MyData(id=1, author=test) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 1, revisionDate = Oct 15, 2023, 11:41:15 AM), revisionType=INSERT}
revision: Revision 2 of entity MyData(id=1, author=newAuthor) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 2, revisionDate = Oct 15, 2023, 11:41:16 AM), revisionType=UPDATE}
```

通过打印内容可以确认，author 字段更新为 null 的变动纪录没有被纪录，说明我们的处理是生效的。