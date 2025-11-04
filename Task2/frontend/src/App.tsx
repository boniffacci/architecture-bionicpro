import React, { useState } from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const baseUrl = `${window.location.origin}${window.location.pathname}`.replace(/\/$/, '');

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL || 'http://localhost:8080',
  realm: process.env.REACT_APP_KEYCLOAK_REALM || 'reports-realm',
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || 'reports-frontend',
};

const keycloak = new Keycloak(keycloakConfig);

const initOptions = {
  onLoad: 'login-required',
  flow: 'standard',
  pkceMethod: 'S256',
  responseMode: 'query',
  redirectUri: baseUrl,
  checkLoginIframe: true, // Включите для проверки сессии
};

const App: React.FC = () => {
  const [error, setError] = useState<unknown>(null);

  const onKeycloakEvent = (event: string, error: unknown) => {
    console.log('Keycloak event:', event, error);
    if (error) {
      setError(error);
    }
    if (event === 'onAuthSuccess') {
      // Очистка URL после успешной авторизации
      const url = new URL(window.location.href);
      if (url.searchParams.has('code') || url.searchParams.has('state') || url.searchParams.has('session_state')) {
        window.history.replaceState(null, '', baseUrl);
      }
    }
  };

  if (error) {
    return <div>Ошибка инициализации аутентификации: {String(error)}</div>;
  }

  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={initOptions}
      onEvent={onKeycloakEvent}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;