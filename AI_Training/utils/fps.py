import time


class FPSCounter:

    def __init__(self, smoothing: int = 30):
        self._times = []
        self._smoothing = smoothing

    def update(self) -> float:
        self._times.append(time.time())

        if len(self._times) > self._smoothing:
            self._times.pop(0)

        return self.get()

    # tương thích code cũ
    def tick(self) -> float:
        return self.update()

    @property
    def fps(self) -> float:
        return self.get()

    def get(self) -> float:
        if len(self._times) < 2:
            return 0.0

        elapsed = self._times[-1] - self._times[0]

        if elapsed <= 0:
            return 0.0

        return (len(self._times) - 1) / elapsed