// Импортируем библиотеку React
import React from 'react';
// Импортируем провайдер для интеграции Keycloak с React
import { ReactKeycloakProvider } from '@react-keycloak/web';
// Импортируем класс Keycloak и тип конфигурации из библиотеки keycloak-js
import Keycloak, { KeycloakConfig } from 'keycloak-js';
// Импортируем компонент страницы отчетов
import ReportPage from './components/ReportPage';

// Создаем объект конфигурации для Keycloak с типизацией
const keycloakConfig: KeycloakConfig = {
  // URL сервера Keycloak из переменных окружения
  url: process.env.REACT_APP_KEYCLOAK_URL,
  // Имя realm (области) Keycloak, если не задано - используем пустую строку
  realm: process.env.REACT_APP_KEYCLOAK_REALM||"",
  // ID клиента в Keycloak, если не задано - используем пустую строку
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID||""
};

// Создаем экземпляр Keycloak с заданной конфигурацией
const keycloak = new Keycloak(keycloakConfig);

// Определяем главный компонент приложения с типом React.FC (Functional Component)
const App: React.FC = () => {
  // Возвращаем JSX разметку компонента
  return (
    // Оборачиваем приложение в провайдер Keycloak для управления аутентификацией
    <ReactKeycloakProvider authClient={keycloak}>
      {/* Контейнер приложения с классом App */}
      <div className="App">
        {/* Рендерим компонент страницы отчетов */}
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

// Экспортируем компонент App как модуль по умолчанию
export default App;