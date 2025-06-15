import heapq
from itertools import count
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from wgups.Package import Package
from wgups.SimulationClock import SimulationClock
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:

    def __init__(self, distance_map: DistanceMap, packages: PackageHashMap, clock:SimulationClock):
        self.distance_map = distance_map
        self.packages = packages
        self.clock = clock

        self.update_address_time: datetime.time = datetime(1900, 1, 1, 10, 20)

    def get_travel_time(self, current_location: str, address_w_zip: str):
        distance = self.distance_map.get_distance(current_location, address_w_zip)
        speed = 18.0
        return timedelta(hours=distance / speed)

    def get_estimated_delivery_time(self, current_time:datetime, current_location: str, address_w_zip: str):
        return current_time + self.get_travel_time(current_location, address_w_zip)

    def update_address(self, package_id):
        package = self.packages[package_id]
        package.set_full_address("410 S. State St.", "Salt Lake City", "Utah", "84111")
        package.set_address_w_zip("410 S State St(84111)")
        package.wrong_address = False
        #print(f"[{clock.as_human_time()}] Address corrected for package {package_id}!")

    def make_available(self, package_id):
        package = self.packages[package_id]
        package.available_time = None
        #print(f"[{clock.as_human_time()}] Package {package_id} has arrived at depot.")

    def get_priority_queue(self, current_time:datetime, visited: set, route_id: int):
        """

        Returns a priority queue of packages available for delivery

        :param now:
        :param visited:
        :param route_id:
        :return:
        """
        priority_queue = []
        grouped = set()
        p3 = []

        for package in self.packages:

            if package.package_id in grouped or package.package_id in visited:
                continue
            if package.available_time is not None and package.available_time > current_time:
                continue
            if package.wrong_address and self.update_address_time > current_time:
                continue
            if package.required_truck and package.required_truck != route_id:
                continue

            if package.must_be_delivered_with:
                for pid in package.must_be_delivered_with:
                    package_in_group = self.packages[pid]
                    if package_in_group.deadline:
                        priority = 2
                if priority is None:
                    priority = 4
                else:
                    priority = min(priority, 4)

                for pid in package.must_be_delivered_with:
                    groupmate = self.packages[pid]
                    grouped.add(groupmate.package_id)
                heapq.heappush(priority_queue, (priority, [grouped]))
                continue

            if package.required_truck == route_id:
                print(f"required truck: {package.required_truck} route_id: {route_id}")
                heapq.heappush(priority_queue, (1, package.package_id))
                continue

            if package.deadline and not package.must_be_delivered_with:
                heapq.heappush(p3, (package.deadline, package.package_id))
            else:
                heapq.heappush(priority_queue, (5, package.package_id))

        heapq.heappush(priority_queue, (3, p3))
        return priority_queue

    def select_packages_by_priority(self, priority_queue: heapq, current_time:datetime, visited: set, max_size: int) -> list[int]:
        primary = []
        current_location = "HUB"
        p3_packages = []
        p5_packages = []
        mock_time = current_time

        while priority_queue and len(primary) < max_size:
            prio, package_id = heapq.heappop(priority_queue)

            # Required-for-truck
            if prio == 1:
                if package_id not in primary:
                    primary.append(package_id)
                continue

            # Grouped with deadline (priority 2)
            if prio == 2:
                if not isinstance(package_id, list):
                    raise TypeError("package_id in priority 2 must be a list")
                for group in package_id:
                    if len(group) > (max_size - len(primary)):
                        continue  # skip if can't fit

                    grouped_packages_w_deadline = []
                    for pid in group:
                        pkg = self.packages[pid]
                        if pkg.deadline:
                            heapq.heappush(grouped_packages_w_deadline,
                                           (pkg.deadline, pkg.package_id, pkg.address_w_zip))

                    group_deliverable = True
                    local_time = mock_time
                    local_location = current_location

                    while grouped_packages_w_deadline:
                        deadline, p_id, addr_zip = heapq.heappop(grouped_packages_w_deadline)
                        eta = self.get_estimated_delivery_time(local_time, local_location, addr_zip)

                        if eta > deadline:
                            group_deliverable = False
                            break
                        local_time = eta
                        local_location = addr_zip

                    if group_deliverable:
                        for pid in group:
                            if pid not in primary and len(primary) < max_size:
                                primary.append(pid)
                        mock_time = local_time
                        current_location = local_location
                continue

            for pid in primary:
                pkg = self.packages[pid]
                siblings = getattr(pkg, 'packages_at_same_address', [])
                if siblings:
                    for sid in siblings:
                        if sid != pid and sid not in primary and len(primary) < max_size and self.is_package_in_priority_queue(
                                priority_queue, sid):
                            print(f"{sid} caught with for loop")
                            primary.append(sid)

            # Priority 3 (deadline, not grouped)
            if prio == 3:
                if isinstance(package_id, list):
                    for deadline_time, pid in package_id:
                        if pid in primary:
                            continue
                        pkg = self.packages[pid]
                        siblings = getattr(pkg, 'packages_at_same_address', [])
                        if siblings and any(sid in primary for sid in siblings) and pid not in primary:
                            primary.append(pid)
                        elif self.get_estimated_delivery_time(mock_time, current_location,
                                                              pkg.address_w_zip) <= pkg.deadline and pid not in primary:
                            p3_packages.append(self.packages[pid])
                continue

            # Priority 5 (everything else)
            if prio == 5:
                if package_id not in primary:
                    p5_packages.append(self.packages[package_id])


            if prio == 4:
                raise ValueError("Priority 4 should not happen.")

        # After main selection, handle deadline (priority 3) packages by deadline, NN sort
        for dline in sorted({pkg.deadline for pkg in p3_packages if pkg.deadline}):
            batch = [pkg for pkg in p3_packages if pkg.deadline == dline]
            sorted_batch = self.sort_nearest_neighbors(batch, current_location)
            for pkg in sorted_batch:
                siblings = getattr(pkg, 'packages_at_same_address', [])
                if pkg.package_id not in primary and len(primary) < max_size:
                    primary.append(pkg.package_id)
                    current_location = pkg.address_w_zip
                    if siblings:
                        for sid in siblings:
                            if sid != pkg.package_id and sid not in primary and len(primary) < max_size and self.is_package_in_priority_queue(
                                    priority_queue, sid):
                                print(f"{sid} caught at priority 3")
                                primary.append(sid)


        # Priority 5: add remainder via NN sort, if space remains
        if len(primary) < max_size and p5_packages:
            sorted_p5 = self.sort_nearest_neighbors(p5_packages, current_location)
            for pkg in sorted_p5:
                if pkg.package_id not in primary and len(primary) < max_size:
                    primary.append(pkg.package_id)
                    current_location = pkg.address_w_zip

        # --- SINGLE ONE-PASS SIBLING EXPANSION HERE ---
        final_packages = set(primary)
        queue = list(primary)
        while queue and len(final_packages) < max_size:
            pid = queue.pop(0)
            pkg = self.packages[pid]
            siblings = pkg.get_siblings() or []
            for sid in siblings:
                if sid not in final_packages and len(final_packages) < max_size and self.is_package_in_priority_queue(
                                        priority_queue, sid):
                    final_packages.add(sid)
                    queue.append(sid)

        return list(final_packages)



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
        regulars = []

        for pid in prioritized_packages:
            pkg = self.packages[pid]
            if pkg.deadline:
                deadline_groups[pkg.deadline].append(pkg)
            else:
                regulars.append(pkg)

        return deadline_groups, regulars

    def build_prioritized_route(self, deadline_groups: defaultdict[list, Any], current_time, current_location):
        base_route = []
        slack_time = timedelta(hours=24)

        for deadline in sorted(deadline_groups.keys()):
            group = deadline_groups[deadline]

            if len(group) == 1:
                package = group[0]
                arrival_time = self.get_estimated_delivery_time(current_time, current_location, package.address_w_zip)
                slack_time = min(slack_time, (package.deadline - arrival_time))
                base_route.append(package)
                group.remove(package)
                current_location = package.address_w_zip
                current_time = arrival_time

            else:
                while group:
                    sorted_group = self.sort_nearest_neighbors(group, current_location)
                    for nearest in sorted_group:
                        base_route.append(nearest)
                        arrival_time = self.get_estimated_delivery_time(current_time, current_location, nearest.address_w_zip)

                        slack_time = min(slack_time, (nearest.deadline - arrival_time))
                        current_location = nearest.address_w_zip
                        mock_time = arrival_time
                        group.remove(nearest)

        return base_route, slack_time

    def get_stop_address(stop):
        return stop.address_w_zip if isinstance(stop, Package) else stop

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
                    if isinstance(previous_stop, Package):
                        if self.get_travel_time(previous_stop.address_w_zip,stop.address_w_zip) > time_package_to_next_stop:
                            heapq.heappush(choices, (time_added, next(counter), previous_stop, stop, package))
                    else:
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

    def sort_packages(self, prioritized_packages: list[int], current_time, visited: set):
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
                        sibling = self.packages[sid]
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

        """if len(visited) >= 26:
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
                        candidate = self.packages[id]
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
            if best_option:
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

        completed_time, miles_travelled = self.get_mock_completion_time_and_distance(completed_route, current_time, current_location)

        return completed_route, completed_time, miles_travelled, visited

    def get_mock_completion_time_and_distance(self, route, current_time, current_location):
        distance_travelled = 0
        for stop in route:
            if isinstance(stop, Package):
                stop_address = stop.address_w_zip
            elif isinstance(stop, str):
                stop_address = stop
            else:
                stop_address = None

            distance = self.distance_map.get_distance(current_location, stop_address)
            travel_time = self.get_travel_time(current_location, stop_address)
            distance_travelled += distance
            current_time += travel_time  # ADVANCE THE MOCK TIME for each leg
            current_location = stop_address

            # Add return to HUB
        distance = self.distance_map.get_distance(current_location, "HUB")
        travel_time = self.get_travel_time(current_location, "HUB")
        distance_travelled += distance
        current_time += travel_time

        return current_time, distance_travelled

    def get_nearest_neighbor(self, packages: list, current_location: str):
        nearest_neighbor = None
        shortest_dist = float("inf")

        for package in packages:
            new_distance = self.distance_map.get_distance(current_location, package.address_w_zip)
            if new_distance < shortest_dist:
                nearest_neighbor = package
                shortest_dist = new_distance

        return nearest_neighbor

    def sort_nearest_neighbors(self, pkgs, start_location):
        route = []
        current = start_location
        to_visit = set(pkgs)
        while to_visit:
            nearest = min(to_visit, key=lambda pkg: self.get_travel_time(current, pkg.address_w_zip))
            route.append(nearest)
            current = nearest.address_w_zip
            to_visit.remove(nearest)
        return route

    def build_route(self, route_id, current_time, visited):
        priority_queue = self.get_priority_queue(current_time, visited, route_id)
        priorities = self.select_packages_by_priority(priority_queue, current_time, visited, 16)
        final_route, final_time, final_miles_travelled, final_visited_ids = self.sort_packages(priorities, current_time, visited)

        return final_route, final_time, final_miles_travelled, final_visited_ids


"""distancesmap = DistanceMap("../data/distances.csv")
packs = PackageLoader("../data/packages.csv", PackageHashMap(61, 1, 1, .75)).get_map()
clock = SimulationClock(datetime(1900,1,1,8,0))
routing = Routing(distancesmap, packs, clock)

clock.schedule_event(datetime(1900,1,1,9,5),routing.make_available, 6)
clock.schedule_event(datetime(1900,1,1,9,5),routing.make_available, 25)
clock.schedule_event(datetime(1900,1,1,9,5),routing.make_available, 28)
clock.schedule_event(datetime(1900,1,1,9,5),routing.make_available, 32)

clock.schedule_event(datetime(1900,1,1,10,20), routing.update_address, 9)

start_time = datetime(1900,1,1,8,0)
clock.run_until(start_time)


sorty, timey, disty, visity = routing.build_route(1, start_time, set())
print(timey, disty, visity)
for package in sorty:
    print(package)


twosorty, twotimey, twodisty, twovisity = routing.build_route(2, start_time, visity)
print(twotimey, twodisty, twovisity)
for package in twosorty:
    print(package)

clock.schedule_event(start_time, deliver_package, 1, sorty, "HUB", 0)
clock.schedule_event(start_time, deliver_package, 2, twosorty, "HUB", 0)

depart_time = min(timey, twotimey)

threesorty, threetimey, threedisty, threevisity = routing.build_route(3, depart_time, twovisity)
print(threetimey, threedisty, threevisity)
for package in threesorty:
    print(package)

clock.run_until(datetime(1900,1,1,17,0))
first_to_arrive = min(timey, twotimey)
print(first_to_arrive)

threesorty, threetimey, threevisity = routing.build_route(3, first_to_arrive, twovisity)
print(threesorty, threetimey, threevisity)"""
