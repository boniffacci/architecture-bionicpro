require('dotenv').config();

module.exports = {
  keycloakRealm: process.env.REACT_APP_KEYCLOAK_REALM,
  keycloakUrl: process.env.REACT_APP_KEYCLOAK_URL,
};
