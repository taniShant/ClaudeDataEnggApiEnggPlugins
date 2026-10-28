# javax → jakarta Mapping

## Package Mapping

| javax Package | jakarta Package | Dependency |
|---|---|---|
| `javax.servlet.*` | `jakarta.servlet.*` | Provided by Spring Boot 3 |
| `javax.validation.*` | `jakarta.validation.*` | `jakarta.validation:jakarta.validation-api:3.0.2` |
| `javax.persistence.*` | `jakarta.persistence.*` | `jakarta.persistence:jakarta.persistence-api:3.1.0` |
| `javax.annotation.*` | `jakarta.annotation.*` | `jakarta.annotation:jakarta.annotation-api:2.1.1` |
| `javax.inject.*` | `jakarta.inject.*` | `jakarta.inject:jakarta.inject-api:2.0.1` |
| `javax.transaction.*` | `jakarta.transaction.*` | `jakarta.transaction:jakarta.transaction-api:2.0.1` |
| `javax.ws.rs.*` | `jakarta.ws.rs.*` | `jakarta.ws.rs:jakarta.ws.rs-api:4.0.0` |
| `javax.xml.bind.*` | `jakarta.xml.bind.*` | `jakarta.xml.bind:jakarta.xml.bind-api:4.0.2` + `org.glassfish.jaxb:jaxb-runtime:4.0.5` |
| `javax.mail.*` | `jakarta.mail.*` | `jakarta.mail:jakarta.mail-api:2.1.3` |
| `javax.activation.*` | `jakarta.activation.*` | `jakarta.activation:jakarta.activation-api:2.1.3` |
| `javax.el.*` | `jakarta.el.*` | `jakarta.el:jakarta.el-api:5.0.1` |
| `javax.faces.*` | `jakarta.faces.*` | `jakarta.faces:jakarta.faces-api:4.0.1` |

## DO NOT Replace (JDK packages)

`javax.swing`, `javax.crypto`, `javax.net`, `javax.sql`, `javax.naming`, `javax.management`, `javax.security.auth`, `javax.imageio`, `javax.sound`, `javax.print`, `javax.xml.parsers`, `javax.xml.transform`, `javax.xml.xpath`

## Key Points

- JAXB requires both API and runtime dependencies
- web.xml namespace changes: `http://xmlns.jcp.org/xml/ns/javaee` → `https://jakarta.ee/xml/ns/jakartaee`
- Most javax Enterprise packages are provided by Spring Boot 3 dependency management
