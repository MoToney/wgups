import heapq
from datetime import datetime, timedelta
from typing import Any, Callable, List, Tuple, Optional


class SimulationClock:
    """
    A simulation clock that manages time progression and event scheduling.
    
    This class provides a discrete event simulation system where events can be
    scheduled for specific times and executed in chronological order. The clock
    maintains a priority queue of events sorted by time.
    """
    
    def __init__(self, start_time: datetime):
        """
        Initializes the simulation clock with a start time.
        
        :param start_time: The initial time for the simulation
        """
        self.current_time = start_time
        self.events: List[Tuple[datetime, int, Callable, Tuple[Any, ...]]] = []  # Priority queue of (time, id, callback, args)

    def now(self) -> datetime:
        """
        Returns the current simulation time.
        
        :return: The current time in the simulation
        """
        return self.current_time

    def advance(self, delta: timedelta) -> None:
        """
        Advances the simulation time by the specified duration.
        
        This method adds time without processing any events.
        Use run_until() to advance time and process events.
        
        :param delta: The time duration to advance by
        """
        self.current_time += delta

    def set_time(self, new_time: datetime) -> None:
        """
        Sets the simulation time to a specific value.
        
        This method directly sets the time without processing events.
        Use run_until() to advance to a specific time and process events.
        
        :param new_time: The new time to set
        """
        self.current_time = new_time

    def until(self, other_time: datetime) -> timedelta:
        """
        Calculates the time difference between current time and another time.
        
        :param other_time: The target time to calculate difference from
        :return: The time difference as a timedelta
        """
        return other_time - self.current_time # returns the time difference between the current time and the other time

    def schedule_event(self, event_time: datetime, callback: Callable, *args: Any) -> None:
        """
        Schedules an event to be executed at a specific time.
        
        Events are stored in a priority queue sorted by time. If multiple events
        are scheduled for the same time, they are ordered by callback ID to ensure
        deterministic execution order.
        
        :param event_time: When the event should be executed
        :param callback: The function to call when the event executes
        :param *args: Arguments to pass to the callback function
        """
        # Use id(callback) as secondary sort key to ensure proper ordering
        # when multiple events are scheduled for the same time
        heapq.heappush(self.events, (event_time, id(callback), callback, args))

    def run_until(self, end_time: datetime) -> None:
        """
        Runs the simulation until the specified end time, processing all events.
        
        This method processes all events that are scheduled up to and including
        the end time. Events are executed in chronological order. After processing
        events, the current time is set to the end time.
        
        :param end_time: The time to run the simulation until
        """
        # Process all events that are scheduled up to the end time
        while self.events and self.events[0][0] <= end_time:
            event_time, _, callback, args = heapq.heappop(self.events)
            self.current_time = event_time  # Update current time to event time
            print(f"[{self.current_time}] Event: {callback.__name__} args={args}") # prints the event time, the name of the callback, and the arguments
            callback(*args)  # Execute the event callback with its arguments
        
        # Set current time to end time after processing all events
        self.current_time = end_time

    def as_human_time(self) -> str:
        """
        Returns the current time formatted as a human-readable string.
        This is used to print the current time in the simulation.

        :return: Current time formatted as "HH:MM"
        """
        return self.current_time.strftime("%H:%M")

    def advance_to_next_event(self) -> None:
        """
        Advances the simulation to the next scheduled event.
        
        If there are no scheduled events, this method does nothing.
        This is useful for stepping through the simulation one event at a time.
        """
        if self.events:
            next_event_time = self.events[0][0]  # Get time of next event
            self.run_until(next_event_time)  # Run until that event



