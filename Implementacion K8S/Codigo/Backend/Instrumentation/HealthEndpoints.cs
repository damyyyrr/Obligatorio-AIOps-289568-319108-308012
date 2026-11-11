using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;

namespace Instrumentation;

public static class HealthEndpoints
{
    public const string ReadinessTag = "ready";
    public const string ReadyPath = "/health/ready";
    private const string LivePath = "/health/live";
    private const string LegacyPath = "/health";

    public static void MapPharmaGoHealth(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapHealthChecks(LivePath, new HealthCheckOptions { Predicate = _ => false });

        var readiness = new HealthCheckOptions { Predicate = check => check.Tags.Contains(ReadinessTag) };
        endpoints.MapHealthChecks(ReadyPath, readiness);
        endpoints.MapHealthChecks(LegacyPath, readiness);
    }

    public static bool IsHealthProbe(PathString path)
        => path == LivePath || path == ReadyPath || path == LegacyPath;

    /// <summary>Probes y scraping: se excluyen de las trazas para no generar ruido (issue #11).</summary>
    public static bool IsInfrastructurePath(PathString path)
        => IsHealthProbe(path) || path.StartsWithSegments("/metrics");
}
