# Glossary

We are trying to make the purpose and best use of *svcs* as clear as possible, even if you're unfamiliar with all the concepts it's based on.
As such, the glossary got slightly out of hand, but we hope it's to your advantage.

If you want a more narrative introduction into the concepts, we strongly recommend reading the wonderful book [*Architecture Patterns with Python*] (you can read it for free [on the web](https://www.cosmicpython.com/book/preface.html)).

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
    They query databases, make HTTP requests, store data in caches, or delete files.

    But they don't do anything business-relevant neither with the data they send out, nor with the data they get back.

    In an ideal world, they only pass data hence and forth with the domain model which decides what happens next based on plain objects.
    :::


Resource
    Used interchangeably with {term}`service`, but also a heavily overloaded term.


Dependency
    Used interchangeably with {term}`service`, but also a heavily overloaded term.


Service Layer
    The service layer is where your business logic (also known as the *domain model*) meets your {term}`service`s.

    Since services can use other services, it's not a flat layer but more of a tree.
    The entry point is called from your {term}`composition root` (e.g., your web framework's views) and coordinates database transactions, other services and, the domain model.

    If you pass in all the services it needs, it's *{term}`dependency injection`*.
    If you look up the services *within* the service layer, it's *{term}`service location`*.

    An example would be a function for adding users to organizations that takes a database [Unit of Work](https://www.cosmicpython.com/book/chapter_06_uow.html), an email notification queue, an organization ID and a user ID as parameters and queries the domain model if it's OK:

    ```python
    def add_user_to_org(unit_of_work, mail_q, org_id, user_id):
        """
        Service Layer entry point.
        """
        with unit_of_work:
            org = unit_of_work.organizations.get(org_id)
            user = unit_of_work.users.get(user_id)

            domain_model.check_if_can_add_user_to_org(org, user)

            unit_of_work.orgs.add_user(org_id, user_id)
            mail_q.send_welcome_mail(user.email, user.name, org.name)

            unit_of_work.commit()
    ```

    In this case, the `unit_of_work` and `mail_q` parameters are services that are used by the service `add_user_to_org()` and are passed -- or: *injected* -- by the {term}`composition root`.

    The business rules are enforced by `domain_model.check_if_can_add_user_to_org()` which is a pure function working on plain domain objects and doesn't use any services.

    ---

    As you can see, ideally you call service layer functions from your views and pass them all the services it needs to do their job.
    That keeps the service layer clean from any framework-specific code and makes it easy to test.
    You could also call that function from a CLI entry point, a work queue, or a test.

    Admittedly, in simple cases it's possible that the whole logic is in the service layer and you don't need a separate domain model.
    Don't let that discourage you.

    ::: {seealso}
    The fourth chapter of the wonderful [*Architecture Patterns with Python*] book called [*Flask API and Service Layer*](https://www.cosmicpython.com/book/chapter_04_service_layer.html) (you can read it for free on the web).
    :::


Service Location
    See {term}`Service Locator`.

Service Locator
    The [architectural pattern](https://en.wikipedia.org/wiki/Architectural_pattern) implemented by *svcs* and a way to achieve {term}`Inversion of Control` and loose coupling.

    **Like** {term}`dependency injection`, it depends on having a central registry of factories for services that aren't instantiated directly in your business code.

    **Unlike** dependency injection, it's *imperative*:
    You ask for services explicitly at runtime instead of having them injected into your business code.
    The injection also usually requires opaque magic and meddling with your function/method definitions when using dependency injection frameworks.

    The active acquisition of services by calling `get()` when you *know* for sure you're going to need them avoids the conundrum of either having to pass a factory (like a connection pool -- which also puts the onus of cleanup on you) or eagerly creating services that you never use:

    % skip: next

    ```python
    def view(request):
        if request.form.valid():
            # Form is valid; only NOW get a DB connection
            # and pass it into your service layer.
            return handle_form_data(
                svcs_from(request).get(Database),
                form.data,
            )

        raise InvalidFormError()
    ```

    ::: {important}
    If you use *svcs* like in the example above, you're doing {term}`dependency injection` -- and that's a Good Thing™.

    Obtaining the database using {meth}`svcs.Container.get()` *is* service location, but passing it into your {term}`service layer` -- without using it yourself -- makes the view a {term}`composition root` and `handle_form_data()` the entry point into your service layer.

    You could say that you're moving your composition root into the view where it acquires services on demand as it needs them.

    We strongly recommend using *svcs* like this.
    :::

    Classic service location in the service layer would look something like this:

    ```python
    from flask import request

    def view():
        if request.form.valid():
            return handle_form_data(form.data)

    def handle_form_data(data):
        svcs.flask.get(Database).do_database_stuff(data)
    ```

    We do not recommend using *svcs* like this because it's harder to test and reason about.

    ::: {seealso}
    <https://en.wikipedia.org/wiki/Service_locator_pattern>.
    :::


Dependency Injection
    Dependency Injection means that the {term}`service layer` is called with all services it needs to do its job.
    It is a fundamental technique to achieve loose coupling between your business code and the services it depends on -- and to achieve {term}`Inversion of Control`.

    Often when talking about dependency injection, people think of *dependency injection frameworks* that use decorators or other magic to inject services into their code.
    But *dependency injection* just means that services are passed from the outside, with no control over how that happens (hence {term}`Inversion of Control`).

    Our preferred way to use *svcs* is to use it as a {term}`service locator`, but *only* in your {term}`composition root` to acquire necessary services.
    Which then injects said services into your {term}`service layer`:

    ```python
    def view(request):
        """
        View and composition root.
        """
        return do_something(svcs_from(request).get(Database))

    def do_something(db):
        """
        Service layer.
        """
        db.do_database_stuff()
    ```

    In this case `view` uses *svcs* to *locate* a `Database` and then *injects* it into `do_something()`.
    `do_something()` doesn't know where `db` is coming from and how it was created.
    It only knows it needs to do database stuff.

    ::: {seealso}
    - <https://en.wikipedia.org/wiki/Dependency_injection>
    - [*incant*](https://github.com/Tinche/incant), a lovely dependency injection framework for Python.
    :::


Composition Root
    The place that acquires all the services your application needs and calls into the {term}`service layer`.

    Common types are web framework views, CLI command entry points, or test fixtures.

    We recommend using *svcs* in your composition roots to get all the services you need and then pass them into your {term}`service layer`.


IoC
    See {term}`Inversion of Control`.

Inversion of Control
    Inversion of Control is a complicated name for a simple idea.

    In the following code, we have a function that adds a user to a database then sends them an email.
    To do that, it needs an `SmtpSender` and a `DbConnection` which it constructs.
    This makes the code hard to test, since we don't want our unit tests to send people emails.

    ```python
    def add_user(email):
        smtp = SmtpSender()
        db = get_database_connection()

        try:
            user = db.create_user(email)
            smtp.send_welcome_email(user)
        except DuplicateUserError:
            log.warning("Duplicate user", email=email)
    ```

    To fix that, we need to take _control_ of the dependencies out of the function, and provide them somehow, usually through {term}`dependency injection`:

    ```python
    def add_user(email, smtp, db):
        try:
            user = db.create_user(email)
            smtp.send_welcome_email(user)
        except DuplicateUserError:
            log.warning("Duplicate user", email=email)
    ```

    Why do we say IoC and not just dependency injection?
    Inversion of Control is a broader term that applies to any situation where we "invert" the flow of control so that lower-level code (frameworks, data access layers, et cetera) invoke our higher-level code: the business logic we care about.

    ::: {seealso}

    - [*What is Inversion of Control and Why Does it Matter?*](https://seddonym.me/2019/04/15/inversion-of-control/)

    - [*Three Techniques for Inverting Control, in Python*](https://seddonym.me/2019/08/03/ioc-techniques/)

    - [*Hoist Your I/O*](https://www.youtube.com/watch?v=PBQN62oUnN8) -- a 2015 talk by Brandon Rhodes.

    :::


Dependency Inversion Principle
    Sometimes confused with {term}`Dependency Injection` due to the similarity of "Injection" and "Inversion", but only tangentially related.
    It's the D in [SOLID](https://en.wikipedia.org/wiki/SOLID) and also known as "*program against interfaces, not implementations*".

    The goal is to achieve loose coupling by making code depend on interfaces instead of concrete implementations.

    Since Python is dynamic and you're free to ignore type hints in your tests, the usefulness isn't quite as high as in more static languages.
    Nobody will stop you from passing a Mock where a Django `QuerySet` is expected.

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

    - <https://alistair.cockburn.us/hexagonal-architecture/>

    - [*Functional Core, Imperative Shell*](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell) -- a screencast by Gary Bernhardt.

    - [*The Clean Architecture in Python*](https://www.youtube.com/watch?v=DJtef410XaM) -- a 2014 talk by Brandon Rhodes.

    :::


Service Discovery
    An completely unrelated concept for finding *remote* services (e.g., web services, database servers, ...).

    Another sad consequence of the overloaded term {term}`service`.

    Common examples of implementations are [Consul](https://www.consul.io), [*etcd*](https://etcd.io), or [Apache ZooKeeper](https://zookeeper.apache.org).
:::


[*Architecture Patterns with Python*]: https://www.oreilly.com/library/view/architecture-patterns-with/9781492052197/
