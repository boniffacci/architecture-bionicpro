using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using ReportApi.Extensions;
using ReportApi.Models;
using ReportApi.Repositories;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ReportApi.Controllers
{
    [ApiController]
    [Route("reports")]
    public class ReportController(ReportRepository reportRepository) : ControllerBase
    {
        private readonly ReportRepository _reportRepository = reportRepository;

        [HttpGet]
        [Authorize]
        public async Task<IEnumerable<Report>> Get()
        {
            var currentUserEmail = User.GetUserEmail();

            return await _reportRepository.GetDataAsync(currentUserEmail);
        }
    }
}
