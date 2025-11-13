FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /app

# Копируем pom.xml и загружаем зависимости (для кэширования слоя)
COPY pom.xml .
RUN mvn dependency:go-offline

# Копируем исходный код и собираем приложение
COPY src ./src
RUN mvn clean package -DskipTests

# Production образ
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# Копируем JAR из build stage
COPY --from=build /app/target/*.jar app.jar

# Создаём непривилегированного пользователя
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring

# Expose port
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8090/api/reports/health || exit 1

# Запуск приложения
ENTRYPOINT ["java", "-jar", "app.jar"]



