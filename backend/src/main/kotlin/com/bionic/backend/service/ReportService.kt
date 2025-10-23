package com.bionic.backend.service

import com.bionic.backend.repository.ReportRepository
import com.bionic.backend.repository.entity.CustomerTelemetryDaily
import org.springframework.security.core.context.SecurityContextHolder
import org.springframework.stereotype.Service
import java.time.LocalDate

@Service
class ReportService(
    private val reportRepository: ReportRepository
) {
    fun getReport(): List<CustomerTelemetryDaily> {

        return reportRepository.findAllByCustomerIdAndDateFrom(
            username = getUserName(),
            startDate = LocalDate.now().minusDays(30)
        )
    }

    private fun getUserName(): String = SecurityContextHolder.getContext().authentication.name
}