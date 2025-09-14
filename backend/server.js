const express = require("express");
const { Pool } = require("pg");
const cors = require("cors");
const helmet = require("helmet");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Database connection
const pool = new Pool({
  user: process.env.DB_USER || "reports_user",
  host: process.env.DB_HOST || "localhost",
  database: process.env.DB_NAME || "reports_db",
  password: process.env.DB_PASSWORD || "reports_password",
  port: process.env.DB_PORT || 5434,
});

// Test database connection
pool.on("connect", () => {
  console.log("Connected to PostgreSQL database");
});

pool.on("error", (err) => {
  console.error("Database connection error:", err);
});

// Routes

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({ status: "OK", timestamp: new Date().toISOString() });
});

// Get all reports
app.get("/reports", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        report_id,
        customer_id,
        customer_name,
        customer_email,
        prosthesis_type,
        report_date,
        total_sessions,
        avg_muscle_signal,
        max_muscle_signal,
        min_muscle_signal,
        avg_position,
        total_activities,
        most_common_activity,
        created_at
      FROM reports_data_mart
      ORDER BY created_at DESC
    `);

    res.json({
      success: true,
      data: result.rows,
      count: result.rows.length,
    });
  } catch (error) {
    console.error("Error fetching reports:", error);
    res.status(500).json({
      success: false,
      error: "Internal server error",
    });
  }
});

// Get report by customer ID
app.get("/reports/customer/:customerId", async (req, res) => {
  try {
    const { customerId } = req.params;

    const result = await pool.query(
      `
      SELECT 
        report_id,
        customer_id,
        customer_name,
        customer_email,
        prosthesis_type,
        report_date,
        total_sessions,
        avg_muscle_signal,
        max_muscle_signal,
        min_muscle_signal,
        avg_position,
        total_activities,
        most_common_activity,
        created_at
      FROM reports_data_mart
      WHERE customer_id = $1
      ORDER BY created_at DESC
    `,
      [customerId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: "Report not found for this customer",
      });
    }

    res.json({
      success: true,
      data: result.rows[0],
    });
  } catch (error) {
    console.error("Error fetching customer report:", error);
    res.status(500).json({
      success: false,
      error: "Internal server error",
    });
  }
});

// Get detailed telemetry data for a customer
app.get("/reports/customer/:customerId/telemetry", async (req, res) => {
  try {
    const { customerId } = req.params;
    const { limit = 100, offset = 0 } = req.query;

    const result = await pool.query(
      `
      SELECT 
        t.telemetry_id,
        t.timestamp,
        t.device_id,
        t.sensor_type,
        t.value,
        t.unit,
        t.activity_type,
        c.name as customer_name,
        c.prosthesis_type
      FROM telemetry_data t
      JOIN crm_customers c ON t.customer_id = c.customer_id
      WHERE t.customer_id = $1
      ORDER BY t.timestamp DESC
      LIMIT $2 OFFSET $3
    `,
      [customerId, limit, offset]
    );

    res.json({
      success: true,
      data: result.rows,
      count: result.rows.length,
      pagination: {
        limit: parseInt(limit),
        offset: parseInt(offset),
      },
    });
  } catch (error) {
    console.error("Error fetching telemetry data:", error);
    res.status(500).json({
      success: false,
      error: "Internal server error",
    });
  }
});

// Get customer statistics
app.get("/reports/customer/:customerId/stats", async (req, res) => {
  try {
    const { customerId } = req.params;

    const result = await pool.query(
      `
      SELECT 
        c.customer_id,
        c.name,
        c.email,
        c.prosthesis_type,
        COUNT(DISTINCT DATE(t.timestamp)) as total_days,
        COUNT(t.telemetry_id) as total_measurements,
        AVG(CASE WHEN t.sensor_type = 'muscle_signal' THEN t.value END) as avg_muscle_signal,
        MAX(CASE WHEN t.sensor_type = 'muscle_signal' THEN t.value END) as max_muscle_signal,
        MIN(CASE WHEN t.sensor_type = 'muscle_signal' THEN t.value END) as min_muscle_signal,
        AVG(CASE WHEN t.sensor_type = 'position' THEN t.value END) as avg_position,
        COUNT(DISTINCT t.activity_type) as unique_activities,
        MODE() WITHIN GROUP (ORDER BY t.activity_type) as most_common_activity
      FROM crm_customers c
      LEFT JOIN telemetry_data t ON c.customer_id = t.customer_id
      WHERE c.customer_id = $1
      GROUP BY c.customer_id, c.name, c.email, c.prosthesis_type
    `,
      [customerId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: "Customer not found",
      });
    }

    res.json({
      success: true,
      data: result.rows[0],
    });
  } catch (error) {
    console.error("Error fetching customer stats:", error);
    res.status(500).json({
      success: false,
      error: "Internal server error",
    });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({
    success: false,
    error: "Internal server error",
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: "Endpoint not found",
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Reports API server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Reports endpoint: http://localhost:${PORT}/reports`);
});
