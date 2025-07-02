using Keycloak.AuthServices.Authentication;
using Keycloak.AuthServices.Authorization;
using Serilog;
using Serilog.Events;
using Serilog.Formatting.Json;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Debug()
    .MinimumLevel.Override("Microsoft", LogEventLevel.Debug)
    .MinimumLevel.Override("System", LogEventLevel.Debug)
    .MinimumLevel.Override("IdentityServer4", LogEventLevel.Debug)
    .Enrich.FromLogContext()
    .Enrich.WithAssemblyName()
    .WriteTo.Console(new JsonFormatter())
    .Enrich.WithProperty("Environment", Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT"))
    .WriteTo.Seq("http://seq:5341")
    .CreateLogger();

builder.Host.UseSerilog();

builder.Services.AddKeycloakWebApiAuthentication(builder.Configuration, x =>
{
    x.TokenValidationParameters.ValidIssuers = new List<string>
    {
        "http://localhost:8080/realms/reports-realm",
        "http://keycloak:8080/realms/reports-realm"
    };
});

builder.Services.AddAuthorization(opts =>
    {
        opts.AddPolicy("prothetic_user", builder =>
        {
            builder.RequireRealmRoles(["prothetic_user"]);
        });
    })
    .AddKeycloakAuthorization(builder.Configuration);

builder.Services.AddCors(c =>
{
    c.AddPolicy("AllowOrigin", options
        => options.AllowAnyOrigin()
            .AllowAnyMethod()
            .AllowAnyHeader()
            .Build());
});

builder.Services
    .AddControllers();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseSerilogRequestLogging();

app.UseCors("AllowOrigin");

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

app.Run();
