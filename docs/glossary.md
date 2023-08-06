# Glossary

:::{glossary}

Service
    Unfortunately, a "service" is a highly overloaded term in software engineering, but we've resisted to come up with a new term that's even more confusing.

    In our context, it's a runtime-{term}`resource` managed by *svcs*.  This can be anything you'd like to be loosely coupled to your application code.
    For example, a database connection, a web API client, or a cache.

    It's usually also something you need to configure before using and can't just instantiate directly in your business code.

Resource
    Used interchangeably with {term}`service`, but also a heavily overloaded term.

Service Layer
    A service layer is sadly not the layer where {term}`service`s live – it's the layer where services *are used*.

    Ideally you call its functions from your views and pass it all the services it needs to do its job.
    That keeps the service layer clean from any framework-specific code and makes it easy to test.

    ::: {seealso}
    The fourth chapter of the wonderful [*Architecture Patterns with Python*] book called [*Flask API and Service Layer*](https://www.cosmicpython.com/book/chapter_04_service_layer.html) (you can read it for free on the web).
    :::

Service Locator
    The [architectural pattern](https://en.wikipedia.org/wiki/Architectural_pattern) implemented by *svcs*.

    **Like** {term}`dependency injection`, it's a way to achieve loose coupling between your business code and the services it depends on by having a central registry of factories for those services.

    **Unlike** dependency injection, it's *imperative* (and not declarative), as you ask for services explicitly at runtime instead of having them injected into your business code based on function parameter types, or similar.

    ::: {seealso}
    <https://en.wikipedia.org/wiki/Service_locator_pattern>.
    :::

Dependency Injection
    Similar to {term}`service locator`, but declarative.
    The injected services are usually passed into the business code as function parameters.

    ::: {seealso}
    - <https://en.wikipedia.org/wiki/Dependency_injection>
    - [*incant*](https://github.com/Tinche/incant), a lovely package that implements dependency injection in Python.
    :::

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

Service Discovery
    An completely unrelated concept of finding services (e.g., web services) running elsewhere.

    Common examples of implementations are [Consul](https://www.consul.io), [*etcd*](https://etcd.io), or [Apache ZooKeeper](https://zookeeper.apache.org).
:::


[*Architecture Patterns with Python*]: https://www.oreilly.com/library/view/architecture-patterns-with/9781492052197/
