import heapq
from datetime import datetime, timedelta

class SimulationClock:
    def __init__(self, start_time:datetime):
        self.current_time = start_time
        self.events = []

    def now(self):
        return self.current_time

    def advance(self, delta: timedelta):
        self.current_time += delta

    def set_time(self, new_time: datetime):
        self.current_time = new_time

    def until(self, other_time: datetime):
        return other_time - self.current_time

    def schedule_event(self, event_time, callback, *args):
        heapq.heappush(self.events, (event_time, id(callback), callback, args))

    def run_until(self, end_time):
        while self.events and self.events[0][0] <= end_time:
            event_time, _, callback, args = heapq.heappop(self.events)
            self.current_time = event_time
            print(f"[{self.current_time}] Event: {callback.__name__} args={args}")
            callback(*args)
        self.current_time = end_time

    def as_human_time(self):
        return self.current_time.strftime("%H:%M")

    def advance_to_next_event(self):
        if self.events:
            next_event_time = self.events[0][0]
            self.run_until(next_event_time)



