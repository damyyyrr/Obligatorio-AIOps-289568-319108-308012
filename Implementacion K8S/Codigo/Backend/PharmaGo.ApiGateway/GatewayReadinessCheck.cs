using System.Net;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Yarp.ReverseProxy.Configuration;
using Instrumentation;

namespace PharmaGo.ApiGateway;

/// <summary>
/// Recuerda si este pod llegó alguna vez a un upstream listo. Singleton: el health check
/// se crea en cada evaluación.
/// </summary>
public sealed class GatewayReadinessState
{
    private int _reachedUpstream;

    public bool ReachedUpstream => Volatile.Read(ref _reachedUpstream) == 1;

    public void MarkReachedUpstream() => Interlocked.Exchange(ref _reachedUpstream, 1);
}

public sealed class GatewayReadinessCheck : IHealthCheck
{
    public const string ClientName = "readiness";
    private readonly IProxyConfigProvider _proxy;
    private readonly IHttpClientFactory _clients;
    private readonly GatewayReadinessState _state;

    public GatewayReadinessCheck(IProxyConfigProvider proxy, IHttpClientFactory clients, GatewayReadinessState state)
    {
        _proxy = proxy;
        _clients = clients;
        _state = state;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        using var client = _clients.CreateClient(ClientName);
        var clusters = _proxy.GetConfig().Clusters
            .Where(cluster => cluster.ClusterId is "users-cluster" or "pharmacy-cluster");
        var available = await Task.WhenAll(clusters.Select(cluster => IsClusterReady(
            cluster, client, cancellationToken)));

        var readyClusters = available.Count(ready => ready);
        if (readyClusters > 0)
        {
            _state.MarkReachedUpstream();
        }

        return Decide(readyClusters, _state.ReachedUpstream);
    }

    /// <summary>
    /// Sin upstreams listos el Gateway solo queda NotReady hasta alcanzarlos por primera vez
    /// (arranque y rollout). Después sigue Ready (Degraded) aunque caigan: hay un único
    /// Gateway y sacarlo del Service no deriva el tráfico, solo deja a los clientes
    /// reintentando la conexión. Ready, responde 502/503/504 acotados (issue #10).
    /// </summary>
    public static HealthCheckResult Decide(int readyClusters, bool reachedUpstreamBefore) => readyClusters switch
    {
        >= 2 => HealthCheckResult.Healthy(),
        1 => HealthCheckResult.Degraded("One upstream is ready."),
        _ when reachedUpstreamBefore => HealthCheckResult.Degraded("No upstream is ready; failing requests fast."),
        _ => HealthCheckResult.Unhealthy("No upstream is ready."),
    };

    private static async Task<bool> IsClusterReady(ClusterConfig cluster, HttpClient client, CancellationToken token)
    {
        if (cluster.Destinations is null)
        {
            return false;
        }

        var destinations = await Task.WhenAll(cluster.Destinations.Values.Select(destination =>
            IsDestinationReady(destination, client, token)));
        return destinations.Any(ready => ready);
    }

    private static async Task<bool> IsDestinationReady(DestinationConfig destination, HttpClient client,
        CancellationToken token)
    {
        try
        {
            var uri = new Uri(new Uri(destination.Address), HealthEndpoints.ReadyPath);
            using var response = await client.GetAsync(uri, HttpCompletionOption.ResponseHeadersRead, token);
            return response.StatusCode == HttpStatusCode.OK;
        }
        catch (HttpRequestException)
        {
            return false;
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        {
            return false;
        }
    }
}
