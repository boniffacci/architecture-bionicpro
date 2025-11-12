package httpserver

import (
	"github.com/labstack/echo/v4"
	"net/http"
	"strings"
)

func (s *Server) CreateStorageBucketsGroup() error {
	s.server.GET("/health", s.HealthHandler)
	s.server.GET("/reports", s.ReportsHandler)

	return nil
}

// HealthHandler
// @Summary Health route
// @Description Health route
// @ID health
// @Tags api
// @Produce  json
// @Success 200 {array} string "Ok"
// @Failure	503 {object} ServerErrorForm "Server does not available"
// @Router /health [get]
func (s *Server) HealthHandler(eCtx echo.Context) error {
	return eCtx.JSON(http.StatusOK, createStatusResponse("Ok"))
}

// ReportsHandler
// @Summary Get reports
// @Description Get reports
// @ID get-reports
// @Tags api
// @Accept  json
// @Produce json
// @Success 200 {object} ResponseForm "Ok"
// @Failure	400 {object} BadRequestForm "Bad Request message"
// @Failure	503 {object} ServerErrorForm "Server does not available"
// @Router /reports [get]
func (s *Server) ReportsHandler(eCtx echo.Context) error {
	auth := eCtx.Request().Header.Get("Authorization")
	if auth == "" || !strings.HasPrefix(strings.ToLower(auth), "bearer ") {
		return echo.NewHTTPError(http.StatusUnauthorized, "Missing or invalid Authorization header")
	}

	token := strings.TrimPrefix(auth, "Bearer ")
	claims, err := s.VerifyJWTAndRequireRole(token, "prothetic_user")
	if err != nil {
		return echo.NewHTTPError(http.StatusUnauthorized, err.Error())
	}

	user, _ := claims["preferred_username"].(string)
	if user == "" {
		user, _ = claims["sub"].(string)
	}

	ctx := eCtx.Request().Context()
	reportData, err := s.reporter.GenReport(ctx, user)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, err.Error())
	}

	// TODO: comment this code block after clickhouse implementation
	//sample := echo.Map{
	//	"generated_at": time.Now().Unix(),
	//	"user":         user,
	//	"summary": echo.Map{
	//		"sessions":          rand.Int(),
	//		"active_days":       rand.Int(),
	//		"avg_usage_minutes": rand.Int(),
	//	},
	//	"entries": []echo.Map{
	//		{"day": "Mon", "minutes": 45},
	//		{"day": "Tue", "minutes": 12},
	//		{"day": "Wed", "minutes": 56},
	//		{"day": "Thu", "minutes": 21},
	//		{"day": "Fri", "minutes": 31},
	//	},
	//}

	return eCtx.JSON(http.StatusCreated, reportData)
}
