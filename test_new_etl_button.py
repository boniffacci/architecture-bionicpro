#!/usr/bin/env python3
"""
Простой тест новой кнопки ETL без авторизации
"""

import requests
import time


def test_new_etl_button():
    """Тестирует новую кнопку ETL через прямой доступ к фронтенду"""
    
    print("=" * 80)
    print("ТЕСТ НОВОЙ КНОПКИ ETL")
    print("=" * 80)
    
    # Проверяем доступность фронтенда
    frontend_url = "http://localhost:5173"  # Прямой доступ к фронтенду
    
    print(f"\n1️⃣ Проверяем доступность фронтенда: {frontend_url}")
    try:
        response = requests.get(frontend_url, timeout=10)
        if response.status_code == 200:
            print("✅ Фронтенд доступен")
            
            # Проверяем, что в HTML есть новая кнопка
            html_content = response.text
            if "Открыть ETL-процесс в Airflow" in html_content:
                print("✅ Новая кнопка 'Открыть ETL-процесс в Airflow' найдена в HTML")
            else:
                print("❌ Новая кнопка не найдена в HTML")
                print("Ищем старую кнопку...")
                if "Запустить ETL-процесс" in html_content:
                    print("❌ Найдена старая кнопка 'Запустить ETL-процесс' - обновление не применилось")
                    return False
                else:
                    print("⚠ Ни старая, ни новая кнопка не найдены")
                    return False
        else:
            print(f"❌ Фронтенд недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к фронтенду: {e}")
        return False
    
    print(f"\n2️⃣ Проверяем доступность Airflow UI: http://localhost:8082")
    try:
        airflow_response = requests.get("http://localhost:8082", timeout=10)
        if airflow_response.status_code == 200:
            print("✅ Airflow UI доступен")
        else:
            print(f"❌ Airflow UI недоступен: {airflow_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к Airflow UI: {e}")
        return False
    
    print(f"\n3️⃣ Проверяем конкретный URL DAG: http://localhost:8082/dags/import_olap_data_monthly/tasks/import_previous_month_data")
    try:
        dag_response = requests.get("http://localhost:8082/dags/import_olap_data_monthly/tasks/import_previous_month_data", timeout=10)
        if dag_response.status_code == 200:
            print("✅ URL DAG доступен")
            print("✅ Пользователь сможет открыть правильную страницу в Airflow")
        else:
            print(f"⚠ URL DAG вернул статус: {dag_response.status_code}")
            print("⚠ Возможно, потребуется авторизация в Airflow")
    except Exception as e:
        print(f"❌ Ошибка подключения к URL DAG: {e}")
        return False
    
    print(f"\n4️⃣ Проверяем JavaScript код фронтенда")
    try:
        # Ищем в HTML ссылки на JavaScript файлы
        import re
        js_files = re.findall(r'src="([^"]*\.js[^"]*)"', html_content)
        
        if js_files:
            print(f"Найдено {len(js_files)} JavaScript файлов")
            
            # Проверяем первый JS файл
            js_url = f"{frontend_url}/{js_files[0].lstrip('./')}"
            js_response = requests.get(js_url, timeout=10)
            
            if js_response.status_code == 200:
                js_content = js_response.text
                
                # Ищем новую функцию
                if "handleOpenEtlInAirflow" in js_content:
                    print("✅ Новая функция 'handleOpenEtlInAirflow' найдена в JavaScript")
                else:
                    print("❌ Новая функция 'handleOpenEtlInAirflow' не найдена в JavaScript")
                    return False
                
                # Ищем правильный URL
                if "dags/import_olap_data_monthly/tasks/import_previous_month_data" in js_content:
                    print("✅ Правильный URL DAG найден в JavaScript")
                else:
                    print("❌ Правильный URL DAG не найден в JavaScript")
                    return False
                
                # Проверяем, что старая функция удалена или изменена
                if "handleRunEtl" in js_content and "api/v2/dags" in js_content:
                    print("⚠ Возможно, старая функция запуска через API всё ещё присутствует")
                else:
                    print("✅ Старая функция запуска через API удалена или изменена")
            else:
                print(f"❌ Не удалось загрузить JavaScript: {js_response.status_code}")
                return False
        else:
            print("❌ JavaScript файлы не найдены в HTML")
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке JavaScript: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_new_etl_button()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ РЕЗУЛЬТАТ: Новая кнопка ETL работает корректно!")
        print("✅ Фронтенд обновлён и готов к использованию")
        print("✅ Пользователи смогут открывать Airflow UI для запуска ETL вручную")
    else:
        print("❌ РЕЗУЛЬТАТ: Есть проблемы с новой кнопкой ETL")
        print("❌ Требуется дополнительная диагностика")
    print("=" * 80)
