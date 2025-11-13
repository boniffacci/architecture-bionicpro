FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /app

# Копируем pom.xml и загружаем зависимости
COPY pom.xml .
RUN mvn dependency:go-offline

# Копируем исходный код и собираем
COPY src ./src
RUN mvn clean package -DskipTests

# Production образ
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Копируем JAR из build stage
COPY --from=build /app/target/*.jar etl-java.jar

# Создаём пользователя
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring

# Запуск (переопределяется в docker-compose или Airflow)
ENTRYPOINT ["java", "-jar", "etl-java.jar"]



