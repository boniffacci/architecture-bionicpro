# Сдача проектной работы 9 спринта

## Задание 1. Повышение безопасности системы

1. [диаграмма](https://drive.google.com/file/d/1bP4TGxW8FGkh9_jxoARsXJKgMDPVWP05/view?usp=sharing, "диаграмма")

## Задача 2. Улучшите безопасность существующего приложения, заменив Code Grant на PKCE

Clickhouse слишком хлопотно, как и выгрузка за конкретные даты, нужно интерфейс писать. Реализовал OLAP на PostgreSQL

1. [диаграмма]("https://drive.google.com/file/d/1X3OlEfDEQUajJNN5xkmB_01UY0uVSaeD/view?usp=sharing", "диаграмма")
2. Код Airflow в папке проекта **airflow**
3. API в папке **backend**
4. user1 не имеет доступа, получит ошибку **403: Insufficient role**. prothetic1 имеет доступ и получит свой отчёт 
5. [UI кнопка для отчёта](https://disk.yandex.ru/i/-kQhnAhK2RM9VA, "UI кнопка")

## Как запустить
1. UP docker-compose.yaml
2. Отклываем Airflow UI http://localhost:8081/home, убеждается, что пайплайны подняты: **init_data** и **olap_pipeline**
3. **init_data** срабатывает единожды
4. **olap_pipeline** срабатывает каждые 5 минут
5. http://localhost:3000/ логинимся под **prothetic[1..3]**, нажимаем кнопку **Download Report**
6. Выгружаются только от **prothetic[1..3]**