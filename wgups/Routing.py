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
            9: [
                ["410 S. State St.", "Salt Lake City", "Utah", 84111],
                ["410 S State St(84111)"]
            ]
        }
        self.packages = packages

    def get_priority_queue(self, curr_time, visited: set, route_id: int):
        priority_queue = []
        grouped_packages = []
        priority_3_packages = []
        deadline_groups = defaultdict(list)
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
                deadline_groups[package.deadline].append(package)
                priority3 = 3
                heapq.heappush(priority_3_packages, (package.deadline, package.package_id))

            else:
                priority = 5
                heapq.heappush(priority_queue, (priority, package.package_id))
        heapq.heappush(priority_queue, (3, priority_3_packages))
        print(f"deadline_groups: {deadline_groups}")
        return priority_queue, curr_time

    def select_packages_by_priority(self, priority_queue: heapq, current_time: datetime, visited: set,
                                    max_size: int) -> list[int]:
        mock_time = current_time
        relevant_packages = []
        current_location = "HUB"

        priority_3_packages = []
        priority_5_packages = []

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
                    local_time = mock_time
                    local_location = current_location

                    while grouped_packages_w_deadline:
                        deadline, p_id, addr_zip = heapq.heappop(grouped_packages_w_deadline)
                        eta = self.get_estimated_delivery_time(mock_time, current_location, addr_zip)

                        if eta > deadline:
                            group_is_deliverable = False
                            break
                        local_time = eta
                        local_location = addr_zip

                    if group_is_deliverable:
                        for pid in group:
                            relevant_packages.append(pid)
                            max_size -= 1
                        mock_time = local_time
                        current_location = local_location
                        if max_size == 0:
                            return relevant_packages
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

            if priority == 3:
                if isinstance(package_id, list):
                    for deadline_time, pid in package_id:
                        if pid in relevant_packages:
                            continue
                        pkg = self.packages.search_package(pid)
                        # ADD IF A MATCHING PACKAGE IS ALREADY ADDED
                        siblings = getattr(pkg, 'packages_at_same_address', [])
                        if siblings and any(sid in relevant_packages for sid in siblings) and pid not in relevant_packages:
                            relevant_packages.append(pid)
                            max_size -= 1

                        elif self.get_estimated_delivery_time(mock_time, current_location,
                                                              pkg.address_w_zip) <= pkg.deadline and pid not in relevant_packages:
                            priority_3_packages.append(pkg)

                    continue

            if priority == 4:
                raise ValueError("should not happen there are no groups that don't have deadline")

            if priority == 5 and max_size > 0:
                if package_id in relevant_packages:
                    continue
                else:
                    pkg = self.packages.search_package(package_id)
                    priority_5_packages.append(pkg)

            if max_size == 0:
                break

             # Priority 3: sort by deadline first, then NN within same deadline
            p3_by_deadline = defaultdict(list)
            for pkg in priority_3_packages:
                p3_by_deadline[pkg.deadline].append(pkg)
            for deadline in sorted(p3_by_deadline):
                batch = p3_by_deadline[deadline]
                sorted_batch = self.sort_nearest_neighbor(batch, current_location, self.distance_map.get_distance)
                for pkg in sorted_batch:
                    siblings = getattr(pkg, 'packages_at_same_address', [])
                    if pkg.package_id not in relevant_packages and max_size > 0:
                        relevant_packages.append(pkg.package_id)
                        current_location = pkg.address_w_zip
                        max_size -= 1
                        if siblings:
                            for sid in siblings:
                                if sid != package_id and sid not in relevant_packages and max_size > 0 and self.is_package_in_priority_queue(
                                        priority_queue, sid):
                                    print(f"{sid} caught at priority 3")
                                    relevant_packages.append(sid)
                                    max_size -= 1
                                    if max_size == 0:
                                        break
                            if max_size == 0:
                                break
                if max_size == 0:
                    break

            # Priority 5: NN sort for remaining, starting from wherever you left off
            if max_size > 0 and priority_5_packages:
                sorted_p5 = self.sort_nearest_neighbor(priority_5_packages, current_location,
                                                  self.distance_map.get_distance)
                for pkg in sorted_p5:
                    if pkg.package_id not in relevant_packages and max_size > 0:
                        relevant_packages.append(pkg.package_id)
                        current_location = pkg.address_w_zip
                        max_size -= 1
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
                    sorted_group = self.sort_nearest_neighbor(group, current_location,
                                                           self.distance_map.get_distance)
                    for nearest in sorted_group:
                        base_route.append(nearest)
                        arrival_time = self.get_estimated_delivery_time(mock_time, current_location,
                                                                        nearest.address_w_zip)
                        slack_time = min(slack_time, (nearest.deadline - arrival_time))
                        current_location = nearest.address_w_zip
                        mock_time = arrival_time
                        group.remove(nearest)

        return base_route, slack_time

    def find_all_feasible_insertions(self, starting_point, base_route, unprioritized_packages, slack_time):
        choices = []
        counter = count()
        for package in unprioritized_packages:

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

    def insert_best_feasible_packages(self, base_route, insertion_heap, remaining_packages, slack_time):
        inserted_packages = set()


        while insertion_heap:  # add packages in their optimal position until the slack_time is exhausted
            travel_time, counter, prev_stop, next_stop, package = heapq.heappop(insertion_heap)

            if travel_time > slack_time:
                print("No more insertions possible within slack time. and time has been exceeded")
                return base_route, slack_time, remaining_packages

            if package in inserted_packages:
                continue

            inserted = False
            if prev_stop == 'HUB':  # check if prev_stop is "HUB" because HUB is not in the base_route
                base_route.insert(0, package)
                insert_idx = 0
                inserted = True
            elif isinstance(prev_stop, Package):  # if the previous stop is a Package
                found = False
                for insert_idx, stop in enumerate(base_route):  # search for the stop and get it's index
                    if stop == prev_stop:  # if the correct
                        if insert_idx + 1 < len(base_route) and base_route[insert_idx + 1] == next_stop:
                            base_route.insert(insert_idx + 1, package)
                            inserted = True
                            found = True
                            break
                if not found:
                    continue
            if not inserted:
                continue

            slack_time -= travel_time
            remaining_packages.remove(package)
            inserted_packages.add(package)
            # check if there's a follow-up insertion that is best
            if insert_idx + 1 < len(base_route):  # if the package was not inserted at the end
                new_inserts = self.find_all_feasible_insertions(
                    starting_point=package, base_route=base_route,
                    unprioritized_packages=remaining_packages, slack_time=slack_time)

                while new_inserts:
                    time_added, counter,prev_stop, next_stop, package = heapq.heappop(new_inserts)
                    if package not in inserted_packages:
                        heapq.heappush(insertion_heap, (time_added, counter, prev_stop, next_stop, package))
        return base_route, slack_time, remaining_packages

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

        if len(visited) >= 26:
            pickup_options = []
            updated = False
            updatable_package = None

            distance_travelled = 0
            start_time = current_time
            current_location = "HUB"

            # Step 1: Simulate route to find best pickup time for the updatable package
            for i, stop in enumerate(completed_route):
                # Move to next stop
                distance_to_next = self.distance_map.get_distance(current_location, stop.address_w_zip)
                start_time = self.get_estimated_delivery_time(start_time, current_location, stop.address_w_zip)
                current_location = stop.address_w_zip

                # After the update time, check for pickup opportunity
                if start_time >= self.update_address_time and not updated:
                    # Try to find the updatable package
                    for id in self.correct_address.keys():
                        candidate = self.packages.search_package(id)
                        if isinstance(candidate, Package) and candidate.package_id not in visited:
                            updatable_package = candidate
                            address = self.correct_address[id]
                            # Set all relevant address fields
                            updatable_package.address = address[0][0]
                            updatable_package.city = address[0][1]
                            updatable_package.state = address[0][2]
                            updatable_package.zip_code = address[0][3]
                            updatable_package.address_w_zip = address[1][0]
                            updated = True
                            idx = i
                            break  # Found the package and updated it

                # If we've just updated, record pickup options from this point on
                if updated and updatable_package:
                    # What if I detour to the hub right after this stop?
                    to_hub = self.distance_map.get_distance(current_location, "HUB")
                    arrival_at_hub = self.get_estimated_delivery_time(start_time, current_location, "HUB")
                    detour_cost = to_hub  # Can expand to roundtrip if desired

                    pickup_options.append({
                        'stop_index': i,
                        'time_at_hub': arrival_at_hub,
                        'detour_cost': detour_cost,
                        'route_state': (list(completed_route), current_location, start_time)
                    })

            # Defensive check: Was the package ever found and updated?
            if not updatable_package:
                print("Updatable package was never set (may not be available yet).")
                best_option = None
            else:
                # Pick the best pickup opportunity (here, lowest detour cost)
                if pickup_options:
                    best_option = min(pickup_options, key=lambda x: x['detour_cost'])
                    print("Best pickup:", best_option)
                else:
                    print("No possible pickup opportunity after update_address_time.")
                    best_option = None

                # Step 2: After picking up, find the best insertion point in the route
                # Use the updated package, insert into completed_route after the best pickup
                # For simplicity, use the current completed_route (could make a copy if needed)
            """if best_option:
                pickup_index = best_option['stop_index']
                before_pickup = completed_route[:pickup_index + 1]
                after_pickup = completed_route[pickup_index + 1:]

                insert_options = []
                starting_location = "HUB"

                for i in range(len(after_pickup) +1):
                    if i == 0:
                        before = starting_location
                    else:
                        before = after_pickup[i-1]

                    if i < len(after_pickup):
                        after = after_pickup[i]
                    else:
                        after = None

                    if isinstance(before, str):
                        before_address = before
                    else:
                        before_address = before.address_w_zip

                    if after:
                        after_address = after.address_w_zip
                    else:
                        after_address = None

                    dist_before_to_update = self.distance_map.get_distance(before_address,
                                                                           updatable_package.address_w_zip)
                    if after_address:
                        dist_update_to_after = self.distance_map.get_distance(updatable_package.address_w_zip,
                                                                              after_address)
                    else:
                        dist_update_to_after = 0

                    if after_address:
                        dist_before_to_after = self.distance_map.get_distance(before_address,
                                                                          after_address)
                    else:
                        dist_before_to_after = 0

                    # Net cost to insert between 'before' and 'after'
                    added_cost = dist_before_to_update + dist_update_to_after - dist_before_to_after
                    insert_options.append((i, added_cost))


                best_insert = min(insert_options, key=lambda x: x[1])
                print("Best insert position:", best_insert)

                after_pickup_w_update = after_pickup.copy()
                after_pickup_w_update.insert(best_insert[0], updatable_package)

                new_route = before_pickup + ["HUB"] + after_pickup_w_update
                for stop in new_route:
                    print("Stop in new route:", stop)
                inserted_time, inserted_miles = self.get_mock_completion_time_and_distance(new_route, current_time, starting_location)
                print("Inserted miles:", inserted_miles, "inserted time:", inserted_time)

                test_route = completed_route + ["HUB"] + [updatable_package]
                for stop in test_route:
                    print("Stop in test route:", stop)
                tested_time, tested_miles = self.get_mock_completion_time_and_distance(test_route, current_time, starting_location)
                print("Tested miles:", tested_miles, "tested time:", tested_time)

                if tested_miles < inserted_miles:
                    completed_route = test_route
                elif inserted_miles <= tested_miles:
                    completed_route = new_route"""

        completed_time, miles_travelled = self.get_mock_completion_time_and_distance(completed_route, current_time,
                                                                                     current_location)

        return completed_route, completed_time, miles_travelled, visited

    def get_mock_completion_time_and_distance(self, route, start_time, current_location):
        distance_travelled = 0
        for stop in route:
            if isinstance(stop, Package):
                stop_address = stop.address_w_zip
            elif isinstance(stop, str):
                stop_address = stop
            else:
                stop_address = None

            distance_travelled += self.distance_map.get_distance(current_location, stop_address)
            travel_time = self.get_estimated_delivery_time(start_time, current_location, stop_address)
            start_time = travel_time
            current_location = stop_address

        distance_travelled += self.distance_map.get_distance(current_location, "HUB")
        start_time = self.get_estimated_delivery_time(start_time, current_location, "HUB")

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

    def sort_nearest_neighbor(self, packages, start_location, get_distance):
        route = []
        current = start_location
        to_visit = set(packages)
        while to_visit:
            nearest = min(to_visit, key=lambda pkg: get_distance(current, pkg.address_w_zip))
            route.append(nearest)
            current = nearest.address_w_zip
            to_visit.remove(nearest)
        return route

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
