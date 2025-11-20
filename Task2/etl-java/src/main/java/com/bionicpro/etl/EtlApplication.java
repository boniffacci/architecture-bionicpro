package com.bionicpro.etl;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ConfigurationPropertiesScan
public class EtlApplication {

    public static void main(String[] args) {
        System.exit(SpringApplication.exit(SpringApplication.run(EtlApplication.class, args)));
    }

}



