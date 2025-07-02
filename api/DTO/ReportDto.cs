namespace Ya_swa_8_RasskazovR_Api.DTO;

public record ReportDto
{
    public Guid Id { get; set; }
    public string Name { get; set; }
    public List<int> Data { get; set; }
}