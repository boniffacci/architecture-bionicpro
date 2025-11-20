## BionicPRO Reports Service — Java ETL & Analytics


## Задание 1 Диаграмма архитектуры системы 

[Диаграмма архитектуры](./arch/bionicpro_reports_c4_container.puml)

### Таблицы clickhouse
![img.png](img.png)
### health
![img_1.png](img_1.png)
### Получение токена
![img_2.png](img_2.png)

### Отчет в таблице
![img_3.png](img_3.png)

### Получение отчета: curl -s -H "Authorization: Bearer $TOKEN"   "http://localhost:8090/api/reports?userId=user-001&dateFrom=2025-11-19&dateTo=2025-11-20" | jq
![img_4.png](img_4.png)

### DAGs http://localhost:8091/home
![img_5.png](img_5.png)