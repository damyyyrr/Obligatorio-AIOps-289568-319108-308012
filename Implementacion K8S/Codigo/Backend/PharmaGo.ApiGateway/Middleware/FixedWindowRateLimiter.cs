namespace PharmaGo.ApiGateway.Middleware
{
    /// <summary>
    /// Regla de ventana fija: como máximo <see cref="Limit"/> solicitudes por <see cref="Window"/>.
    /// </summary>
    public sealed record RateLimitRule(string Key, int Limit, TimeSpan Window);

    public sealed record RateLimitDecision(bool Allowed, string Reason, TimeSpan RetryAfter)
    {
        public static readonly RateLimitDecision Accept = new(true, string.Empty, TimeSpan.Zero);
    }

    /// <summary>
    /// Contador de ventana fija en memoria del proceso.
    /// La comprobación y el incremento de todas las reglas de una solicitud son atómicos
    /// (un único lock), de modo que ráfagas concurrentes no superan el límite.
    /// El estado es LOCAL a cada réplica del Gateway: con N pods el máximo efectivo
    /// por cliente es N × límite si el balanceo reparte sus solicitudes.
    /// </summary>
    public sealed class FixedWindowRateLimiter
    {
        private readonly object _sync = new();
        private readonly Dictionary<string, Window> _windows = new();
        private DateTimeOffset _nextSweep = DateTimeOffset.MinValue;

        private sealed class Window
        {
            public long Index;
            public int Count;
            public DateTimeOffset ExpiresAt;
        }

        public RateLimitDecision TryAcquire(IReadOnlyList<RateLimitRule> rules, DateTimeOffset now)
        {
            lock (_sync)
            {
                SweepExpired(now);

                foreach (var rule in rules)
                {
                    var window = GetWindow(rule, now);
                    if (window.Count >= rule.Limit)
                    {
                        return new RateLimitDecision(
                            false,
                            $"Exceeded {rule.Limit} requests per {Describe(rule.Window)}",
                            window.ExpiresAt - now);
                    }
                }

                // Solo se cuenta la solicitud si todas las reglas la aceptan.
                foreach (var rule in rules)
                {
                    GetWindow(rule, now).Count++;
                }

                return RateLimitDecision.Accept;
            }
        }

        public int TrackedWindows
        {
            get { lock (_sync) { return _windows.Count; } }
        }

        private Window GetWindow(RateLimitRule rule, DateTimeOffset now)
        {
            var index = now.UtcTicks / rule.Window.Ticks;
            var storageKey = $"{rule.Key}|{rule.Window.Ticks}";

            if (!_windows.TryGetValue(storageKey, out var window) || window.Index != index)
            {
                window = new Window
                {
                    Index = index,
                    Count = 0,
                    ExpiresAt = new DateTimeOffset((index + 1) * rule.Window.Ticks, TimeSpan.Zero),
                };
                _windows[storageKey] = window;
            }

            return window;
        }

        private void SweepExpired(DateTimeOffset now)
        {
            if (now < _nextSweep)
            {
                return;
            }

            foreach (var key in _windows.Where(pair => pair.Value.ExpiresAt <= now).Select(pair => pair.Key).ToList())
            {
                _windows.Remove(key);
            }

            _nextSweep = now.AddMinutes(1);
        }

        private static string Describe(TimeSpan window) => window switch
        {
            { TotalHours: 1 } => "hour",
            { TotalMinutes: 1 } => "minute",
            _ => $"{window.TotalSeconds:0} seconds",
        };
    }
}
