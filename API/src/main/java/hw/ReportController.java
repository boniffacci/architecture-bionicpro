package hw;

import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;

@RestController
public class ReportController {

    @GetMapping(path = "/reports", produces = MediaType.APPLICATION_OCTET_STREAM_VALUE)
    @PreAuthorize("hasAuthority(@jwtGrantedAuthoritiesPrefix + 'PROTHETIC_USER')")
    public @ResponseBody byte[] report() {
        return "report data".getBytes(StandardCharsets.UTF_8);
    }
}
