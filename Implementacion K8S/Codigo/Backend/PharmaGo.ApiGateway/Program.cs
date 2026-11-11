using System.Diagnostics.CodeAnalysis;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Exporter;
using AspNetCoreRateLimit;
using PharmaGo.ApiGateway;
using PharmaGo.ApiGateway.Middleware;
using Instrumentation;
using InstrumentationInterface;
using Yarp.ReverseProxy.Transforms;
using Microsoft.AspNetCore.HttpOverrides;

var builder = WebApplication.CreateBuilder(args);

// Leave time for endpoint propagation (preStop) and in-flight requests before SIGKILL.
builder.Services.Configure<Microsoft.Extensions.Hosting.HostOptions>(options =>
    options.ShutdownTimeout = TimeSpan.FromSeconds(20));

builder.Services.AddMemoryCache();

// X-Forwarded-For/Proto solo se aplican si la conexión viene de un proxy declarado en
// RateLimiting:TrustedProxies (IPs) o RateLimiting:TrustedNetworks (CIDR). Si ambas listas
// quedan vacías el middleware NO se registra: ForwardedHeadersMiddleware con listas vacías
// confía en cualquier origen, y kubectl port-forward entra además por 127.0.0.1 (loopback,
// confiable por defecto), lo que permitiría falsificar la IP del cliente.
var trustedProxies = builder.Configuration.GetSection("RateLimiting:TrustedProxies").Get<string[]>() ?? Array.Empty<string>();
var trustedNetworks = builder.Configuration.GetSection("RateLimiting:TrustedNetworks").Get<string[]>() ?? Array.Empty<string>();
var useForwardedHeaders = trustedProxies.Length > 0 || trustedNetworks.Length > 0;
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
    options.ForwardLimit = 1;
    options.KnownProxies.Clear();
    options.KnownNetworks.Clear();
    foreach (var proxy in trustedProxies)
    {
        options.KnownProxies.Add(System.Net.IPAddress.Parse(proxy));
    }
    foreach (var network in trustedNetworks)
    {
        var parts = network.Split('/');
        options.KnownNetworks.Add(new IPNetwork(System.Net.IPAddress.Parse(parts[0]), int.Parse(parts[1])));
    }
});

var rateLimitMode = builder.Configuration["RateLimiting:Mode"] ?? "IP";

if (rateLimitMode.Equals("IP", StringComparison.OrdinalIgnoreCase))
{
    // Rate limiting por IP (útil para endpoints públicos)
    builder.Services.Configure<IpRateLimitOptions>(builder.Configuration.GetSection("IpRateLimiting"));
    builder.Services.Configure<IpRateLimitPolicies>(builder.Configuration.GetSection("IpRateLimitPolicies"));
    builder.Services.AddInMemoryRateLimiting();
    builder.Services.AddSingleton<IRateLimitConfiguration, GatewayRateLimitConfiguration>();
}
else if (rateLimitMode.Equals("User", StringComparison.OrdinalIgnoreCase))
{
    builder.Services.Configure<UserRateLimitOptions>(builder.Configuration.GetSection(UserRateLimitOptions.SectionName));
    builder.Services.AddSingleton<FixedWindowRateLimiter>();
}

builder.Services.AddReverseProxy()
    .LoadFromConfig(builder.Configuration.GetSection("ReverseProxy"))
    .AddTransforms(transformBuilder =>
    {
        transformBuilder.AddRequestTransform(context =>
        {
            if (context.HttpContext.Items.TryGetValue(CorrelationIdMiddlewareExtensions.HttpContextItemKey, out var value)
                && value is string correlationId
                && !string.IsNullOrEmpty(correlationId))
            {
                context.ProxyRequest.Headers.Remove("X-Correlation-ID");
                context.ProxyRequest.Headers.TryAddWithoutValidation("X-Correlation-ID", correlationId);
            }
            return default;
        });
    });

builder.Services.AddSingleton<ICustomMetrics, CustomMetrics>();
builder.Services.AddHttpClient(GatewayReadinessCheck.ClientName, client => client.Timeout = TimeSpan.FromSeconds(2));
builder.Services.AddHealthChecks().AddCheck<GatewayReadinessCheck>("upstreams",
    tags: new[] { HealthEndpoints.ReadinessTag }, timeout: TimeSpan.FromSeconds(3));

builder.Services.AddOpenTelemetry()
    .WithMetrics(metricsBuilder => 
    {
        metricsBuilder
            .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("PharmaGo.ApiGateway"))
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddMeter("PharmaGo.CustomMetrics")
            .AddPrometheusExporter()
            .AddOtlpExporter(options =>
            {
                options.Endpoint = new Uri("http://otlp-collector:4317");
                options.Protocol = OtlpExportProtocol.Grpc;
            });
    });

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddCors(options =>
{
    options.AddPolicy("MyAllowedOrigins",
        policy =>
        {
            policy.SetIsOriginAllowed(_ => true)
                .AllowAnyHeader()
                .AllowAnyMethod();
        });
});

var app = builder.Build();

if (useForwardedHeaders)
{
    app.UseForwardedHeaders();
}
app.UseCors("MyAllowedOrigins");
app.UseGatewayCorrelationId();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseMetricsMiddleware();

app.UseWhen(context => !HealthEndpoints.IsHealthProbe(context.Request.Path), routes =>
{
    if (rateLimitMode.Equals("IP", StringComparison.OrdinalIgnoreCase))
    {
        routes.UseIpRateLimiting();
    }
    else if (rateLimitMode.Equals("User", StringComparison.OrdinalIgnoreCase))
    {
        routes.UseUserRateLimit();
    }
});

app.UseAuthorization();

app.MapPharmaGoHealth();
app.MapReverseProxy();
app.MapPrometheusScrapingEndpoint();

app.Run();

[ExcludeFromCodeCoverage]
public partial class Program { }

