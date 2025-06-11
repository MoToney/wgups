import heapq
from itertools import count
from collections import defaultdict
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

    def select_packages_by_priority(self, priority_queue: heapq, current_time: datetime, visited: set,
                                    max_size: int) -> list[int]:
        mock_time = current_time
        relevant_packages = []
        current_location = "HUB"

        while priority_queue and max_size > 0:
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
                for group in package_id:
                    if len(group) > max_size:
                        continue

                    grouped_packages_w_deadline = []
                    for pid in group:
                        pkg = self.packages.search_package(pid)
                        if pkg.deadline:
                            heapq.heappush(grouped_packages_w_deadline,
                                           (pkg.deadline, pkg.package_id, pkg.address_w_zip))

                    group_is_deliverable = True

                    while grouped_packages_w_deadline:
                        deadline, p_id, addr_zip = heapq.heappop(grouped_packages_w_deadline)
                        eta = self.get_estimated_delivery_time(mock_time, current_location, addr_zip)

                        if eta > deadline:
                            group_is_deliverable = False
                            break
                        mock_time = eta
                        current_location = addr_zip

                    if group_is_deliverable:
                        for pid in group:
                            relevant_packages.append(pid)
                            max_size -= 1
                            if max_size == 0:
                                return relevant_packages
                continue

            if priority == 3:
                if isinstance(package_id, list):
                    for deadline_time, pid in package_id:
                        pkg = self.packages.search_package(pid)
                        travel_time = self.get_estimated_delivery_time(mock_time, current_location,
                                                                       pkg.address_w_zip)

                        # ADD IF A MATCHING PACKAGE IS ALREADY ADDED
                        siblings = getattr(pkg, 'packages_at_same_address', [])
                        if siblings and any(sid in relevant_packages for sid in siblings) and pid not in relevant_packages:
                            relevant_packages.append(pid)
                            max_size -= 1

                        elif travel_time <= pkg.deadline and pid not in relevant_packages:
                            relevant_packages.append(pid)
                            mock_time = travel_time
                            current_location = pkg.address_w_zip
                            max_size -= 1

                        if siblings and pid in relevant_packages and max_size > 0:
                            for sid in siblings:
                                if sid != pid and sid not in relevant_packages and max_size > 0 and  self.is_package_in_priority_queue(priority_queue, sid):
                                    print(f"{sid} caught at priority 3")
                                    relevant_packages.append(sid)
                                    max_size -= 1
                                    if max_size == 0:
                                        break
                            if max_size == 0:
                                break
                    continue

            for pid in relevant_packages:
                pkg = self.packages.search_package(pid)
                siblings = getattr(pkg, 'packages_at_same_address', [])
                if siblings:
                    for sid in siblings:
                        if sid != pid and sid not in relevant_packages and max_size > 0 and self.is_package_in_priority_queue(
                                priority_queue, sid):
                            print(f"{sid} caught with for loop")
                            relevant_packages.append(sid)
                            max_size -= 1
                            if max_size == 0:
                                break
                    if max_size == 0:
                        break


            if priority == 4:
                raise ValueError("should not happen there are no groups that don't have deadline")

            if priority == 5 and max_size > 0:
                if package_id in relevant_packages:
                    continue
                relevant_packages.append(package_id)
                max_size -= 1

                package = self.packages.search_package(package_id)
                siblings = getattr(package, 'packages_at_same_address', [])
                if siblings:
                    for sid in siblings:
                        if sid != package_id and sid not in relevant_packages and max_size > 0 and self.is_package_in_priority_queue(
                                priority_queue, sid):
                            print(f"{sid} caught at priority 5")
                            relevant_packages.append(sid)
                            max_size -= 1
                            if max_size == 0:
                                break
                    if max_size == 0:
                        break
                continue

            if max_size == 0:
                break
        return relevant_packages

    def is_package_in_priority_queue(self, priority_queue, pid_to_find):
        for priority, item in priority_queue:
            if isinstance(item, list):
                for sub in item:
                    if isinstance(sub, tuple):
                        if sub[1] == pid_to_find:
                            return True
                    elif sub == pid_to_find:
                        return True
            elif item == pid_to_find:
                return True
        return False

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

    def build_prioritized_route(self, deadline_groups: defaultdict[list, Any], mock_time: datetime, current_location):
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

    def find_all_feasible_insertions(self, starting_point, base_route, unprioritized_packages, slack_time):
        choices = []
        counter = count()
        for package in unprioritized_packages:
            #PACKAGE 24!!!

            previous_stop = starting_point
            time_prev_stop_to_package, time_package_to_next_stop = None, None

            for i, stop in enumerate(base_route):
                if time_prev_stop_to_package is None:
                    if isinstance(starting_point, str):
                        time_prev_stop_to_package = self.get_travel_time("HUB", package.address_w_zip)
                    elif isinstance(starting_point, Package):
                        time_prev_stop_to_package = self.get_travel_time(previous_stop.address_w_zip,
                                                                         package.address_w_zip)

                time_package_to_next_stop = self.get_travel_time(package.address_w_zip, stop.address_w_zip)
                time_added = time_prev_stop_to_package + time_package_to_next_stop

                if time_added <= slack_time:
                    if isinstance(previous_stop, Package) and self.get_travel_time(previous_stop.address_w_zip,
                                                                                   stop.address_w_zip) > time_package_to_next_stop:
                        heapq.heappush(choices, (time_added, next(counter), previous_stop, stop, package))

                time_prev_stop_to_package = time_package_to_next_stop
                previous_stop = stop

        return choices

    def insert_best_feasible_packages(self, base_route, potential_packages, regular_packages, slack_time):
        added_to_route = set()

        while potential_packages:  # add packages in their optimal position until the slack_time is exhausted
            travel_time, counter, prev_stop, next_stop, package = heapq.heappop(potential_packages)

            if travel_time > slack_time:
                print("No more insertions possible within slack time. and time has been exceeded")
                return base_route, slack_time, regular_packages

            if package in added_to_route:
                continue

            inserted = False
            if prev_stop == 'HUB':  # check if prev_stop is "HUB" because HUB is not in the base_route
                base_route.insert(0, package)
                index = 0
                inserted = True
            elif isinstance(prev_stop, Package):  # if the previous stop is a Package
                found = False
                for index, stop in enumerate(base_route):  # search for the stop and get it's index
                    if stop == prev_stop:  # if the correct
                        if index + 1 < len(base_route) and base_route[index + 1] == next_stop:
                            base_route.insert(index + 1, package)
                            inserted = True
                            found = True
                            break
                if not found:
                    continue
            if not inserted:
                continue

            slack_time -= travel_time
            regular_packages.remove(package)
            added_to_route.add(package)



            # check if there's a follow-up insertion that is best
            if index + 1 < len(base_route):  # if the package was not inserted at the end
                new_inserts = self.find_all_feasible_insertions(
                    starting_point=package, base_route=base_route,
                    unprioritized_packages=regular_packages, slack_time=slack_time)

                while new_inserts:
                    time_added, counter,prev_stop, next_stop, package = heapq.heappop(new_inserts)
                    if package not in added_to_route:
                        heapq.heappush(potential_packages, (time_added, counter,prev_stop, next_stop, package))
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

    def sort_packages(self, prioritized_packages: list[int], visited: set, current_time: datetime):
        mock_time = current_time
        current_location = "HUB"
        visited = visited.union(prioritized_packages)

        deadline_groups, regular_packages = self.sort_packages_by_deadline(prioritized_packages)
        if deadline_groups:
            prioritized_route, slack_time = self.build_prioritized_route(deadline_groups, current_time,
                                                                         current_location)

            for index, stop in enumerate(prioritized_route):
                siblings = getattr(stop, 'packages_at_same_address', [])
                sibling = None
                if siblings:
                    for sid in siblings:
                        sibling = self.packages.search_package(sid)
                        if sibling and sibling in regular_packages:
                            prioritized_route.insert(index+1, sibling)
                            regular_packages.remove(sibling)

            print(len(prioritized_route), len(regular_packages))

            # add the packages that have potential to be fit in between the expedited packages
            potential_package_insertions = self.find_all_feasible_insertions("HUB", prioritized_route,
                                                                             regular_packages, slack_time)

            base_route, new_slack_time, packages_not_in_route = (self.insert_best_feasible_packages
                                                                 (prioritized_route, potential_package_insertions,
                                                                  regular_packages, slack_time))

            print(len(base_route), len(packages_not_in_route))

            current_stop = base_route[-1]

            completed_route = self.build_regular_route(route=base_route, packages_not_in_route=packages_not_in_route,
                                                       current_stop=current_stop)
        else:
            completed_route = self.build_regular_route(route=[], packages_not_in_route=regular_packages,
                                                       current_stop="HUB")
        completed_time, miles_travelled = self.get_mock_completion_time_and_distance(completed_route, current_time,
                                                                                     current_location)

        return completed_route, completed_time, miles_travelled, visited

    def get_mock_completion_time_and_distance(self, route, start_time, current_location):
        distance_travelled = 0
        for stop in route:
            distance_travelled += self.distance_map.get_distance(current_location, stop.address_w_zip)
            travel_time = self.get_estimated_delivery_time(start_time, current_location, stop.address_w_zip)
            start_time = travel_time
            current_location = stop.address_w_zip

        return start_time, distance_travelled

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
        priorities = self.select_packages_by_priority(priority_queue, curr_time, visited, 16)
        final_route, final_time, final_miles_travelled, final_visited_ids = self.sort_packages(priorities, visited,
                                                                                               curr_time)

        return final_route, final_time, final_miles_travelled, final_visited_ids


"""
distancesmap = DistanceMap("../data/distances.csv")
packs = PackageLoader("../data/packages.csv", PackageHashMap(61, 1, 1, .75)).get_map()
routing = Routing(distancesmap, packs)
current_tha_time = datetime(1900, 1, 1, 8, 0)

sorty, timey,disty, visity = routing.build_route(1, current_tha_time, set())
print(sorty, timey, disty, visity)

twosorty, twotimey, twovisity = routing.build_route(2, current_tha_time, visity)
print(twosorty, twovisity, twotimey)
for package in twosorty:
    print(package)

first_to_arrive = min(timey, twotimey)
print(first_to_arrive)

threesorty, threetimey, threevisity = routing.build_route(3, first_to_arrive, twovisity)
print(threesorty, threetimey, threevisity)
"""
