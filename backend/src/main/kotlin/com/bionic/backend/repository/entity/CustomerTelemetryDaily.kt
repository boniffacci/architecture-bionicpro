package com.bionic.backend.repository.entity


import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.Id
import jakarta.persistence.Table
import java.math.BigDecimal
import java.time.LocalDate
import java.time.LocalDateTime

@Entity
@Table(name = "customer_telemetry_daily", schema = "mart")
data class CustomerTelemetryDaily(
    @Id
    @Column(name = "username", nullable = false)
    val username: String,

    @Column(name = "date", nullable = false)
    val date: LocalDate,

    @Column(nullable = false)
    val accuracy: Long = 0,

    @Column(nullable = false)
    val movements: Long = 0,

    @Column(nullable = false)
    val intensity: BigDecimal = BigDecimal.ZERO,

    @Column(name = "last_event")
    val lastEvent: LocalDateTime? = null
)
