import React from 'react'
import { ReactKeycloakProvider } from '@react-keycloak/web'
import Keycloak, { KeycloakConfig } from 'keycloak-js'
import ReportPage from './components/ReportPage'
import LoadingBlock from './components/LoadingBlock'

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || '',
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || '',
}

const keycloak = new Keycloak(keycloakConfig)

const App: React.FC = () => {
  return (
    <div className="App">
      <ReactKeycloakProvider
        authClient={keycloak}
        LoadingComponent={<LoadingBlock />}
        initOptions={{
          pkceMethod: 'S256',
        }}
      >
        <ReportPage />
      </ReactKeycloakProvider>
    </div>
  )
}

export default App
