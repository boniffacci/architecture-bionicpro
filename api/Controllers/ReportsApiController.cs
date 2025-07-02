using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Ya_swa_8_RasskazovR_Api.DTO;

namespace Ya_swa_8_RasskazovR_Api.Controllers;

[ApiController]
[Authorize(Policy = "prothetic_user")]
[Route("reports")]
public class ReportsApiController(ILogger<ReportsApiController> logger) : ControllerBase
{
    public ActionResult<ReportDto> GetReports()
    {
        var random = new Random();

        var reportDto = new ReportDto
        {
            Id = Guid.NewGuid(),
            Name = "Report #" + random.Next(1, 1000),
            Data = new List<int>
            {
                random.Next(1, 1000),
                random.Next(1, 1000),
                random.Next(1, 1000),
                random.Next(1, 1000),
                random.Next(1, 1000),
                random.Next(1, 1000)
            }
        };

        return Ok(reportDto);
    }
}