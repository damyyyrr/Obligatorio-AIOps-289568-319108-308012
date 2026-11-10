using PharmaGo.UsersService.Factory;
using PharmaGo.UsersService.Filters;
using PharmaGo.UsersService;
using System.Diagnostics.CodeAnalysis;
using Instrumentation;
using PharmaGo.DataAccess;

if (args.Length > 0 && args[0] == "--migrate")
{
    Environment.ExitCode = DatabaseMigration.Run(args.Skip(1).ToArray());
    return;
}

var builder = WebApplication.CreateBuilder(args);

builder.Logging.SuppressEfAndSqlClientLogs();

builder.Services.AddHttpContextAccessor();
builder.Services.RegisterBusinessLogicServices(builder.Configuration);
builder.Services.RegisterDataAccessServices(builder.Configuration);
builder.Services.AddControllers(options => options.Filters.Add(typeof(ExceptionFilter)));

builder.Services.AddControllers();

builder.Services.AddHealthChecks().AddTypeActivatedCheck<SqlReadinessCheck>("sql",
    failureStatus: null, tags: new[] { HealthEndpoints.ReadinessTag }, timeout: TimeSpan.FromSeconds(2),
    args: new object[] { "SELECT TOP (1) Id FROM dbo.Users;" });

builder.Services.AddPharmaGoOpenTelemetryMetrics("PharmaGo.UsersService");

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

