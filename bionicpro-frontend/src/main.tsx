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
  // Проверяем SSO при загрузке (не перенаправляем автоматически на страницу входа)
  onLoad: 'check-sso' as const,
  // Явно указываем использование PKCE (Proof Key for Code Exchange) с методом S256
  pkceMethod: 'S256' as const,
  // Включаем silent check-sso для проверки авторизации без редиректа
  silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html'
}

// Получаем корневой элемент DOM
const container = document.getElementById('root')!

// Создаем корневой React элемент и рендерим приложение
createRoot(container).render(
    <React.StrictMode>
        {/* Оборачиваем приложение в провайдер Keycloak для управления аутентификацией */}
        <ReactKeycloakProvider 
            authClient={keycloak}
            initOptions={initOptions}
        >
            {/* Рендерим главный компонент приложения */}
            <App />
        </ReactKeycloakProvider>
    </React.StrictMode>
)