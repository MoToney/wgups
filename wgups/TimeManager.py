from datetime import datetime, timedelta


class TimeManager:
    def __init__(self, start_time:datetime):
        self.current_time = start_time

    def time_now(self) -> datetime:
        return self.current_time

    def advance(self, duration:timedelta):
        self.current_time += duration

    def set(self, new_time:datetime):
        self.current_time = new_time

    def __str__(self):
        return self.current_time.strftime("%H:%M %p")
