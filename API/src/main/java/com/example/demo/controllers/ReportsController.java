package com.example.demo.controllers;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.*;

@RestController
public class ReportsController {

    @GetMapping(
            value = "/reports")
    @PreAuthorize("hasAuthority('prothetic_user')")
    public ResponseEntity<FileSystemResource>  getReports(HttpServletResponse response) throws IOException {

        File file = new File(this.getClass().getClassLoader().getResource("report.txt").getFile());
        long fileLength = file.length();

        HttpHeaders respHeaders = new HttpHeaders();
        respHeaders.setContentType(MediaType.APPLICATION_JSON);
        respHeaders.setContentLength(fileLength);
        respHeaders.set(HttpHeaders.CONTENT_DISPOSITION,
                "attachment; filename=report.txt");

        return new ResponseEntity<>(
                new FileSystemResource(file), respHeaders, HttpStatus.OK
        );

    }

}
