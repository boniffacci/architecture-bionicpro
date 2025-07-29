FROM gradle:8.14.3-jdk21-alpine AS build
COPY --chown=gradle:gradle . /home/gradle/src
WORKDIR /home/gradle/src
RUN gradle build --no-daemon


FROM openjdk:21-jdk

RUN mkdir /app

COPY --from=build /home/gradle/src/build/libs/*.jar /app/app.jar

EXPOSE 8000

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
