using System;

namespace ReportApi.Models
{
    public class Report
    {
        public Guid id { get; set; }
        public int user_id { get; set; }
        public string user_name { get; set; }
        public string user_email { get; set; }
        public int user_age { get; set; }
        public string user_gender { get; set; }
        public string user_country { get; set; }
        public string user_address { get; set; }
        public string user_phone { get; set; }
        public string prosthesis_type { get; set; }
        public string muscle_group { get; set; }
        public int signal_frequency { get; set; }
        public int signal_duration { get; set; }
        public decimal signal_amplitude { get; set; }
        public DateTimeOffset signal_time { get; set; }
    }
}
