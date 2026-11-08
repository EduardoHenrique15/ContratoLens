from contratolens.ingest.rate_limit import MinIntervalLimiter


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_waits_minimum_interval():
    clock = FakeClock()
    limiter = MinIntervalLimiter(1.0, clock=clock.time, sleep=clock.sleep)
    limiter.wait()
    clock.now += 0.25
    limiter.wait()
    clock.now += 2.0
    limiter.wait()
    assert clock.sleeps == [0.75]
