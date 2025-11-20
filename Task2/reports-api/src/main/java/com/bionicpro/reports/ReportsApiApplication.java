package com.bionicpro.reports;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class ReportsApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(ReportsApiApplication.class, args);
    }

}



