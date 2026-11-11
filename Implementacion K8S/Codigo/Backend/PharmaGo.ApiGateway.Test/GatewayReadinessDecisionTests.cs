using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace PharmaGo.ApiGateway.Test
{
    [TestClass]
    public class GatewayReadinessDecisionTests
    {
        [TestMethod]
        public void BothUpstreamsReady_IsHealthy()
            => Assert.AreEqual(HealthStatus.Healthy, GatewayReadinessCheck.Decide(2, false).Status);

        [TestMethod]
        public void OneUpstreamReady_IsDegraded_AndStillReady()
            => Assert.AreEqual(HealthStatus.Degraded, GatewayReadinessCheck.Decide(1, false).Status);

        [TestMethod]
        public void NoUpstreamAtStartup_IsUnhealthy_SoRolloutWaits()
            => Assert.AreEqual(HealthStatus.Unhealthy, GatewayReadinessCheck.Decide(0, false).Status);

        [TestMethod]
        public void NoUpstreamAfterHavingReachedThem_StaysReadyToFailFast()
            => Assert.AreEqual(HealthStatus.Degraded, GatewayReadinessCheck.Decide(0, true).Status);

        [TestMethod]
        public void State_RemembersFirstSuccess()
        {
            var state = new GatewayReadinessState();
            Assert.IsFalse(state.ReachedUpstream);

            state.MarkReachedUpstream();
            state.MarkReachedUpstream();

            Assert.IsTrue(state.ReachedUpstream);
        }
    }
}
