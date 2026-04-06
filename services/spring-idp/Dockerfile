# ============================================
# ForgeLink Spring IDP - Multi-stage Dockerfile
# ============================================

# -------------------- Builder --------------------
FROM eclipse-temurin:25-jdk-alpine as builder

WORKDIR /app

# Install Maven
RUN apk add --no-cache maven

# Copy pom.xml first for dependency caching
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source and build
COPY src ./src
RUN mvn package -DskipTests -B

# -------------------- Development --------------------
FROM eclipse-temurin:25-jdk-alpine as development

WORKDIR /app

RUN apk add --no-cache maven

COPY pom.xml .
COPY src ./src

# Enable remote debugging
ENV JAVA_TOOL_OPTIONS="-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005"

EXPOSE 8080 5005

CMD ["mvn", "spring-boot:run"]

# -------------------- Production --------------------
FROM gcr.io/distroless/java21-debian12 as production

WORKDIR /app

# Copy the built JAR from builder
COPY --from=builder /app/target/*.jar app.jar

# Non-root user (distroless already runs as nonroot)
USER nonroot

EXPOSE 8080

# Note: HEALTHCHECK not supported in distroless - use K8s probes instead

ENTRYPOINT ["java", "-jar", "app.jar"]
