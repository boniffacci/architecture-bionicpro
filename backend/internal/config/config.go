package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/joho/godotenv"
	"github.com/spf13/viper"
)

type Config struct {
	Server   ServerConfig   `mapstructure:"server"`
	Reporter ReporterConfig `mapstructure:"reporter"`
}

type ServerConfig struct {
	Http   HttpServerConfig `mapstructure:"http"`
	Logger LoggerConfig     `mapstructure:"logger"`
	Login  LoginConfig      `mapstructure:"login"`
}

type HttpServerConfig struct {
	Address string `mapstructure:"address"`
}

type LoggerConfig struct {
	Level string `mapstructure:"level"`
}

type LoginConfig struct {
	AllowedCors []string       `mapstructure:"cors"`
	Keycloak    KeycloakConfig `mapstructure:"keycloak"`
	JwtCache    JwtCacheConfig `mapstructure:"jwt_cache"`
}

type JwtCacheConfig struct {
	Expired time.Duration `mapstructure:"expired"`
}

type KeycloakConfig struct {
	URL   string `mapstructure:"url"`
	Realm string `mapstructure:"realm"`
}

type ReporterConfig struct {
	Address  string `mapstructure:"address"`
	Database string `mapstructure:"database"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
}

func FromFile(filePath string) (*Config, error) {
	_ = godotenv.Load()

	config := &Config{}

	viperInstance := viper.New()
	viperInstance.SetConfigFile(filePath)
	viperInstance.SetConfigType("toml")

	viperInstance.AutomaticEnv()
	viperInstance.SetEnvPrefix("bionicpro")
	viperInstance.SetEnvKeyReplacer(strings.NewReplacer(".", "__"))

	// Server config
	bindErr := viperInstance.BindEnv("server.http.address", "BIONICPRO__SERVER__HTTP__ADDRESS")
	if bindErr != nil {
		return nil, fmt.Errorf("failed to bine env varialbe: %w", bindErr)
	}

	bindErr = viperInstance.BindEnv("server.logger.level", "BIONICPRO__SERVER__LOGGER__LEVEL")
	if bindErr != nil {
		return nil, fmt.Errorf("failed to bine env varialbe: %w", bindErr)
	}

	bindErr = viperInstance.BindEnv("server.login.cors", "BIONICPRO__SERVER__LOGIN__CORS")
	if bindErr != nil {
		return nil, fmt.Errorf("failed to bine env varialbe: %w", bindErr)
	}
	bindErr = viperInstance.BindEnv("server.login.keycloak.url", "BIONICPRO__SERVER__LOGIN__KEYCLOAK__URL")
	if bindErr != nil {
		return nil, fmt.Errorf("failed to bine env varialbe: %w", bindErr)
	}
	bindErr = viperInstance.BindEnv("server.login.keycloak.realm", "BIONICPRO__SERVER__LOGIN__KEYCLOAK__REALM")
	if bindErr != nil {
		return nil, fmt.Errorf("failed to bine env varialbe: %w", bindErr)
	}

	bindErr = viperInstance.BindEnv("server.login.jwt_cache.expired", "BIONICPRO__SERVER__LOGIN__JWT_CACHE__EXPIRED")
	if bindErr != nil {
		return nil, fmt.Errorf("failed to bine env varialbe: %w", bindErr)
	}

	if err := viperInstance.ReadInConfig(); err != nil {
		confErr := fmt.Errorf("failed while reading config file %s: %w", filePath, err)
		return config, confErr
	}

	if err := viperInstance.Unmarshal(config); err != nil {
		confErr := fmt.Errorf("failed while unmarshaling config file %s: %w", filePath, err)
		return config, confErr
	}

	return config, nil
}
