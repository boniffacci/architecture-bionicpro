package com.bionic.backend.repository

import com.bionic.backend.repository.entity.CustomerTelemetryDaily
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import java.time.LocalDate

interface ReportRepository : JpaRepository<CustomerTelemetryDaily, String> {

    @Query(
        """
        SELECT c
        FROM CustomerTelemetryDaily c
        WHERE c.username = :username
          AND c.date >= :startDate
        ORDER BY c.date
        """
    )
    fun findAllByCustomerIdAndDateFrom(
        username: String,
        startDate: LocalDate
    ): List<CustomerTelemetryDaily>
}