package main

import (
	"bytes"
	"encoding/csv"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

func (app *App) GetReports(c *gin.Context) {
	// Get user ID from context (set by auth middleware)
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "User ID not found in token"})
		return
	}

	userIDStr, ok := userID.(string)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Invalid user ID format"})
		return
	}

	// Query ClickHouse
	reports, err := app.ClickHouse.GetUserReports(c.Request.Context(), userIDStr)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Failed to fetch reports: %v", err)})
		return
	}

	// Generate CSV
	csvData, err := generateCSV(reports)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to generate CSV"})
		return
	}

	// Set headers for file download
	filename := fmt.Sprintf("user_reports_%s_%s.csv", userIDStr, time.Now().Format("2006-01-02"))
	c.Header("Content-Type", "text/csv")
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=%s", filename))
	c.Header("Content-Length", strconv.Itoa(len(csvData)))

	c.Data(http.StatusOK, "text/csv", csvData)
}

func generateCSV(reports []ReportRecord) ([]byte, error) {
	// Create a bytes.Buffer to write CSV data
	var buffer bytes.Buffer

	// Create CSV writer
	writer := csv.NewWriter(&buffer)

	// Write header
	header := []string{"Prosthesis Type", "Muscle Group", "Signals", "Avg Amplitude", "P95 Amplitude", "Avg Frequency", "Avg Duration", "First Signal", "Last Signal"}
	if err := writer.Write(header); err != nil {
		return nil, fmt.Errorf("failed to write CSV header: %w", err)
	}

	// Write data rows
	for _, record := range reports {
		row := []string{
			record.ProsthesisType,
			record.MuscleGroup,
			strconv.FormatInt(record.Signals, 10),
			strconv.FormatFloat(record.AvgAmplitude, 'f', 2, 64),
			strconv.FormatFloat(record.P95Amplitude, 'f', 2, 64),
			strconv.FormatFloat(record.AvgFrequency, 'f', 2, 64),
			strconv.FormatFloat(record.AvgDuration, 'f', 2, 64),
			record.FirstSignal.Format("2006-01-02 15:04:05"),
			record.LastSignal.Format("2006-01-02 15:04:05"),
		}
		if err := writer.Write(row); err != nil {
			return nil, fmt.Errorf("failed to write CSV row: %w", err)
		}
	}

	writer.Flush()
	if err := writer.Error(); err != nil {
		return nil, fmt.Errorf("failed to flush CSV writer: %w", err)
	}

	return buffer.Bytes(), nil
}
