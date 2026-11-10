using System.Net;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Yarp.ReverseProxy.Configuration;
using Instrumentation;

namespace PharmaGo.ApiGateway;

public sealed class GatewayReadinessCheck : IHealthCheck
{
    public const string ClientName = "readiness";
    private readonly IProxyConfigProvider _proxy;
    private readonly IHttpClientFactory _clients;

    public GatewayReadinessCheck(IProxyConfigProvider proxy, IHttpClientFactory clients)
    {
        _proxy = proxy;
        _clients = clients;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        using var client = _clients.CreateClient(ClientName);
        var clusters = _proxy.GetConfig().Clusters
            .Where(cluster => cluster.ClusterId is "users-cluster" or "pharmacy-cluster");
        var available = await Task.WhenAll(clusters.Select(cluster => IsClusterReady(
            cluster, client, cancellationToken)));

        return available.Count(ready => ready) switch
        {
            2 => HealthCheckResult.Healthy(),
            1 => HealthCheckResult.Degraded("One upstream is ready."),
            _ => HealthCheckResult.Unhealthy("No upstream is ready."),
        };
    }

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
