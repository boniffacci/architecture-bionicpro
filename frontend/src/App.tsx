import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, {
  KeycloakConfig,
  KeycloakInitOptions,
} from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || '',
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || '',
};

const keycloak = new Keycloak(keycloakConfig);

// ВАЖНО: включаем PKCE (S256) для фронтенда
const keycloakInitOptions: KeycloakInitOptions = {
  pkceMethod: 'S256',
  // можно оставить check-sso, но для простоты логиним всех сразу
  onLoad: 'login-required',
  checkLoginIframe: false,
};

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={keycloakInitOptions}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;