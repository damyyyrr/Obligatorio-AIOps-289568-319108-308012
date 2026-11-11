using PharmaGo.PharmacyService.Factory;
using PharmaGo.PharmacyService.Filters;
using System.Diagnostics.CodeAnalysis;
using Instrumentation;
using PharmaGo.DataAccess;

var builder = WebApplication.CreateBuilder(args);

// Leave time for endpoint propagation (preStop) and in-flight requests before SIGKILL.
builder.Services.Configure<Microsoft.Extensions.Hosting.HostOptions>(options =>
    options.ShutdownTimeout = TimeSpan.FromSeconds(20));

builder.Logging.SuppressEfAndSqlClientLogs();

builder.Services.AddHttpContextAccessor();
builder.Services.RegisterBusinessLogicServices(builder.Configuration);
builder.Services.RegisterDataAccessServices(builder.Configuration);
builder.Services.AddControllers(options => options.Filters.Add(typeof(ExceptionFilter)));

builder.Services.AddControllers();

builder.Services.AddHealthChecks().AddTypeActivatedCheck<SqlReadinessCheck>("sql",
    failureStatus: null, tags: new[] { HealthEndpoints.ReadinessTag }, timeout: TimeSpan.FromSeconds(2),
    args: new object[] { "SELECT TOP (1) Id FROM dbo.Drugs;" });

builder.Services.AddPharmaGoOpenTelemetryMetrics("PharmaGo.PharmacyService");
builder.Services.AddPharmaGoOpenTelemetryTracing(builder.Configuration, "PharmaGo.PharmacyService");

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddCors(options =>
{
    options.AddPolicy("MyAllowedOrigins",
        policy =>
        {
            policy.WithOrigins("*")
                .AllowAnyHeader()
                .AllowAnyMethod();
        });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseCors("MyAllowedOrigins");
app.UseServiceCorrelationScope();

app.UseAuthorization();

app.MapPharmaGoHealth();
app.UseMetricsMiddleware();

app.MapControllers();
app.MapPrometheusScrapingEndpoint();

app.Run();

[ExcludeFromCodeCoverage]
public partial class Program { }

