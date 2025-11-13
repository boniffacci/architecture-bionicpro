using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace BionicPro.Controllers;

/// <summary>
/// Reports Controller
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class ReportsController : Controller
{
    /// <summary>
    /// Get reports
    /// </summary>
    /// <returns>A list of reports</returns>
    [HttpGet]
    [Authorize(Roles = "prothetic_user")]
    [ProducesResponseType(StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status403Forbidden)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public ActionResult GetReports()
    {
        try
        {
            var reports = new List<string>
            {
                "Report 1",
                "Report 2",
                "Report 3"
            };

            return Ok(reports);
        }
        catch (Exception ex)
        {
            return StatusCode(StatusCodes.Status500InternalServerError, $"An error occurred: {ex.Message}");
        }
    }
}