FROM alpine/java:21-jdk

EXPOSE 8000/tcp
COPY build/libs/backend*.jar backend.jar

ENTRYPOINT [ "java", "-jar", "/backend.jar"]
