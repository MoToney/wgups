import heapq
from itertools import count
from queue import PriorityQueue
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Any

from wgups.Package import Package
from wgups.TruckState import TruckState
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:

    def __init__(self, distance_map: DistanceMap):
        self.distance_map = distance_map
        self.group_to_route: dict[frozenset[int], int] = {}
        self.update_address_time: datetime.time = datetime(1900, 1, 1, 10, 20)
        self.correct_address = {
            9: "410 S. State St., Salt Lake City, UT 84111"
        }

    def build_route(self, route_id: int, start: str, packages: PackageHashMap, visited_ids: set, current_time: datetime,
                    max_capacity: int, total_dist: int = 0):
        route = [("None", start)]
        current_location = start

        # get all possible choices for this route
        available_packages = self.get_available_packages(packages=packages, visited_ids=visited_ids,
                                                         current_time=current_time, route_id=route_id)

        while len(route) < max_capacity:

            scored_packages = self.get_scored_packages(available_packages=available_packages, current_time=current_time,
                                                       current_location=current_location, visited_ids=visited_ids,
                                                       route_id=route_id)
            """for package,score in scored_packages:
                print(str(package.package_id), score)"""

            # if no more valid options
            if not scored_packages:
                break

            # select lowest cost package
            best_package = self.select_best_package(scored_packages=scored_packages)

            # add group if needed
            group = self.get_package_group(best_package=best_package, packages=packages, visited_ids=visited_ids)

            # check if adding group exceeds capacity
            if len(route) + len(group) > max_capacity:
                print("mark_group_as_skipped(group)")
                continue

            # add package(s) to route
            current_location, current_time, total_dist = self.add_group_to_route(group=group, route=route,
                                                                                 visited_ids=visited_ids,
                                                                                 current_location=current_location,
                                                                                 current_time=current_time,
                                                                                 total_dist=total_dist)

            # refresh possible choices for next stop
            available_packages = self.get_available_packages(packages, visited_ids, current_time, route_id)

        return route, self.group_to_route, visited_ids, current_time, total_dist, available_packages

    """def get_available_packages(self, packages: PackageHashMap, visited_ids: set, current_time: datetime,
                               route_id: int) -> dict[str: deque(Package)]:
        available_packages = {
            "required": deque(),
            "deadline": deque(),
            "normal": deque()
        }

        for package in packages.packages_table:
            if not isinstance(package, Package):
                continue

            if package.package_id not in visited_ids:
                available = True

                if package.available_time and package.available_time > current_time.time():
                    continue
                if package.wrong_address:
                    if self.update_address_time > current_time.time():
                        continue
                    else:
                        if package.package_id == 9:
                            package.address, package.city, package.zip_code = "410 S State St","Salt Lake City","84111"
                            package.address_w_zip = "410 S State St(84111)"

                if package.required_truck and package.required_truck == route_id:
                    available_packages["required"].append(package)

                if available:
                    available_packages["normal"].append(package)
        return available_packages"""

    def get_priority_queue(self, packages: PackageHashMap, visited_ids: set, current_time: datetime, route_id: int):
        priority_queue = []
        grouped_packages = []
        priority_3_packages = []
        for package in packages.packages_table:
            priority = None
            if not isinstance(package, Package):
                continue
            if package.package_id in grouped_packages:
                continue
            if package.package_id in visited_ids:
                continue
            if package.available_time and package.available_time > current_time:
                continue
            if package.wrong_address and self.update_address_time > current_time:
                continue

            if package.must_be_delivered_with:
                for pid in package.must_be_delivered_with:
                    package_in_group = packages.search_package(pid)
                    if package_in_group.deadline:
                        priority = 2
                if priority is None:
                    priority = 4
                else:
                    priority = min(priority, 4)

                for pid in package.must_be_delivered_with:
                    groupmate = packages.search_package(pid)
                    grouped_packages.append(groupmate.package_id)
                heapq.heappush(priority_queue, (priority, [grouped_packages]))
                continue

            if package.required_truck == route_id:
                priority = 1
                heapq.heappush(priority_queue, (priority, package.package_id))
                continue

            if package.deadline and not package.must_be_delivered_with:
                priority3 = 3
                heapq.heappush(priority_3_packages, (package.deadline, package.package_id))

            else:
                priority = 5
                heapq.heappush(priority_queue, (priority, package.package_id))
        heapq.heappush(priority_queue, (3, priority_3_packages))
        return priority_queue, current_time

    def get_list_from_priority_queue(self, priority_queue: heapq, current_time: datetime, max_size: int) -> list[int]:
        mock_time = current_time
        relevant_packages = []
        current_location = "HUB"
        priority_two_i = 0 # iterator for multiple groups with priority level 2
        priotity_four_i = 0 # iterator for multiple groups with priority level 4
        while priority_queue:
            priority, package_id = heapq.heappop(priority_queue)

            # grab all packages that are required for that truck/route
            if priority == 1:
                relevant_packages.append(package_id)
                max_size -= 1
                continue

            # if there are grouped packages that also have a deadline
            if priority == 2:
                # if not a group
                if not isinstance(package_id, list):
                    raise TypeError("package_id in priority 2 must be a list")
                # if group can't fit
                if len(package_id[priority_two_i]) > max_size:
                    continue
                else:
                    grouped_packages_w_deadline = []

                    for pid in package_id[priority_two_i]:
                        gpackage = packages.search_package(pid)
                        if gpackage.deadline:
                            heapq.heappush(grouped_packages_w_deadline, (gpackage.deadline, gpackage.package_id, gpackage.address_w_zip))

                    while grouped_packages_w_deadline:
                        deadline, p_id, addr_zip =  heapq.heappop(grouped_packages_w_deadline)
                        arrival_time = self.get_estimated_delivery_time(mock_time, current_location, addr_zip)

                        if arrival_time <= deadline:
                            current_location = addr_zip
                            mock_time = arrival_time

                        # remove the entire group if it cannot be delivered within time range
                        if arrival_time > deadline:
                            mock_time = current_time
                            priority_two_i += 1
                            continue

                    for reachable_package in package_id[priority_two_i]:
                        relevant_packages.append(reachable_package)
                        max_size -= 1
                        continue

            if priority == 3:
                if isinstance(package_id, list):
                    for time,pid in package_id:
                        package_w_deadline = packages.search_package(pid)

                        travel_time = self.get_estimated_delivery_time(mock_time, current_location, package_w_deadline.address_w_zip)
                        if travel_time <= package_w_deadline.deadline:
                            mock_time = travel_time
                            current_location = package_w_deadline.address_w_zip
                            relevant_packages.append(package_w_deadline.package_id)
                            max_size -= 1
                        else:
                            pass
                            """print("TOO LATE")
                            print(f"package_id {package_w_deadline} is past deadline")"""
            if priority == 4:
                raise ValueError("should not happen there are no groups that don't have deadline")

            if priority == 5:
                # print(self.)
                relevant_packages.append(package_id)
                max_size -= 1
            if max_size == 0:
                return relevant_packages
        return relevant_packages

    def sort_packages_by_deadline(self, prioritized_packages: list[int]) :
        deadline_groups = defaultdict(list)
        non_expedited_packages = []

        for package_id in prioritized_packages:
            package = packages.search_package(package_id)
            if package.deadline:
                deadline_groups[package.deadline].append(package)
            else: non_expedited_packages.append(package)


        return deadline_groups, non_expedited_packages

    def build_priorized_route(self, deadline_groups: defaultdict[list, Any], mock_time:datetime, current_location):
        base_route = []
        slack_time = timedelta(hours=24, minutes=00, seconds=00)

        for deadline in sorted(deadline_groups.keys()):
            group = deadline_groups[deadline]

            if len(group) == 1:
                package = group[0]
                arrival_time = self.get_estimated_delivery_time(mock_time, current_location, package.address_w_zip)
                slack_time = min(slack_time, (deadline - arrival_time))
                base_route.append(package)
                group.remove(package)
                current_location = package.address_w_zip
                mock_time = arrival_time

            else:
                while len(group) > 0:
                    neighbor = self.get_nearest_neighbor(group, current_time, current_location)
                    base_route.append(neighbor)
                    arrival_time = self.get_estimated_delivery_time(mock_time, current_location, neighbor.address_w_zip)
                    slack_time = min(slack_time, (neighbor.deadline - arrival_time))
                    current_location = neighbor.address_w_zip
                    mock_time = arrival_time
                    group.remove(neighbor)

        return base_route, slack_time

    def get_potential_insertable_packages(self, starting_point, base_route, unprioritized_packages, slack_time):
        choices = []
        counter = count()
        for package in unprioritized_packages:

            previous_stop = starting_point
            time_prev_stop_to_package, time_package_to_next_stop = None, None

            for i, stop in enumerate(base_route):
                if time_prev_stop_to_package is None:
                    if isinstance(starting_point, str):
                        time_prev_stop_to_package = self.get_travel_time(previous_stop, package.address_w_zip)
                    elif isinstance(starting_point, Package):
                        time_prev_stop_to_package = self.get_travel_time(previous_stop.address_w_zip, package.address_w_zip)

                time_package_to_next_stop = self.get_travel_time(package.address_w_zip, stop.address_w_zip)
                time_added = time_prev_stop_to_package + time_package_to_next_stop

                if time_added <= slack_time:
                    heapq.heappush(choices, (time_added, next(counter), previous_stop, stop, package))

                    """print(f"Considering package: {package.package_id, package.address_w_zip} "
                          f"\n After stop: {previous_stop}"
                      f"\n Before stop: {stop.package_id, stop.address_w_zip, stop.deadline} "
                      f"\n Time to package: {time_prev_stop_to_package} Time from package to stop: {time_package_to_next_stop} "
                      f"\n Total time added {time_added}\n")"""

                time_prev_stop_to_package = time_package_to_next_stop
                previous_stop = stop


        return choices

    def insert_potential_packages_into_base_route(self, base_route, potential_packages, regular_packages, slack_time):
        added_to_route = set()
        time_added = timedelta(hours=0,minutes=0,seconds=0)

        while potential_packages: # add packages in their optimal position until the slack_time is exhausted
            travel_time, counter, prev_stop, next_stop, package = heapq.heappop(potential_packages)

            if travel_time > slack_time:
                print("No more insertions possible within slack time. and time has been exceeded")
                break

            if package in added_to_route:
                continue

            if prev_stop == 'HUB': # check if prev_stop is "HUB" because HUB is not in the base_route
                base_route.insert(0, package)
            elif isinstance(prev_stop, Package):  # if the previous stop is a Package
                for index, stop in enumerate(base_route): # search for the stop and get it's index
                    if stop == prev_stop: # if the correct
                        if index + 1 < len(base_route) and base_route[index+1] ==next_stop:
                            base_route.insert(index+1, package)
                            #print(f"package {package.package_id} added travel time of {travel_time}")
                            break
            time_added += travel_time
            slack_time -= travel_time
            regular_packages.remove(package)
            added_to_route.add(package)

            inserted_index = index
            inserted_package = package

            # check if there's a follow-up insertion that is best
            if inserted_index + 1 < len(base_route): # if the package was not inserted at the end
                new_insertables = self.get_potential_insertable_packages(
                    starting_point=inserted_package, base_route=base_route,
                    unprioritized_packages=regular_packages,slack_time=slack_time)

                potential_packages = []

                for item in new_insertables:
                    if item[4] not in added_to_route:
                        heapq.heappush(potential_packages, item)
        return base_route, slack_time, regular_packages

    def sort_packages(self, prioritized_packages: list[int], current_time: datetime):
        mock_time = current_time
        current_location = "HUB"
        print(f"Packages: {prioritized_packages}\n")

        deadline_groups, regular_packages = self.sort_packages_by_deadline(prioritized_packages)

        base_route, slack_time = self.build_priorized_route(deadline_groups, current_time, current_location)
        #add the packages that have potential to be fit in between the expedited packages
        potential_package_insertions = self.get_potential_insertable_packages("HUB",base_route, regular_packages, slack_time)

        new_base_route, new_slack_time, packages_not_in_route = self.insert_potential_packages_into_base_route(base_route, potential_package_insertions, regular_packages, slack_time)

        fake_time = datetime(1900,1,1, 8, 0)
        fake_current = "HUB"
        for stop in new_base_route:
            travel_time = self.get_estimated_delivery_time(fake_time, fake_current, stop.address_w_zip)
            fake_time = travel_time
            fake_current = stop.address_w_zip
        print(fake_time)


    def get_nearest_neighbor(self,packages:list, current_time,  current_location:str):
        nearest_neighbor = None
        shortest_dist = float("inf")

        for package in packages:
            new_distance = self.distance_map.get_distance(current_location, package.address_w_zip)
            if new_distance < shortest_dist:
                nearest_neighbor = package
                shortest_dist = new_distance

        return nearest_neighbor

    def score(self, package: Package, current_time: datetime, current_location: str, visited_ids: set,
              route_id: int) -> float:
        distance = self.distance_map.get_distance(current_location, package.address_w_zip)
        travel_time = self.get_estimated_delivery_time(distance)
        estimated_delivery_time = current_time + travel_time

        # if required truck

        deadline_boost = 0
        if package.deadline:
            time_remaining = (package.deadline - current_time).total_seconds() / 60
            eta_vs_deadline = (package.deadline - estimated_delivery_time).total_seconds() / 60
            deadline_missed = estimated_delivery_time > package.deadline

            if not deadline_missed:
                urgency = 1 / max(time_remaining, 1)
            else:
                urgency = 0

            if 0 <= eta_vs_deadline <= 30:
                deadline_boost = (30 - eta_vs_deadline) / 30  # scale from 0 to 1
        else:
            urgency = 0
            deadline_missed = False

        #print(f"ETA: {estimated_delivery_time.time()}, Deadline: {package.deadline}, Urgency: {urgency}")

        penalty = 0

        if self.violates_group_constraint(package, visited_ids, route_id):
            penalty += 10000
        if package.required_truck is not None and package.required_truck != route_id:
            penalty += 10000

        ALPHA = 1.0
        BETA = 150.0
        DEADLINE_BOOST_WEIGHT = 500.0

        #print(f"({distance * ALPHA}) - ({urgency * BETA}) + {penalty} ")
        cost = (distance * ALPHA) - (urgency * BETA) - (deadline_boost * DEADLINE_BOOST_WEIGHT) + penalty
        return cost

    def get_scored_packages(self, available_packages: list[Package], current_time: datetime, current_location: str,
                            visited_ids: set, route_id: int) -> list[tuple[Package, float]]:
        scored = []
        for package in available_packages:
            if self.violates_group_constraint(package, visited_ids, route_id):
                continue
            cost = self.score(package, current_time, current_location, visited_ids, route_id)
            scored.append((package, cost))
        return scored

    def select_best_package(self, scored_packages: list[tuple[Package, float]]) -> Package:
        lowest_cost = float("inf")
        for package, cost in scored_packages:
            if cost < lowest_cost:
                lowest_cost = cost
                best = package
        return best

    def violates_group_constraint(self, package: Package, visited_ids: set, route_id: int) -> bool:
        group = package.must_be_delivered_with

        if group is None or len(group) == 0:
            return False

        full_group_ids = set(group + [package.package_id])

        frozen_group = frozenset(full_group_ids)

        visited_in_group = visited_ids & full_group_ids

        # case 1: Partial group already visited (split delivery)
        if 0 < len(visited_in_group) < len(full_group_ids):
            return True

        if frozen_group in self.group_to_route and self.group_to_route[frozen_group] != route_id:
            return True

        return False

    def get_package_group(self, best_package: Package, packages: PackageHashMap, visited_ids: set) -> list[Package]:
        group = set()
        stack = [package.package_id]

        package_has_deadline = False
        package_has_required_truck = False
        package_has_wrong_address = False

        while stack:
            current_id = stack.pop()
            if current_id in visited_ids:
                continue
            visited_ids.add(current_id)
            group.add(current_id)

            current_package = packages.search_package(current_id)
        return group

    def add_group_to_route(self, group: list[Package], route: list[tuple[str, str]], visited_ids: set,
                           current_location: str,
                           current_time: datetime, total_dist: float):
        for pkg in group:
            dist = self.distance_map.get_distance(current_location, pkg.address_w_zip)
            travel_time = self.get_estimated_delivery_time(dist)
            current_time += travel_time
            if pkg.deadline and pkg.deadline > current_time:
                if pkg.must_be_delivered_with:
                    print(f"{pkg.package_id}HAD TO DO IT")
                else:
                    print("YOOOOO")
            total_dist += dist
            visited_ids.add(pkg.package_id)
            route.append((str(pkg.package_id), pkg.address_w_zip))
            current_location = pkg.address_w_zip
        return current_location, current_time, total_dist

    def get_travel_time(self, current_location:str, address_w_zip:str):
        distance = self.distance_map.get_distance(current_location, address_w_zip)
        hours = distance / 18.0
        seconds = hours * 3600
        travel_time = timedelta(seconds=seconds)
        return travel_time

    def get_estimated_delivery_time(self, current_time:datetime, current_location:str, address_w_zip:str):
        estimated_delivery_time = current_time + self.get_travel_time(current_location, address_w_zip)
        return estimated_delivery_time

    def old_cost(self, package: Package, current_time: datetime, current_location: str) -> float:
        distance = self.distance_map.get_distance(current_location, package.address_w_zip)

        if package.deadline:
            time_remaining = (package.deadline - current_time).total_seconds() / 60
            if time_remaining <= 0:
                return float('inf')
            return distance * (60 / time_remaining)  # more urgent
        return distance * 2  # no deadline = deprioritized

    def build_dual_routes(self, packages: PackageHashMap, start_time_1: datetime, start_time_2: datetime,
                          max_capacity: int):
        truck1 = TruckState(1, "HUB", start_time_1)
        truck2 = TruckState(2, "HUB", start_time_2)

        while True:
            combined_visited = truck1.visited_ids | truck2.visited_ids

            next_move = []
            for truck in [truck1, truck2]:
                available = self.get_available_packages(packages, combined_visited, truck.current_time, truck.id)
                scored = self.get_scored_packages(available, truck.current_time, truck.current_location,
                                                  combined_visited, truck.id)
                if scored:
                    best = self.select_best_package(scored)
                    group = self.get_package_group(best, packages, combined_visited)
                    if len(truck.route) + len(group) <= max_capacity:
                        next_move.append((truck, group))

            if not next_move:
                break  # No moves left for either truck

            # Pick the truck whose next move has the lowest cost
            chosen_truck, chosen_group = min(next_move, key=lambda pair: self.score(pair[1][0], pair[0].current_time,
                                                                                    pair[0].current_location,
                                                                                    truck1.visited_ids | truck2.visited_ids,
                                                                                    pair[0].id))

            # Apply group to the chosen truck
            chosen_truck.current_location, chosen_truck.current_time, chosen_truck.total_distance = self.add_group_to_route(
                chosen_group, chosen_truck.route, chosen_truck.visited_ids,
                chosen_truck.current_location, chosen_truck.current_time, chosen_truck.total_distance
            )

        return truck1, truck2

distances = DistanceMap("../data/distances.csv")
packages = PackageLoader("../data/packages.csv", PackageHashMap(61, 1, 1, .75)).get_map()
routing = Routing(distances)

PQ, current_time = (routing.get_priority_queue(packages, set(), datetime(1900,1,1,8,0), 1))
priorities = routing.get_list_from_priority_queue(PQ, current_time=current_time, max_size=16)
sorty = routing.sort_packages(priorities, current_time=current_time)

