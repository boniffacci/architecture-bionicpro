FROM openjdk:21-jdk-slim
ARG JAR_FILE=build/libs/*.jar
COPY ${JAR_FILE} reports-backend-0.0.1-SNAPSHOT.jar
EXPOSE 8081
ENTRYPOINT ["java","-jar","/reports-backend-0.0.1-SNAPSHOT.jar"]