import heapq
from itertools import count
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Any

from wgups.Package import Package
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:

    def __init__(self, distance_map: DistanceMap, packages: PackageHashMap):
        self.distance_map = distance_map
        self.group_to_route: dict[frozenset[int], int] = {}
        self.update_address_time: datetime.time = datetime(1900, 1, 1, 10, 20)
        self.correct_address = {
            9: "410 S. State St., Salt Lake City, UT 84111"
        }
        self.packages = packages

    def get_priority_queue(self, curr_time, visited: set, route_id: int):
        priority_queue = []
        grouped_packages = []
        priority_3_packages = []
        for package in self.packages.packages_table:
            priority = None
            if not isinstance(package, Package):
                continue
            if package.package_id in grouped_packages:
                continue
            if package.package_id in visited:
                continue
            if package.available_time and package.available_time > curr_time:
                continue
            if package.wrong_address and self.update_address_time > curr_time:
                continue

            if package.must_be_delivered_with:
                for pid in package.must_be_delivered_with:
                    package_in_group = self.packages.search_package(pid)
                    if package_in_group.deadline:
                        priority = 2
                if priority is None:
                    priority = 4
                else:
                    priority = min(priority, 4)

                for pid in package.must_be_delivered_with:
                    groupmate = self.packages.search_package(pid)
                    grouped_packages.append(groupmate.package_id)
                heapq.heappush(priority_queue, (priority, [grouped_packages]))
                continue

            if package.required_truck and package.required_truck != route_id:
                continue

            if package.required_truck == route_id:
                print(f"required truck: {package.required_truck} route_id: {route_id}")
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
        return priority_queue, curr_time

    def get_list_from_priority_queue(self, priority_queue: heapq, current_time: datetime, max_size: int) -> list[int]:
        mock_time = current_time
        relevant_packages = []
        current_location = "HUB"
        priority_two_i = 0  # iterator for multiple groups with priority level 2
        priotity_four_i = 0  # iterator for multiple groups with priority level 4
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
                        gpackage = self.packages.search_package(pid)
                        if gpackage.deadline:
                            heapq.heappush(grouped_packages_w_deadline,
                                           (gpackage.deadline, gpackage.package_id, gpackage.address_w_zip))

                    while grouped_packages_w_deadline:
                        deadline, p_id, addr_zip = heapq.heappop(grouped_packages_w_deadline)
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
                    for time, pid in package_id:
                        package_w_deadline = self.packages.search_package(pid)

                        travel_time = self.get_estimated_delivery_time(mock_time, current_location,
                                                                       package_w_deadline.address_w_zip)
                        if travel_time <= package_w_deadline.deadline:
                            mock_time = travel_time
                            current_location = package_w_deadline.address_w_zip
                            relevant_packages.append(package_w_deadline.package_id)
                            max_size -= 1
                        else:
                            break
            if priority == 4:
                raise ValueError("should not happen there are no groups that don't have deadline")

            if priority == 5:
                # print(self.)
                relevant_packages.append(package_id)
                max_size -= 1
            if max_size == 0:
                return relevant_packages
        return relevant_packages

    def sort_packages_by_deadline(self, prioritized_packages: list[int]):
        deadline_groups = defaultdict(list)
        non_expedited_packages = []

        for package_id in prioritized_packages:
            package = self.packages.search_package(package_id)
            if package.deadline:
                deadline_groups[package.deadline].append(package)
            else:
                non_expedited_packages.append(package)

        return deadline_groups, non_expedited_packages

    def build_priorized_route(self, deadline_groups: defaultdict[list, Any], mock_time: datetime, current_location):
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
                    neighbor = self.get_nearest_neighbor(group, current_location)
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
                        time_prev_stop_to_package = self.get_travel_time(previous_stop.address_w_zip,
                                                                         package.address_w_zip)

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
        time_added = timedelta(hours=0, minutes=0, seconds=0)

        while potential_packages:  # add packages in their optimal position until the slack_time is exhausted
            travel_time, counter, prev_stop, next_stop, package = heapq.heappop(potential_packages)

            if travel_time > slack_time:
                print("No more insertions possible within slack time. and time has been exceeded")
                break

            if package in added_to_route:
                continue

            if prev_stop == 'HUB':  # check if prev_stop is "HUB" because HUB is not in the base_route
                base_route.insert(0, package)
            elif isinstance(prev_stop, Package):  # if the previous stop is a Package
                for index, stop in enumerate(base_route):  # search for the stop and get it's index
                    if stop == prev_stop:  # if the correct
                        if index + 1 < len(base_route) and base_route[index + 1] == next_stop:
                            base_route.insert(index + 1, package)
                            # print(f"package {package.package_id} added travel time of {travel_time}")
                            break
            time_added += travel_time
            slack_time -= travel_time
            regular_packages.remove(package)
            added_to_route.add(package)

            inserted_index = index
            inserted_package = package

            # check if there's a follow-up insertion that is best
            if inserted_index + 1 < len(base_route):  # if the package was not inserted at the end
                new_insertables = self.get_potential_insertable_packages(
                    starting_point=inserted_package, base_route=base_route,
                    unprioritized_packages=regular_packages, slack_time=slack_time)

                potential_packages = []

                for item in new_insertables:
                    if item[4] not in added_to_route:
                        heapq.heappush(potential_packages, item)
        return base_route, slack_time, regular_packages

    def build_regular_route(self, route, packages_not_in_route, current_stop):
        while packages_not_in_route:
            if isinstance(current_stop, str):
                next_package = self.get_nearest_neighbor(packages_not_in_route, current_stop)
            elif isinstance(current_stop, Package):
                next_package = self.get_nearest_neighbor(packages_not_in_route, current_stop.address_w_zip)

            else:
                break
            route.append(next_package)
            current_stop = next_package
            packages_not_in_route.remove(next_package)
        return route

    def sort_packages(self, prioritized_packages: list[int], visited:set, current_time: datetime):
        mock_time = current_time
        current_location = "HUB"
        visited = visited.union(prioritized_packages)

        deadline_groups, regular_packages = self.sort_packages_by_deadline(prioritized_packages)
        if deadline_groups:
            prioritized_route, slack_time = self.build_priorized_route(deadline_groups, current_time, current_location)
            # add the packages that have potential to be fit in between the expedited packages
            potential_package_insertions = self.get_potential_insertable_packages("HUB", prioritized_route,
                                                                                  regular_packages, slack_time)

            base_route, new_slack_time, packages_not_in_route = (self.insert_potential_packages_into_base_route
                                                                 (prioritized_route, potential_package_insertions,
                                                                  regular_packages, slack_time))

            current_stop = base_route[-1]

            completed_route = self.build_regular_route(route=base_route, packages_not_in_route=packages_not_in_route,
                                                       current_stop=current_stop)
        else:
            completed_route = self.build_regular_route(route=[], packages_not_in_route=regular_packages,
                                                       current_stop="HUB")

        fake_time = datetime(1900, 1, 1, 8, 0)
        fake_current = "HUB"
        completed_time = self.get_mock_completion_time(completed_route, current_time, current_location)

        return completed_route, completed_time, visited

    def get_mock_completion_time(self, route, start_time, current_location):
        for stop in route:
            travel_time = self.get_estimated_delivery_time(start_time, current_location, stop.address_w_zip)
            start_time = travel_time
            current_location = stop.address_w_zip

        return start_time

    def get_nearest_neighbor(self, packages: list, current_location: str):
        nearest_neighbor = None
        shortest_dist = float("inf")

        for package in packages:
            new_distance = self.distance_map.get_distance(current_location, package.address_w_zip)
            if new_distance < shortest_dist:
                nearest_neighbor = package
                shortest_dist = new_distance

        return nearest_neighbor

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

    def get_travel_time(self, current_location: str, address_w_zip: str):
        distance = self.distance_map.get_distance(current_location, address_w_zip)
        hours = distance / 18.0
        seconds = hours * 3600
        travel_time = timedelta(seconds=seconds)
        return travel_time

    def get_estimated_delivery_time(self, current_time: datetime, current_location: str, address_w_zip: str):
        estimated_delivery_time = current_time + self.get_travel_time(current_location, address_w_zip)
        return estimated_delivery_time

    def build_route(self, route_id, curr_time, visited):
        priority_queue, curr_time = self.get_priority_queue(curr_time, visited, route_id)
        priorities = self.get_list_from_priority_queue(priority_queue, curr_time, 16)
        final_route, final_time, final_visited_ids = self.sort_packages(priorities, visited, curr_time)

        return final_route, final_time, final_visited_ids


"""distances = DistanceMap("../data/distances.csv")
packs = PackageLoader("../data/packages.csv", PackageHashMap(61, 1, 1, .75)).get_map()
routing = Routing(distances, packs)
current_tha_time = datetime(1900, 1, 1, 8, 0)

sorty, timey, visity = routing.build_route(1, current_tha_time, set())
print(sorty, timey, visity)

twosorty, twotimey, twovisity = routing.build_route(2, current_tha_time, visity)
print(twosorty, twovisity, twotimey)
for package in twosorty:
    print(package)

first_to_arrive = min(timey, twotimey)
print(first_to_arrive)

threesorty, threetimey, threevisity = routing.build_route(3, first_to_arrive, twovisity)
print(threesorty, threetimey, threevisity)
"""