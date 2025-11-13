using System.Reflection;
using Keycloak.AuthServices.Authentication;
using Keycloak.AuthServices.Authorization;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration
    .AddJsonFile("Configurations/appsettings.json", optional: false, reloadOnChange: true)
    .AddJsonFile($"Configurations/appsettings.{builder.Environment.EnvironmentName}.json", optional: true)
    .AddEnvironmentVariables();

builder.Services.AddControllers();
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddKeycloakWebApi(builder.Configuration, options =>
    {
        options.RequireHttpsMetadata = false;
        options.Authority = builder.Configuration["Keycloak:Authority"];
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateAudience = false,
            ValidateIssuer = false,
            NameClaimType = "preferred_username",
            RoleClaimType = builder.Configuration["Keycloak:RoleClaimType"],
        };
    });

builder.Services
    .AddAuthorization()
    .AddKeycloakAuthorization(options =>
    {
        options.EnableRolesMapping = RolesClaimTransformationSource.Realm;
        options.VerifyTokenAudience = false;
        options.RoleClaimType = "realm_access.roles"; 
    });

builder.Services.AddCors(options =>
{
    options.AddPolicy("default", policy =>
    {
        policy.WithOrigins(builder.Configuration["AllowedOrigins"]?.Split(',') ?? Array.Empty<string>())
            .AllowAnyMethod()
            .AllowAnyHeader()
            .WithExposedHeaders("Token-Expired");
    });
});

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "BionicPro",
        Version = "v1",
        Description = "API for BionicPro reports."
    });
    
    var xmlFile = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
    c.IncludeXmlComments(xmlPath);
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("default");
app.UseHttpsRedirection();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

app.Run();

