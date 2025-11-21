# Этап 1: сборка jar
FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /app

# Копируем pom.xml и зависимости
COPY pom.xml .
RUN mvn dependency:go-offline

# Копируем исходники и собираем
COPY src ./src
RUN mvn clean package -DskipTests

# Этап 2: запуск приложения
FROM eclipse-temurin:21-jdk
WORKDIR /app

# Копируем jar из предыдущего этапа
COPY --from=build /app/target/reports-api-0.0.1-SNAPSHOT.jar app.jar

# Экспонируем порт
EXPOSE 8000

# Запуск
ENTRYPOINT ["java","-jar","app.jar"]