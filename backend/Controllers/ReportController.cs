using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using ReportApi.Extensions;
using ReportApi.Models;
using ReportApi.Repositories;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ReportApi.Controllers
{
    [ApiController]
    [Route("reports")]
    public class ReportController(ILogger<ReportController> logger, ReportRepository reportRepository) : ControllerBase
    {
        private readonly ILogger<ReportController> _logger = logger;
        private readonly ReportRepository _reportRepository = reportRepository;

        [HttpGet]
        [Authorize]
        public async Task<IEnumerable<Report>> Get()
        {
            var currentUserId = User.GetUserId<long>();
            _logger.LogWarning($"UserId: {currentUserId}");
            return await _reportRepository.GetDataAsync(currentUserId);
        }
    }
}
