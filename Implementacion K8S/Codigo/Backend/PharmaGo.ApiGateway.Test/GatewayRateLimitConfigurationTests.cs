using AspNetCoreRateLimit;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using PharmaGo.ApiGateway.Middleware;

namespace PharmaGo.ApiGateway.Test
{
    [TestClass]
    public class GatewayRateLimitConfigurationTests
    {
        [TestMethod]
        public void CountersAreGroupedByRule_NotByConcretePath()
        {
            var configuration = new GatewayRateLimitConfiguration(
                Options.Create(new IpRateLimitOptions()),
                Options.Create(new ClientRateLimitOptions()));

            Assert.IsInstanceOfType(configuration.EndpointCounterKeyBuilder, typeof(EndpointCounterKeyBuilder));
        }

        [TestMethod]
        public void OnlyConnectionIpIsUsed_EvenWhenRealIpHeaderHasLibraryDefault()
        {
            var configuration = new GatewayRateLimitConfiguration(
                Options.Create(new IpRateLimitOptions { RealIpHeader = "X-Real-IP" }),
                Options.Create(new ClientRateLimitOptions()));

            configuration.RegisterResolvers();

            Assert.AreEqual(1, configuration.IpResolvers.Count);
            Assert.IsInstanceOfType(configuration.IpResolvers[0], typeof(IpConnectionResolveContributor));
        }

        [TestMethod]
        public void AppSettings_DoNotTrustClientSuppliedIpHeaders()
        {
            var settings = new ConfigurationBuilder()
                .AddJsonFile(Path.Combine(AppContext.BaseDirectory, "appsettings.json"))
                .Build();

            Assert.IsTrue(string.IsNullOrEmpty(settings["IpRateLimiting:RealIpHeader"]));
            Assert.IsFalse(settings.GetSection("RateLimiting:TrustedProxies").GetChildren().Any());
            Assert.IsFalse(settings.GetSection("RateLimiting:TrustedNetworks").GetChildren().Any());
        }
    }
}
