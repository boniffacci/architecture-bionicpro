plugins {
	java
	id("org.springframework.boot") version "3.1.5"
	id("io.spring.dependency-management") version "1.1.3"
}
 
group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
	toolchain {
		languageVersion = JavaLanguageVersion.of(21)
	}
}

repositories {
	mavenCentral()
	maven { url = uri("https://repo.spring.io/milestone") }
	maven { url = uri("https://repo.spring.io/snapshot") }
}

dependencyManagement {
	imports {
		mavenBom("org.keycloak.bom:keycloak-adapter-bom:12.0.3")
	}
}

dependencies {
	implementation ("org.springframework.boot:spring-boot-starter-oauth2-client")
	implementation ("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
	implementation ("org.springframework.boot:spring-boot-starter-security")
	implementation ("org.springframework.boot:spring-boot-starter-thymeleaf")
	implementation ("org.springframework.boot:spring-boot-starter-web")
	implementation ("org.thymeleaf.extras:thymeleaf-extras-springsecurity6")
	compileOnly ("org.projectlombok:lombok")
	annotationProcessor ("org.projectlombok:lombok")
	testImplementation ("org.springframework.boot:spring-boot-starter-test")
	testImplementation ("org.springframework.security:spring-security-test")
}

tasks.withType<Test> {
	useJUnitPlatform()
}
