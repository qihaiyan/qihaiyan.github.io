---
layout: post
title:  "Conditional Audit Records with Spring Data Envers"
date:   2023-10-15 16:20:00 +0800
lang: en
slug_zh: spring-data-conditional-auditing
tags: [spring,java]
categories: [spring boot]
image: assets/images/data-audit.jpg
description: "Save and query data audit records with Spring Data Envers, and record audit entries only when custom conditions are met, using custom event listeners."
---

Data auditing is a basic capability of business systems: the system needs to persist the change history of key data and support querying that history.

With spring-data-envers, saving and querying data change records can be implemented easily.

In some cases, we only want to save the change records that meet specific conditions, and skip the ones that don't — for example, only save change records where a certain field has a value.

This post describes how to support conditional saving and querying of change records.

The complete code is available in the example project [https://github.com/qihaiyan/springcamp/tree/main/spring-data-envers-conditional](https://github.com/qihaiyan/springcamp/tree/main/spring-data-envers-conditional).

## 1. Overview

With spring-data-envers, saving and querying change records is easy — adding a few annotations is enough. Implementing conditional saving and querying of change records, however, requires some complex handling.

## 2. Using spring-data-envers

First, add the spring-data-envers dependency.

Add one line to build.gradle:

``` groovy
implementation 'org.springframework.data:spring-data-envers'
```

Add the Audited annotation to the entity class:

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

Extend RevisionRepository in the repository:

``` java
public interface MyDataRepository extends JpaRepository<MyData, Long>, RevisionRepository<MyData, Long, Integer> {
}
```

With these 3 steps, the saving of change records is in place. We can confirm that the records are saved successfully by calling the revision query method.

Once the repository extends RevisionRepository, a default findRevisions implementation is available, which we can call directly:

``` java
public Revisions<Integer, MyData> findRevisions(Long id) {
        return myDataRepository.findRevisions(id);
}
```

Finally, we can run a complete save of the main entity data and print the change records to the console:

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

After running the program, we can see that both save operations have corresponding change records, and each record also shows through revisionType whether the operation was an insert or an update:

```
revision: Revision 1 of entity MyData(id=1, author=test) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 1, revisionDate = Oct 15, 2023, 11:41:15 AM), revisionType=INSERT}
revision: Revision 2 of entity MyData(id=1, author=newAuthor) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 2, revisionDate = Oct 15, 2023, 11:41:16 AM), revisionType=UPDATE}
```

## 3. Conditional Saving of Change Records with a Custom Event Listener

When data changes occur, Envers handles them by listening to events. The following events are listened to:

``` java
EventType.POST_INSERT
EventType.PRE_UPDATE
EventType.POST_UPDATE
EventType.POST_DELETE
EventType.POST_COLLECTION_RECREATE
EventType.PRE_COLLECTION_REMOVE
EventType.PRE_COLLECTION_UPDATE
```

Each event has a specific Listener. In this example, we want to skip saving the change record when the author value is updated to null, which we can achieve by customizing the PRE_UPDATE and POST_UPDATE listeners.

Since the framework provides default listeners, the custom listeners only need to extend the default ones and add our own specific logic.

MyEnversPostUpdateEventListenerImpl:

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

In the custom listeners, we added the logic that checks whether the author field is null.

## 4. Registering the Custom Event Listeners

Once the custom event listeners are done, we still need the framework to run our custom listeners instead of the default ones.

The framework registers listeners through the EnversIntegrator class. What we need to do is reimplement EnversIntegrator; in this example, the reimplemented class is MyEnversIntegrator:

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

As the code shows, we only changed the listeners registered for PRE_UPDATE and POST_UPDATE; the listeners for the other events still use the framework defaults.

Finally, we need to put our MyEnversIntegrator implementation into the META-INF/services/org.hibernate.integrator.spi.Integrator configuration file.

```
cn.springcamp.springdata.envers.MyEnversIntegrator
```

## 5. Verifying That the Conditional Saving of Change Records Works

Finally, we modify the console program to update the author field to null and save, then check whether this update operation appears in the change records.

Add the save code:

``` java
// won't generate audit record when author is null
myData.setAuthor(null);
dbService.saveData(myData);
dbService.findRevisions(myData.getId()).forEach(r -> System.out.println("revision: " + r.toString()));
```

Run the program and observe the console output:

```
revision: Revision 1 of entity MyData(id=1, author=test) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 1, revisionDate = Oct 15, 2023, 11:41:15 AM), revisionType=INSERT}
revision: Revision 2 of entity MyData(id=1, author=newAuthor) - Revision metadata DefaultRevisionMetadata{entity=DefaultRevisionEntity(id = 2, revisionDate = Oct 15, 2023, 11:41:16 AM), revisionType=UPDATE}
```

The output confirms that the change record for updating the author field to null was not recorded, which means our handling is effective.
