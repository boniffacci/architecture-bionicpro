from keycloak import KeycloakOpenID

URL_AUTH = (
    "{authorization-endpoint}?client_id={client-id}&response_type=code&redirect_uri={redirect-uri}"
    "&scope={scope}&state={state}&nonce={nonce}&code_challenge={pkce_challenge}&code_challenge_method=S256"
)


class PKCEKeycloakOpenID(KeycloakOpenID):
    async def a_pkce_auth_url(self, redirect_uri: str, state: str, pkce_challenge: str):
        params_path = {
            "authorization-endpoint": "http://localhost:8080/realms/reports-realm/protocol/openid-connect/auth",
            "client-id": self.client_id,
            "redirect-uri": redirect_uri,
            "scope": "email",
            "state": state,
            "nonce": "nonce",
            "pkce_challenge": pkce_challenge,
        }
        return URL_AUTH.format(**params_path)
