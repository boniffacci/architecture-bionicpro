package reporter

import (
	"context"
	"fmt"
	"log"
	"time"

	"bionicpro/internal/config"

	"github.com/jmoiron/sqlx"

	_ "github.com/ClickHouse/clickhouse-go/v2"
)

type Reporter struct {
	conn *sqlx.DB
}

type UserReport struct {
	Username            string    `db:"username" json:"username"`
	Age                 int       `db:"age" json:"age"`
	ProsthesisID        int64     `db:"prosthesis_id" json:"prosthesis_id"`
	SensorName          string    `db:"sensor_name" json:"sensor_name"`
	SensorType          string    `db:"sensor_type" json:"sensor_type"`
	InstalledAt         time.Time `db:"installed_at" json:"installed_at"`
	MetricTimestamp     time.Time `db:"metric_timestamp" json:"metric_timestamp"`
	ForceNewtons        int       `db:"force_newtons" json:"force_newtons"`
	ForceDirection      float32   `db:"force_direction" json:"force_direction"`
	AccelerationX       int       `db:"acceleration_x" json:"acceleration_x"`
	AccelerationY       int       `db:"acceleration_y" json:"acceleration_y"`
	AccelerationZ       int       `db:"acceleration_z" json:"acceleration_z"`
	TemperatureCelsius  int       `db:"temperature_celsius" json:"temperature_celsius"`
	BatteryLevelPercent int       `db:"battery_level_percent" json:"battery_level_percent"`
}

func NewReporter(config config.ReporterConfig) *Reporter {
	connStr := fmt.Sprintf(
		"clickhouse://%s:%s@%s/%s?dial_timeout=2s&read_timeout=5s",
		config.Username, config.Password, config.Address, config.Database,
	)

	db, err := sqlx.Open("clickhouse", connStr)
	if err != nil {
		log.Fatalf("failed to open clickhouse connection: %v", err)
	}

	ctx := context.Background()
	if err := db.PingContext(ctx); err != nil {
		log.Fatalf("failed to ping clickhouse: %v", err)
	}

	return &Reporter{
		conn: db,
	}
}

func (r *Reporter) Close() {
	_ = r.conn.Close()
}

func (r *Reporter) GenReport(ctx context.Context, user string) ([]UserReport, error) {
	query := `
		SELECT  username, 
		        age, 
		        prosthesis_id,
		        sensor_name,
				sensor_type,
    			installed_at,
    			metric_timestamp,
    			force_newtons,
    			force_direction,
    			acceleration_x,
    			acceleration_y,
    			acceleration_z,
    			temperature_celsius,
				battery_level_percent
		FROM reports
		WHERE username = ?
	`

	var userReports []UserReport
	err := r.conn.SelectContext(ctx, &userReports, query, user)
	if err != nil {
		return nil, err
	}

	return userReports, nil
}
