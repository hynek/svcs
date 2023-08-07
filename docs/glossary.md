# Glossary

:::{glossary}

Service
    Unfortunately, a "service" is a highly overloaded term in software engineering, but we've resisted to come up with a new term that's even more confusing.

    In our context, it's a *local* object managed by *svcs*.
    This can be anything you'd like to be loosely coupled to your application code.
    For example, a database connection, a web API client, or a cache.

    They're usually also something you need to configure before using and can't just instantiate directly in your business code.

    ::: {important}
    One key aspect of these services is that they provide **behavior**, but have **no state** that is relevant to the business logic.
    They are pure *doers*.
    They query a database, make HTTP requests, store data in a cache, or delete files.

    But they don't do anything business-relevant neither with the data they send out, nor with the data they get back.
    :::


Resource
    Used interchangeably with {term}`service`, but also a heavily overloaded term.


Service Layer
    The service layer is where your business logic (also known as the *domain model*) and your {term}`service`s meet.

    Since services can use other services, it's not a flat layer but more of a tree.
    The entry point is called from your {term}`composition root` (e.g., your web framework's views).
    If you pass in all the services it needs, it's {term}`Dependency Injection`.

    An example would be a function that takes a database Unit of Work, an email notification queue, an organization ID and a user ID and adds the user to the organization, if the domain model allows that:

    ```python
    def add_user_to_org(unit_of_work, mail_q, org_id, user_id):
        with unit_of_work:
            org = unit_of_work.organizations.get(org_id)
            user = unit_of_work.users.get(user_id)

            domain_model.check_if_can_add_user_to_org(org, user)

            unit_of_work.orgs.add_user(org_id, user_id)
            mail_q.send_welcome_mail(user.email)

            unit_of_work.commit()
    ```

    In this case, the `unit_of_work` and `mail_q` parameters are services that are used by the service `add_user_to_org()` and are *injected* by the {term}`composition root`.

    The business rules are enforced by `domain_model.check_if_can_add_user_to_org()` which is a pure function working on plain domain objects and doesn't use any services.

    ---

    As you can see, ideally you call service layer functions from your views and pass them all the services it needs to do their job.
    That keeps the service layer clean from any framework-specific code and makes it easy to test.
    You could also call that function from a CLI command, a work queue, or a test.

    You can also let the service layer find it's services by using a {term}`service locator` like *svcs* **inside of the service layer** but that makes it a lot harder to test and reason about.

    Admittedly, in simple cases it's possible that the whole logic is in the service layer and you don't need a separate domain model.
    Don't let that discourage you.

    ::: {seealso}
    The fourth chapter of the wonderful [*Architecture Patterns with Python*] book called [*Flask API and Service Layer*](https://www.cosmicpython.com/book/chapter_04_service_layer.html) (you can read it for free on the web).
    :::


Service Locator
    The [architectural pattern](https://en.wikipedia.org/wiki/Architectural_pattern) implemented by *svcs*.

    **Like** {term}`dependency injection`, it's a way to achieve loose coupling between your business code and the services it depends on by having a central registry of factories for those services.

    **Unlike** dependency injection, it's *imperative* (and not declarative), as you ask for services explicitly at runtime instead of having them injected into your business code based on function parameter types, or similar.

    That usually requires less opaque magic since nothing meddles with your function/method definitions.

    The active acquisition of resources by calling `get()` when you *know* for sure you're going to need it avoids the conundrum of either having to pass a factory (e.g., a connection pool – which also puts the onus of cleanup on you) or eagerly creating resources that you never use:

    % skip: next

    ```python
    def view(request):
        if request.form.valid():
            # Form is valid; only NOW get a DB connection
            # and pass it into your business logic.
            return handle_form_data(
                request.services.get(Database),
                form.data,
            )

        raise InvalidFormError()
    ```

    But you can use, e.g., your web framework's injection capabilities to inject the locator object into your views and benefit from *svcs*'s upsides without giving up some of DI's ones.

    ::: {seealso}
    <https://en.wikipedia.org/wiki/Service_locator_pattern>.
    :::


Dependency Injection
    Dependency Injection means that the {term}`service layer` is called with all services it needs to do its job.
    It is a fundamental technique to achieve loose coupling between your business code and the services it depends on – and to achieve {term}`Inversion of Control`.

    Often when talking about dependency injection, people think of *dependency injection frameworks* that use decorators or other magic to inject services into their code.
    But *dependency injection* just means that services are passed from the outside, with no

    Our preferred way to use *svcs* is to use it as a {term}`service locator`, but in your {term}`composition root`, which then injects the services into your {term}`service layer`:

    ```python
    def view(request):
        return do_something(request.svcs.get(Database))

    def do_something(db):
        db.do_database_stuff()
    ```

    In this case `view` uses *svcs* to *locate* a `Database` and then *injects* it into `do_something()`.

    ::: {seealso}
    - <https://en.wikipedia.org/wiki/Dependency_injection>
    - [*incant*](https://github.com/Tinche/incant), a lovely package that implements dependency injection in Python.
    :::


Composition Root
    The place that collects all the services your application needs and calls into the {term}`service layer`.

    Common types are web framework views, CLI command entry points, or test fixtures.


Dependency Inversion Principle
    Sometimes confused with {term}`Dependency Injection` due to the similarity of "Injection" and "Inversion", but only tangentially related.
    It's the D in [SOLID](https://en.wikipedia.org/wiki/SOLID) and also known as "*program against interfaces, not implementations*".

    The goal is to achieve loose coupling by making code depend on interfaces instead of concrete implementations.

    Given that Python is dynamic and you're free to ignore type hints in your tests, the usefulness isn't quite as high as in more static languages.
    Nobody is going to stop you to pass a Mock where a Django `QuerySet` is expected.

    ::: {seealso}
    - {doc}`typing-caveats` regarding abstract classes and *svcs*.

    - <https://en.wikipedia.org/wiki/Dependency_inversion_principle>

    - The third chapter of the wonderful [*Architecture Patterns with Python*] book called [*On Coupling and Abstractions*](https://www.cosmicpython.com/book/chapter_03_abstractions.html) (you can read it for free on the web).
    :::


Hexagonal Architecture
    Also known as "*ports and adapters*", "*onion architecture*", or "*clean architecture*".
    They all have slightly different meaning, but the core idea is the same.

    It divides a system into several loosely-coupled interchangeable components, such as the database, the user interface, test scripts, and interfaces with other systems (also known as services) with the application core (also known as business code) in the middle.

    The business code doesn't use those services directly, but only through interfaces that are called *ports* here.

    Now a service locator like *svcs* can be used to register factories for those interfaces such that the business code can use the services as *adapters* to the real world (e.g., query a database) without knowing what they are and where they come from.

    It is therefore a special case of the {term}`Dependency Inversion Principle`.

    The *svcs* logo is a hexagon to remind you of this architecture.

    ::: {seealso}
    - <https://en.wikipedia.org/wiki/Hexagonal_architecture_(software)>

    - [*Functional Core, Imperative Shell*](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell)

    - <https://alistair.cockburn.us/hexagonal-architecture/>
    :::


IoC
    See {term}`Inversion of Control`.


Inversion of Control
    ::: {seealso}
    - [*What is Inversion of Control and Why Does it Matter?*](https://seddonym.me/2019/04/15/inversion-of-control/)
    - [*Three Techniques for Inverting Control, in Python*](https://seddonym.me/2019/08/03/ioc-techniques/)
    :::


Service Discovery
    An completely unrelated concept for finding *remote* services (e.g., web services, database servers, ...).

    Another sad consequence of the overloaded term {term}`service`.

    Common examples of implementations are [Consul](https://www.consul.io), [*etcd*](https://etcd.io), or [Apache ZooKeeper](https://zookeeper.apache.org).
:::


[*Architecture Patterns with Python*]: https://www.oreilly.com/library/view/architecture-patterns-with/9781492052197/
