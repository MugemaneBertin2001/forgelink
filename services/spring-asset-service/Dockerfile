# ============================================
# ForgeLink Spring Asset Service - Multi-stage Dockerfile
# ============================================

# -------------------- Builder --------------------
FROM eclipse-temurin:21-jdk-alpine as builder

WORKDIR /app

RUN apk add --no-cache maven

COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn package -DskipTests -B

# -------------------- Development --------------------
FROM eclipse-temurin:21-jdk-alpine as development

WORKDIR /app

RUN apk add --no-cache maven

COPY pom.xml .
COPY src ./src

ENV JAVA_TOOL_OPTIONS="-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5006"

EXPOSE 8081 5006

CMD ["mvn", "spring-boot:run"]

# -------------------- Production --------------------
FROM gcr.io/distroless/java21-debian12 as production

WORKDIR /app

COPY --from=builder /app/target/*.jar app.jar

USER nonroot

EXPOSE 8081

ENTRYPOINT ["java", "-jar", "app.jar"]
