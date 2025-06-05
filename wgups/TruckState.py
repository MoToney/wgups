class TruckState:
    def __init__(self, id, start_location, start_time):
        self.id = id
        self.current_location = start_location
        self.current_time = start_time
        self.route = [("None", start_location)]
        self.visited_ids = set()
        self.total_distance = 0.0