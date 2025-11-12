package httpserver

import (
	"bionicpro/internal/reporter"
	"context"
	"fmt"
	"log"
	"net/http"

	"bionicpro/internal/config"
	"bionicpro/internal/httpserver/mw"
	"github.com/MicahParks/keyfunc/v3"
	"github.com/golang-jwt/jwt/v5"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"

	_ "bionicpro/docs"
	echoSwagger "github.com/swaggo/echo-swagger"
)

// Server
// @title          Bionicpro service
// @version        0.0.1
// @description    Bionicpro backend service.
//
// @tag.name api
// @tag.description APIs to get status tasks. When TaskStatus may be:
type Server struct {
	config   *config.ServerConfig
	server   *echo.Echo
	reporter *reporter.Reporter
	jwks     keyfunc.Keyfunc
}

func New(config *config.ServerConfig, reporter *reporter.Reporter) *Server {
	return &Server{
		config:   config,
		reporter: reporter,
	}
}

func (s *Server) setupServer() {
	s.server = echo.New()

	s.server.Use(middleware.Recover())

	s.initLoggerMW()
	s.initLoginMW()

	_ = s.CreateStorageBucketsGroup()

	s.server.GET("/swagger/*", echoSwagger.WrapHandler)
}

func (s *Server) Start(_ context.Context) error {
	s.setupServer()
	if err := s.server.Start(s.config.Http.Address); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}

	return nil
}

func (s *Server) Shutdown(ctx context.Context) error {
	return s.server.Shutdown(ctx)
}

func (s *Server) initLoginMW() {
	s.server.Use(middleware.CORSWithConfig(middleware.CORSConfig{
		AllowOrigins: s.config.Login.AllowedCors,
		AllowMethods: []string{echo.GET, echo.OPTIONS},
		AllowHeaders: []string{echo.HeaderOrigin, echo.HeaderContentType, echo.HeaderAuthorization},
	}))

	kcConfig := s.config.Login.Keycloak
	realmURLRes := fmt.Sprintf("%s/realms/%s", kcConfig.URL, kcConfig.Realm)
	jwksURL := fmt.Sprintf("%s/protocol/openid-connect/certs", realmURLRes)

	jwks, err := keyfunc.NewDefault([]string{jwksURL})
	if err != nil {
		log.Fatalf("Failed to create JWK Set from resource at the given URL.\nError: %s", err)
	}
	s.jwks = jwks
}

func (s *Server) initLoggerMW() {
	s.server.Use(mw.InitLocalLogger(s.config.Logger))
}

func (s *Server) VerifyJWTAndRequireRole(tokenStr string, requiredRole string) (jwt.MapClaims, error) {
	token, err := jwt.Parse(tokenStr, s.jwks.Keyfunc)
	if err != nil {
		return nil, err
	}

	if !token.Valid {
		return nil, echo.NewHTTPError(http.StatusUnauthorized, "Invalid token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, echo.NewHTTPError(http.StatusUnauthorized, "Invalid claims")
	}

	// Check roles in realm_access
	if realmAccess, ok := claims["realm_access"].(map[string]interface{}); ok {
		if roles, ok := realmAccess["roles"].([]interface{}); ok {
			for _, r := range roles {
				if r.(string) == requiredRole {
					return claims, nil
				}
			}
		}
	}

	return nil, echo.NewHTTPError(http.StatusForbidden, "Missing required role: "+requiredRole)
}
