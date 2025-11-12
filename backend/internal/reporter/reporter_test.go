package reporter

import (
	"context"
	"testing"

	"bionicpro/internal/config"

	"github.com/stretchr/testify/assert"
)

const TestingConfigFilePath = "../../configs/testing.toml"

func TestReport(t *testing.T) {
	servConfig, servErr := config.FromFile(TestingConfigFilePath)
	assert.NoError(t, servErr)

	t.Run("Generate report", func(t *testing.T) {
		rep := NewReporter(servConfig.Reporter)
		defer rep.Close()

		report, err := rep.GenReport(context.Background(), "prothetic1")
		assert.NoError(t, err)

		assert.NotEmpty(t, report)
		assert.Equal(t, 2, len(report))
	})
}
