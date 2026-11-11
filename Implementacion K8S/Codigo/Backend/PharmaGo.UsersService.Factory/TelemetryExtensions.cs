using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Configuration;
using OpenTelemetry.Metrics;
using OpenTelemetry.Trace;
using OpenTelemetry.Resources;
using OpenTelemetry.Exporter;
using System.Diagnostics;

namespace PharmaGo.UsersService.Factory
{
    public static class OpenTelemetryExtensions
    {
        public static IServiceCollection AddPharmaGoOpenTelemetryMetrics(this IServiceCollection services, string serviceName = "PharmaGo.UsersService")
        {
            services.AddOpenTelemetry()
                    .WithMetrics(metricsBuilder => { metricsBuilder
                    .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService(serviceName))
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

            return services;
        }

        /// <summary>
        /// Trazas OTLP (issue #11): entrada HTTP, salidas HTTP y SQL. El contexto W3C
        /// (traceparent) llega desde el Gateway y se propaga a los spans hijos.
        /// </summary>
        public static IServiceCollection AddPharmaGoOpenTelemetryTracing(this IServiceCollection services,
            IConfiguration configuration, string serviceName)
        {
            var endpoint = configuration["Otlp:Endpoint"] ?? "http://otlp-collector:4317";
            services.AddOpenTelemetry()
                .WithTracing(tracing => tracing
                    .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService(serviceName))
                    .AddAspNetCoreInstrumentation(options =>
                    {
                        options.Filter = context => !Instrumentation.HealthEndpoints.IsInfrastructurePath(context.Request.Path);
                        options.RecordException = true;
                    })
                    .AddHttpClientInstrumentation(options => options.RecordException = true)
                    .AddSqlClientInstrumentation(options =>
                    {
                        // Texto SQL parametrizado (sin valores). El SQL de /health/ready no se
                        // registra: su span HTTP padre está filtrado y el muestreo es ParentBased.
                        options.SetDbStatementForText = true;
                        options.RecordException = true;
                    })
                    .AddOtlpExporter(options =>
                    {
                        options.Endpoint = new Uri(endpoint);
                        options.Protocol = OtlpExportProtocol.Grpc;
                    }));

            return services;
        }
    }
}

