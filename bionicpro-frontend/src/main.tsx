// Импортируем библиотеку React
import React from 'react'
// Импортируем функцию для создания корневого элемента React 18
import { createRoot } from 'react-dom/client'
// Импортируем главный компонент приложения
import App from './App'
// Импортируем глобальные стили
import './index.css'
// Импортируем провайдер для интеграции Keycloak с React
import { ReactKeycloakProvider } from '@react-keycloak/web'
// Импортируем класс Keycloak из библиотеки keycloak-js
import Keycloak from 'keycloak-js'

// Создаем объект конфигурации для Keycloak
const keycloakConfig = {
  // URL сервера Keycloak
  url: 'http://localhost:8080',
  // Имя realm (области) Keycloak
  realm: 'reports-realm',
  // ID клиента в Keycloak
  clientId: 'reports-frontend'
}

// Создаем экземпляр Keycloak с заданной конфигурацией
const keycloak = new Keycloak(keycloakConfig)

// Параметры инициализации Keycloak
const initOptions = {
  // Принудительно перенаправляем пользователя на страницу входа один раз
  onLoad: 'login-required' as const,
  // Явно указываем использование PKCE (Proof Key for Code Exchange) с методом S256
  pkceMethod: 'S256' as const,
  // ВАЖНО: Отключаем проверку статуса входа через iframe
  // Это решает проблему с Content Security Policy (CSP) "frame-ancestors 'self'"
  checkLoginIframe: false,
  // Используем query параметры вместо hash fragment для избежания проблем с iss
  responseMode: 'query' as const,
}

// Получаем корневой элемент DOM
const container = document.getElementById('root')!

// Создаем корневой React элемент и рендерим приложение
createRoot(container).render(
    /* Оборачиваем приложение в провайдер Keycloak для управления аутентификацией */
    <ReactKeycloakProvider 
        authClient={keycloak}
        initOptions={initOptions}
    >
        {/* Рендерим главный компонент приложения */}
        <App />
    </ReactKeycloakProvider>
)