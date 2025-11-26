#!/usr/bin/env python3
"""Тест потока авторизации через Keycloak."""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright


async def test_auth_flow():
    """Тестирование потока авторизации."""
    print("=== Тест потока авторизации через Keycloak ===\n")
    
    async with async_playwright() as p:
        # Запускаем браузер
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Включаем логирование консоли
        page.on("console", lambda msg: print(f"  [BROWSER] {msg.text}"))
        
        try:
            # 1. Открываем главную страницу
            print("1. Открытие http://localhost:3000/")
            await page.goto("http://localhost:3000/", wait_until="networkidle", timeout=10000)
            await page.wait_for_timeout(2000)
            
            # Проверяем, произошёл ли редирект на Keycloak
            current_url = page.url
            print(f"   Текущий URL: {current_url}")
            
            if "keycloak" in current_url or "localhost:8080" in current_url:
                print("   ✓ Редирект на Keycloak произошёл")
                
                # 2. Вводим учётные данные
                print("\n2. Ввод учётных данных (admin/admin)")
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "admin")
                await page.click('input[type="submit"]')
                
                # Ждём редиректа обратно
                print("   Ожидание редиректа обратно на приложение...")
                await page.wait_for_url("http://localhost:3000/**", timeout=15000)
                
                # 3. Проверяем финальный URL
                final_url = page.url
                print(f"\n3. Финальный URL: {final_url}")
                
                if "error" in final_url:
                    print(f"   ✗ ОШИБКА: {final_url}")
                    
                    # Получаем текст страницы
                    page_text = await page.inner_text("body")
                    print(f"   Текст страницы: {page_text[:200]}")
                    
                    return False
                else:
                    print("   ✓ Редирект успешен, ошибок нет")
                    
                    # Ждём загрузки страницы
                    await page.wait_for_timeout(3000)
                    
                    # Проверяем, что пользователь авторизован
                    page_text = await page.inner_text("body")
                    
                    if "авторизованы" in page_text or "Вы авторизованы" in page_text:
                        print("   ✓ Пользователь успешно авторизован!")
                        print(f"\n=== ✓ Тест пройден успешно! ===")
                        return True
                    elif "Загрузка" in page_text:
                        print("   ⚠ Страница показывает 'Загрузка...'")
                        print(f"   Текст страницы: {page_text[:200]}")
                        return False
                    else:
                        print(f"   ? Неожиданное состояние страницы")
                        print(f"   Текст страницы: {page_text[:200]}")
                        return False
            else:
                print("   ✗ Редирект на Keycloak не произошёл")
                page_text = await page.inner_text("body")
                print(f"   Текст страницы: {page_text[:200]}")
                return False
                
        except Exception as e:
            print(f"\n✗ Ошибка: {e}")
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_auth_flow())
    sys.exit(0 if result else 1)
