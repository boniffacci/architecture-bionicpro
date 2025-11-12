package mw

import (
	"fmt"
	"strings"

	"bionicpro/internal/config"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func InitLocalLogger(config config.LoggerConfig) echo.MiddlewareFunc {
	logConfig := middleware.LoggerConfig{
		Skipper: func(c echo.Context) bool {
			uri := c.Path()
			return strings.Contains(uri, "swagger")
		},
		CustomTimeFormat: "2006/01/02 15:04:05",
		Format: fmt.Sprintf(
			"%s %s http-response={%s %s %s %s %s}\n",
			"${time_custom}",
			config.Level,
			"method=${method}",
			"uri=${path}",
			"latency=${latency}",
			"status=${status}",
			"error=\"${error}\"",
		),
	}

	return middleware.LoggerWithConfig(logConfig)
}
