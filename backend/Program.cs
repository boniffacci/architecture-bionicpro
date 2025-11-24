using ClickHouse.Client.ADO;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.Tokens;
using ReportApi.Repositories;
using static System.Net.WebRequestMethods;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddJwtBearer(options =>
        {
            options.Authority = builder.Configuration["Authentication:Keycloak:ServerAddress"] + "/realms/" + builder.Configuration["Authentication:Keycloak:Realm"];
            options.Audience = builder.Configuration["Authentication:Keycloak:Audience"];
            options.RequireHttpsMetadata = false; // Set to true in production
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidIssuer = builder.Configuration["Authentication:Keycloak:Issuer"],
                ValidateAudience = false, // TODO: setup audience
                ValidateIssuer = true,
                ValidateLifetime = true
            };
        });


builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll",
        builder =>
        {
            builder.AllowAnyOrigin()
                   .AllowAnyHeader()
                   .AllowAnyMethod();
        });
});

builder.Services.AddTransient(provider =>
{
    var connectionString = builder.Configuration.GetConnectionString("ClickHouseConnection");
    return new ClickHouseConnection(connectionString);
});

builder.Services.AddScoped<ReportRepository>();

builder.Services.AddAuthorization();

var app = builder.Build();

// Configure the HTTP request pipeline.

app.UseAuthentication();
app.UseAuthorization();
app.UseCors("AllowAll");
app.MapControllers();

app.Run();
