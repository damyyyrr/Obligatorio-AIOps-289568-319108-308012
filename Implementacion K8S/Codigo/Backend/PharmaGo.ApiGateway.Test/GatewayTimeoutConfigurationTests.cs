using Microsoft.Extensions.Configuration;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace PharmaGo.ApiGateway.Test
{
    [TestClass]
    public class GatewayTimeoutConfigurationTests
    {
        [TestMethod]
        public void EveryCluster_HasBoundedActivityTimeout()
        {
            var settings = new ConfigurationBuilder()
                .AddJsonFile(Path.Combine(AppContext.BaseDirectory, "appsettings.json"))
                .Build();

            var clusters = settings.GetSection("ReverseProxy:Clusters").GetChildren().ToList();
            Assert.IsTrue(clusters.Count >= 2);

            foreach (var cluster in clusters)
            {
                var value = cluster["HttpRequest:ActivityTimeout"];
                Assert.IsNotNull(value, $"{cluster.Key} sin ActivityTimeout (YARP usaría 100 s)");
                Assert.AreEqual(TimeSpan.FromSeconds(10), TimeSpan.Parse(value), cluster.Key);
            }
        }
    }
}
