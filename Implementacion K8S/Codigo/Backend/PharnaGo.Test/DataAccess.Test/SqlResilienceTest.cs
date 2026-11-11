using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using PharmaGo.DataAccess;

namespace PharmaGo.Test.DataAccess.Test
{
    [TestClass]
    public class SqlResilienceTest
    {
        private const string Base = "Server=pharmago-db;Database=PharmaDb;User Id=sa;Password=\"x\"";

        private static IConfiguration Config(params (string Key, string Value)[] values)
            => new ConfigurationBuilder()
                .AddInMemoryCollection(values.Select(v => new KeyValuePair<string, string>(v.Key, v.Value)))
                .Build();

        [TestMethod]
        public void ConnectionString_GetsDefaultConnectTimeout_AndNeverBlockingPool()
        {
            var result = new SqlConnectionStringBuilder(
                SqlResilience.ConnectionString(Config(("ConnectionStrings:DefaultConnection", Base))));

            Assert.AreEqual(5, result.ConnectTimeout);
            Assert.AreEqual(PoolBlockingPeriod.NeverBlock, result.PoolBlockingPeriod);
            Assert.AreEqual("pharmago-db", result.DataSource);
            Assert.AreEqual("PharmaDb", result.InitialCatalog);
            Assert.AreEqual("x", result.Password);
        }

        [TestMethod]
        public void Timeouts_CanBeOverriddenByConfiguration()
        {
            var config = Config(
                ("ConnectionStrings:DefaultConnection", Base),
                ("Database:ConnectTimeoutSeconds", "3"),
                ("Database:CommandTimeoutSeconds", "6"));

            Assert.AreEqual(3, new SqlConnectionStringBuilder(SqlResilience.ConnectionString(config)).ConnectTimeout);
            Assert.AreEqual(6, SqlResilience.CommandTimeoutSeconds(config));
        }

        [TestMethod]
        public void InvalidValues_FallBackToDefaults()
        {
            var config = Config(("Database:ConnectTimeoutSeconds", "0"), ("Database:CommandTimeoutSeconds", "abc"));

            Assert.AreEqual(SqlResilience.DefaultConnectTimeoutSeconds, SqlResilience.ConnectTimeoutSeconds(config));
            Assert.AreEqual(SqlResilience.DefaultCommandTimeoutSeconds, SqlResilience.CommandTimeoutSeconds(config));
        }

        [TestMethod]
        public void TimeoutOrder_StaysBelowGatewayTimeout()
        {
            const int gatewayActivityTimeoutSeconds = 10;

            Assert.IsTrue(SqlResilience.DefaultConnectTimeoutSeconds < gatewayActivityTimeoutSeconds);
            Assert.IsTrue(SqlResilience.DefaultCommandTimeoutSeconds < gatewayActivityTimeoutSeconds);
        }

        [TestMethod]
        public void EmptyConnectionString_IsLeftUntouched()
        {
            Assert.AreEqual(string.Empty, SqlResilience.ApplyConnectionLimits(string.Empty, 5));
        }
    }
}
