package com.bionic.backend.api

import com.bionic.backend.service.ReportService
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.bind.annotation.RequestMapping


@RestController
@RequestMapping
class ReportController(
    private val reportService: ReportService
) {

    @GetMapping("/reports")
    fun getReport(): Any =
        reportService.getReport()
}