package com.bionicpro.etl;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * BionicPRO ETL Application
 * 
 * Spring Batch приложение для ETL процессов:
 * - Извлечение данных из CRM (REST API)
 * - Извлечение телеметрии из Core DB (PostgreSQL)
 * - Агрегация и загрузка в ClickHouse
 * 
 * Запуск из командной строки:
 * java -jar etl.jar --job=extractCrmJob
 * java -jar etl.jar --job=extractTelemetryJob  
 * java -jar etl.jar --job=buildMartJob
 */
@SpringBootApplication
@EnableScheduling
@ConfigurationPropertiesScan
public class EtlApplication {

    public static void main(String[] args) {
        System.exit(SpringApplication.exit(SpringApplication.run(EtlApplication.class, args)));
    }

}



