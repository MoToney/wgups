import heapq
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import count
from typing import Any, Optional

from wgups.Package import Package

from wgups.SimulationClock import SimulationClock
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap


class Routing:
    """
    Represents the routing of packages to their destinations and the building of routes

    Attributes:
        distance_map (DistanceMap): The distance map of the packages
        packages (PackageHashMap): The hash map of the packages
        clock (SimulationClock): The clock of the simulation
    """

    def __init__(self, distance_map: DistanceMap, packages: PackageHashMap, clock:SimulationClock):
        """
        Initializes the Routing object

        :param distance_map: The distance map of the packages
        :param packages: The hash map of the packages
        :param clock: The clock of the simulation
        """
        self.distance_map = distance_map # stores the distance map of the packages, which is used to calculate the distance between addresses
        self.packages = packages # stores the hash map of the packages
        self.clock = clock # stores the clock of the simulation

        self.MAX_SIZE = 16

    def get_travel_time(self, current_stop: str, next_stop: str) -> timedelta:
        """
        Returns the travel time between two addresses

        :param current_stop: The current location of the truck
        :param next_stop: The next location of the truck
        :return: The travel time between the two addresses
        """
        distance = self.distance_map.get_distance(current_stop, next_stop) # gets the distance between the two stops
        return timedelta(hours=distance / 18.0) # returns the travel time between the two stops

    def get_estimated_delivery_time(self, current_time:datetime, current_location: str, address: str) -> datetime:
        """
        Returns the estimated delivery time of a package

        :param current_time: The current time of the simulation
        :param current_location: The current location of the truck
        :param address: The address of the package
        :return: The estimated delivery time of the package
        """
        return current_time + self.get_travel_time(current_location, address) # returns the elapsed time between the current time and the estimated delivery time

    def update_address(self, package_id: int) -> None:
        """
        Updates the address of a package with the correct address

        :param package_id: The id of the package to update
        :return: None
        """
        package = self.packages[package_id] # gets the package from the hash map
        package.set_full_address("410 S State St", "Salt Lake City", "UT", "84111") # sets the full address of the package (address, city, state, zip code)
        package.lat = 40.757776
        package.lon = -111.8883356
        package.wrong_address = False # sets the wrong address flag to False

    def get_priority_queue(self, current_time:datetime, dispatched_packages: set, truck_id: int) -> (list[tuple[int, Any]], list[Package]):
        """

        Builds a priority queue of packages available for delivery with the following priority:
        1. Packages that are required for a specific truck
        2. Packages that are grouped with a deadline
        3. Packages that have a deadline
        4. Packages that are not grouped with a deadline
        5. Packages that are not required for a specific truck

        :param current_time: The current time of the simulation
        :param dispatched_packages: The set of packages that have already been dispatched to trucks
        :param truck_id: The id of the truck that the package is on
        :return: A priority queue of packages available for delivery
        """
        priority_queue = [] # initializes the priority queue
        packages_in_pq = [] # this will be referenced in self.select_packages_by_priority
        grouped = set() # initializes the set of grouped packages to avoid duplicates

        #checks if the package is in the grouped set, has been visited, has the wrong address, is not available, or is required for another truck
        for package in self.packages:
            # if the package is in the grouped set, it is already being considered for delivery
            if package.package_id in grouped:
                continue
            # if the package has been dispatched, it is already being delivered or has been delivered
            if package.package_id in dispatched_packages:
                continue
            # if the package has a specific time it is available, and the current time is before that time, the package is not available
            if package.available_time is not None and package.available_time > current_time:
                continue
            # if the package has the wrong address, and the update address time has not been reached, the package is not eligible for delivery
            if package.wrong_address:
                continue
            # if the package is required for another truck, it is not eligible for delivery on this truck
            if package.required_truck and package.required_truck != truck_id:
                continue


            #if the package is grouped with other packages
            if package.must_be_delivered_with:
                priority = 4  # default priority for grouped packages without deadline
                # iterate through the packages that must be delivered with the current package
                for pid in package.must_be_delivered_with:
                    package_in_group = self.packages[pid]
                    # if any package in the group has a deadline, the priority is 2
                    if package_in_group.deadline:
                        priority = 2
                group = []
                # add all the packages in the group to the grouped set
                for pid in package.must_be_delivered_with:
                    groupmate = self.packages[pid]
                    grouped.add(groupmate.package_id)
                    group.append(groupmate.package_id)
                    packages_in_pq.append(groupmate)
                heapq.heappush(priority_queue, (priority, group))# add the grouped packages to the priority queue with the priority established above
                continue

            # if the package is required for this truck, the priority is 1
            if package.required_truck == truck_id:
                heapq.heappush(priority_queue, (1, package.package_id)) # add the package to the priority queue with the priority of 1
                packages_in_pq.append(package)
                continue

            """
            if the package has a deadline, and is not grouped with other packages, 
            add the package to the list of packages sorted by which package has the earliest deadline
            """
            if package.deadline and not package.must_be_delivered_with:
                heapq.heappush(priority_queue, (3, package.package_id))
                packages_in_pq.append(package)
                continue

            # if the package has no deadline, not required for by any truck, and is not grouped with other packages, the priority is 5
            heapq.heappush(priority_queue, (5, package.package_id))
            packages_in_pq.append(package)

        return priority_queue, packages_in_pq

    def select_packages_by_priority(self, priority_queue: list[tuple[int, Any]], packages_in_pq: list[Package], current_time:datetime) -> list[int]:
        """
        Selects the packages to be delivered by the truck based on the priority of the package
        and its distance from other packages that are also being delivered

        :param priority_queue: The priority queue of packages
        :param current_time: The current time of the simulation
        :param packages_in_pq: The packages that were in the original priority queue prior to popping any packages

        :return: A list of packages to be delivered by the truck
        """
        primary = [] # initializes the list of packages to be delivered by the truck
        current_location = "HUB" # initializes the current location of the truck
        p3_packages = [] # initializes the list of packages with a deadline
        p5_packages = [] # initializes the list of packages with no special conditions  
        mock_time = current_time # initializes the mock time of the truck


        # while the priority queue is not empty and the truck has not reached its maximum size
        while priority_queue and len(primary) < self.MAX_SIZE:
            prio, package_id = priority_queue.pop()

            if package_id in primary:
                continue

            # if the package is required for this truck
            if prio == 1:
                primary.append(package_id)

            # if the package is grouped with other packages and at least one of the packages has a deadline
            if prio == 2:
                # if not a list, raise an error
                if not isinstance(package_id, list):
                    raise TypeError("package_id in priority 2 must be a list")

                if len(package_id) > (self.MAX_SIZE - len(primary)):
                    continue  # skip if group can't fit

                grouped_packages_w_deadline = [] # initializes the list of packages with a deadline
                # iterate through the packages in the group
                for pid in package_id:
                    pkg = self.packages[pid]
                    # if the package has a deadline, add it to the list of packages with a deadline
                    if pkg.deadline:
                        grouped_packages_w_deadline.append((pkg.deadline, pkg.package_id, pkg.address))
                group_deliverable = True # initializes the group deliverable flag
                local_time = mock_time # initializes the local time of the truck
                local_location = current_location # initializes the local location of the truck
                grouped_packages_w_deadline.sort(key=lambda x: x[0], reverse=True) # sort by earliest deadline
                # while the list of packages with a deadline is not empty check if the packages can be delivered on time
                while grouped_packages_w_deadline:
                    deadline, p_id, addr_zip = grouped_packages_w_deadline.pop()
                    eta = self.get_estimated_delivery_time(local_time, local_location, addr_zip) # gets the estimated delivery time of the package based on the current time, location, and address
                    # if the estimated delivery time is greater than the deadline, the group is not deliverable
                    if eta > deadline:
                        group_deliverable = False
                        break
                    local_time = eta # updates the local time of the truck
                    local_location = addr_zip # updates the local location of the truck
                # if the group is deliverable, add all the packages in the group to the list of packages to be delivered
                if group_deliverable:
                    # iterate through the packages in the group
                    for pid in package_id:
                        # if the package is not already in the list of packages to be delivered and the truck has not reached its maximum size, add the package to the list
                        if pid not in primary and len(primary) < self.MAX_SIZE:
                            primary.append(pid)
                    mock_time = local_time # updates the mock time of the truck
                    current_location = local_location # updates the current location of the truck

            # check the packages that are already in the list of packages to be delivered to see if there are packages at the same address that are not already in the list
            for pid in primary:
                pkg = self.packages[pid]
                primary = self.add_siblings_to_primary(pkg, primary, packages_in_pq)

            # if the package is not grouped with other packages and has a deadline
            if prio == 3:
                pkg = self.packages[package_id] # gets the package from the hash map
                if self.get_estimated_delivery_time(mock_time, current_location,
                                                      pkg.address) <= pkg.deadline:
                    p3_packages.append(self.packages[package_id]) # add the package to the list of packages with a deadline

            # if the package is not grouped with other packages, required for this truck, and has no deadline
            if prio == 5:
                p5_packages.append(self.packages[package_id]) # add the package to the list of packages with no special conditions

            # if the package is grouped with other packages and has no deadline, raise an error because this should not happen
            if prio == 4:
                raise ValueError("Priority 4 should not happen.")

        # after all packages have been checked, handle the packages with a deadline, starting with the earliest deadline
        for dline in sorted({pkg.deadline for pkg in p3_packages if pkg.deadline}):
            batch = [pkg for pkg in p3_packages if pkg.deadline == dline] # get all the packages with the same deadline
            sorted_batch = self.sort_nearest_neighbors(batch, current_location) # sort the packages by the nearest neighbor
            for pkg in sorted_batch:
                if pkg.package_id not in primary and len(primary) < self.MAX_SIZE:
                    eta = self.get_estimated_delivery_time(mock_time, current_location, pkg.address)
                    if eta <= pkg.deadline:
                        primary.append(pkg.package_id)
                        current_location = pkg.address
                        mock_time = eta
                        primary = self.add_siblings_to_primary(pkg, primary, packages_in_pq)

        # if the truck has not reached its maximum size, and there are packages with no special conditions, add the packages to the list of packages to be delivered
        if len(primary) < self.MAX_SIZE and p5_packages:
            sorted_p5 = self.sort_nearest_neighbors(p5_packages, current_location) # sort the packages with no special conditions by the nearest neighbor
            # iterate through the sorted packages
            for pkg in sorted_p5:
                # if the package is not already in the list of packages to be delivered, and the truck has not reached its maximum size, add the package to the list of packages to be delivered
                if pkg.package_id not in primary and len(primary) < self.MAX_SIZE:
                    primary.append(pkg.package_id) # add the package to the list of packages to be delivered
                    primary = self.add_siblings_to_primary(pkg, primary, packages_in_pq)

        return primary

    def get_eligible_siblings(self, package: Package, primary: set[int], packages_in_pq: list[Package]) -> list[int]:
        """
        Gets eligible sibling packages that can be added to the delivery list

        :param package: The package to find siblings for
        :param primary: The current list of packages to be delivered
        :param packages_in_pq: The packages that are in the priority queue
        :return: List of eligible sibling package IDs
        """
        eligible_siblings = [] # initializes the list of eligible siblings
        siblings = package.get_siblings() # gets the packages at the same address as the current package

        # if the package has siblings
        if siblings:
            # iterate through the siblings
            for sid in siblings:
                # if the sibling is not the current package, is not already in the list of packages to be delivered, and the truck has not reached its maximum size, and the sibling is in the priority queue, add the sibling to the list of eligible siblings
                if (sid != package.package_id and
                    sid not in primary and
                    len(primary) < self.MAX_SIZE and # if the truck has not reached its maximum size
                    self.packages[sid] in packages_in_pq):
                    eligible_siblings.append(sid) # add the sibling to the list of eligible siblings
        return eligible_siblings

    def add_siblings_to_primary(self, package: Package, primary: list[int], packages_in_pq: list[Package]) -> list[int]:
        """
        Adds eligible sibling packages to the primary delivery list

        :param package: The package to find siblings for
        :param primary: The current list of packages to be delivered
        :param packages_in_pq: The packages in the priority queue
        """
        eligible_siblings = self.get_eligible_siblings(package, primary, packages_in_pq) # gets the eligible siblings
        mock_primary = primary
        for sid in eligible_siblings:
            if len(mock_primary) < self.MAX_SIZE:
                mock_primary.append(sid) # add the eligible sibling to the list of packages to be delivered
        return mock_primary

    def sort_packages_by_deadline(self, prioritized_packages: list[int]) -> tuple[list[tuple[datetime, list[Package]]], list[Package]]:
        deadline_groups = defaultdict(list)
        regulars = [] # initializes the list of packages with no deadline

        # iterate through the prioritized packages
        for pid in prioritized_packages:
            pkg = self.packages[pid]
            # if the package has a deadline, add it to the dictionary of packages by deadline
            if pkg.deadline:
                deadline_groups[pkg.deadline].append(pkg)
            else:
                regulars.append(pkg) # add the package to the list of packages with no deadline

        return deadline_groups, regulars

    def build_prioritized_route(self, deadline_groups: defaultdict[list], current_time: datetime, current_location: str) -> tuple[list[Package], timedelta]:
        base_route = [] # initializes the list of packages to be delivered
        slack_time = timedelta(hours=24) # initializes the slack time, this is the time that the truck can be late by

        # iterate through the deadlines
        for deadline in sorted(deadline_groups.keys()):
            group = deadline_groups[deadline]

            # if the deadline has only one package listed under it
            if len(group) == 1:
                package = group[0] # get the package from the group
                arrival_time = self.get_estimated_delivery_time(current_time, current_location, package.address)
                slack_time = min(slack_time, (package.deadline - arrival_time)) # update the slack time
                base_route.append(package) # add the package to the base route
                current_location = package.address
                current_time = arrival_time
            else:
                # Sort packages by nearest neighbor and deliver them
                sorted_group = self.sort_nearest_neighbors(group, current_location) # sort the group by the nearest neighbor
                for package in sorted_group:
                    arrival_time = self.get_estimated_delivery_time(current_time, current_location, package.address) # get the estimated delivery time of the package
                    slack_time = min(slack_time, (package.deadline - arrival_time)) # update the slack time
                    base_route.append(package) # add the package to the base route
                    current_location = package.address
                    current_time = arrival_time

        return base_route, slack_time

    def find_all_feasible_insertions(self, starting_point: str | Package, base_route: list[Package], unprioritized_packages: list[Package], slack_time: timedelta) -> list[tuple[float, int, Any, Any, Package]]:
        """
        Finds all feasible insertion points for packages in the route

        :param starting_point: The starting point (HUB or Package)
        :param base_route: The base route to insert packages into
        :param unprioritized_packages: Packages to consider for insertion
        :param slack_time: Available slack time for insertions
        :return: List of feasible insertions as (time_added, counter, prev_stop, next_stop, package)
        """
        choices = []
        counter = count()

        for package in unprioritized_packages:
            previous_stop = starting_point
            time_prev_stop_to_package = None

            # Check each possible insertion point in the route
            for stop in base_route:
                # Calculate travel time from previous stop to package (only once per package)
                if time_prev_stop_to_package is None:
                    if isinstance(starting_point, str):
                        time_prev_stop_to_package = self.get_travel_time("HUB", package.address)
                    elif isinstance(starting_point, Package):
                        time_prev_stop_to_package = self.get_travel_time(previous_stop.address, package.address)

                # Calculate travel time from package to next stop
                time_package_to_next_stop = self.get_travel_time(package.address, stop.address)
                # Total additional time if package is inserted here
                time_added = time_prev_stop_to_package + time_package_to_next_stop

                # Check if insertion is feasible within slack time
                if time_added <= slack_time:
                    # Check if insertion is beneficial (reduces total route time)
                    should_insert = True
                    if isinstance(previous_stop, Package):
                        # Compare with original direct route time
                        original_time = self.get_travel_time(previous_stop.address, stop.address)
                        should_insert = time_added < original_time

                    if should_insert:
                        heapq.heappush(choices, (time_added, next(counter), previous_stop, stop, package))

                # Update for next iteration
                time_prev_stop_to_package = time_package_to_next_stop
                previous_stop = stop

        return choices

    def insert_best_feasible_packages(self, base_route: list[Package], insertion_heap: list[tuple[float, int, Any, Any, Package]], remaining_packages: list[Package], slack_time: timedelta) -> tuple[list[Package], timedelta, list[Package]]:
        """
        Inserts the best feasible packages into the route

        :param base_route: The base route to insert packages into
        :param insertion_heap: Heap of feasible insertions
        :param remaining_packages: Packages not yet inserted
        :param slack_time: Available slack time
        :return: Updated route, remaining slack time, and remaining packages
        """
        inserted_packages = set()

        while insertion_heap and slack_time > timedelta(0):  # add packages in their optimal position until the slack_time is exhausted
            travel_time, _, prev_stop, next_stop, package = heapq.heappop(insertion_heap)

            if travel_time > slack_time:
                break

            if package in inserted_packages:
                continue

            # Try to insert the package
            insert_idx = self._find_insertion_index(base_route, prev_stop, next_stop)
            if insert_idx is None:
                continue

            base_route.insert(insert_idx, package)
            slack_time -= travel_time
            if package in remaining_packages:
                remaining_packages.remove(package)
            inserted_packages.add(package)

            # Check for new feasible insertions after this insertion
            if insert_idx + 1 < len(base_route):
                new_inserts = self.find_all_feasible_insertions(
                    starting_point=package, base_route=base_route,
                    unprioritized_packages=remaining_packages, slack_time=slack_time)

                for insertion in new_inserts:
                    if insertion[4] not in inserted_packages:  # package not already inserted
                        heapq.heappush(insertion_heap, insertion)

        return base_route, slack_time, remaining_packages

    def _find_insertion_index(self, base_route: list[Package], prev_stop: str | Package, next_stop: Package) -> int | None:
        """
        Finds the insertion index for a package between prev_stop and next_stop

        :param base_route: The base route
        :param prev_stop: The previous stop
        :param next_stop: The next stop
        :return: Insertion index or None if not found
        """
        if prev_stop == 'HUB':
            return 0
        elif isinstance(prev_stop, Package):
            for i, stop in enumerate(base_route):
                if stop == prev_stop:
                    # if the next stop is the next stop in the base route, return the index of the next stop
                    if i + 1 < len(base_route) and base_route[i + 1] == next_stop:
                        return i + 1
        return None

    def build_regular_route(self, route: list[Package], packages_not_in_route: list[Package], current_stop: str | Package) -> list[Package]:
        """
        Builds a route by always selecting the nearest package to the current stop.

        :param route: The existing route (will be extended)
        :param packages_not_in_route: Packages not yet in the route (will be depleted)
        :param current_stop: Starting location ('HUB' or a Package)
        :return: The completed route (with all packages added)
        """
        while packages_not_in_route:
            # Figure out the current address
            if isinstance(current_stop, str):
                curr_address = current_stop
            elif isinstance(current_stop, Package):
                curr_address = current_stop.address
            else:
                raise TypeError(f"current_stop must be str or Package, not {type(current_stop)}")

            # Select nearest neighbor from remaining packages
            next_package = self.get_nearest_neighbor(packages_not_in_route, curr_address)
            if next_package is None:
                # Defensive: if no reachable package, break
                break

            route.append(next_package)
            current_stop = next_package
            packages_not_in_route.remove(next_package)
        return route

    def get_mock_completion_time_and_distance(self, route: list[Package | str], current_time: datetime, current_location: str) -> tuple[datetime, float]:
        """
        Calculates the completion time and total distance for a route
        
        :param route: The route to calculate
        :param current_time: Starting time
        :param current_location: Starting location
        :return: Completion time and total distance
        """
        distance_travelled = 0.0

        for stop in route:
            if isinstance(stop, Package):
                stop_address = stop.address
            elif isinstance(stop, str):
                stop_address = stop
            else:
                continue

            distance = self.distance_map.get_distance(current_location, stop_address)
            travel_time = self.get_travel_time(current_location, stop_address)
            distance_travelled += distance
            current_time += travel_time
            current_location = stop_address

        # Add return to HUB
        distance = self.distance_map.get_distance(current_location, "HUB")
        travel_time = self.get_travel_time(current_location, "HUB")
        distance_travelled += distance
        current_time += travel_time

        return current_time, distance_travelled

    def get_nearest_neighbor(self, packages: list[Package], current_location: str) -> Optional[Package]:
        """
        Finds the nearest neighbor package from current location
        
        :param packages: List of packages to search
        :param current_location: Current location
        :return: Nearest package or None if no packages
        """
        candidates = [pkg for pkg in packages if
                      self.distance_map.get_distance(current_location, pkg.address) < float('inf')]
        if not candidates:
            return None
        return min(candidates, key=lambda pkg: self.distance_map.get_distance(current_location, pkg.address))

    def sort_nearest_neighbors(self, pkgs: list[Package], start_location: str) -> list[Package]:
        """
        Sorts packages by nearest neighbor algorithm
        
        :param pkgs: List of packages to sort
        :param start_location: Starting location
        :return: Sorted list of packages
        """
        route = []
        current = start_location
        to_visit = set(pkgs)

        while to_visit:
            nearest = min(to_visit, key=lambda pkg: self.get_travel_time(current, pkg.address))
            route.append(nearest)
            current = nearest.address
            to_visit.remove(nearest)
        return route

    def sort_packages(self, prioritized_packages: list[int], current_time: datetime, dispatched_packages: set) -> tuple[list[Package], datetime, float, set[int]]:
        current_location = "HUB"
        dispatched_packages = dispatched_packages.union(prioritized_packages)

        deadline_groups, regular_packages = self.sort_packages_by_deadline(prioritized_packages)
        # if there are deadline packages, build the route with the deadline packages
        if deadline_groups:
            prioritized_route, slack_time = self.build_prioritized_route(deadline_groups, current_time,
                                                                         current_location)
            # Prepare siblings to insert after iteration (avoid in-place mutation)
            siblings_to_insert = []
            regular_package_set = set(regular_packages)  # For fast lookup and removal

            for index, stop in enumerate(prioritized_route):
                siblings = getattr(stop, 'packages_at_same_address', [])
                # If there are siblings, queue them for insertion
                if siblings:
                    for sid in siblings:
                        sibling = self.packages[sid]
                        if sibling and sibling in regular_package_set:
                            siblings_to_insert.append((index + 1, sibling))
                            regular_package_set.remove(sibling)

            # Insert siblings in reverse to maintain correct indices
            for index, sibling in reversed(siblings_to_insert):
                prioritized_route.insert(index, sibling)

            # After sibling insertions, use the updated list of remaining regular packages
            remaining_regular_packages = list(regular_package_set)

            # add the packages that have potential to be fit in between the expedited packages
            potential_package_insertions = self.find_all_feasible_insertions("HUB", prioritized_route,
                                                                             remaining_regular_packages, slack_time)

            base_route, new_slack_time, packages_not_in_route = (self.insert_best_feasible_packages
                                                                 (prioritized_route, potential_package_insertions,
                                                                  remaining_regular_packages, slack_time))

            current_stop = base_route[-1]

            completed_route = self.build_regular_route(route=base_route, packages_not_in_route=packages_not_in_route,
                                                       current_stop=current_stop)
        # if there are no deadline packages, build the route using only regular packages
        else:
            completed_route = self.build_regular_route(route=[], packages_not_in_route=regular_packages,
                                                       current_stop="HUB")

        completed_time, miles_travelled = self.get_mock_completion_time_and_distance(completed_route, current_time, "HUB")

        return completed_route, completed_time, miles_travelled, dispatched_packages

    def build_route(self, route_id: int, current_time: datetime, dispatched_packages: set) -> tuple[list[Package], datetime, float, set[int]]:
        """
        Builds a route for a truck
        
        :param route_id: The ID of the truck
        :param current_time: The current time
        :param dispatched_packages: The packages that have been dispatched
        :return: The completed route, the completion time, the miles travelled, and the dispatched packages
        """
        priority_queue, packages_in_pq = self.get_priority_queue(current_time, dispatched_packages, route_id)
        priorities = self.select_packages_by_priority(priority_queue, packages_in_pq, current_time)
        final_route, final_time, final_miles_travelled, final_dispatched_packages = self.sort_packages(priorities, current_time, dispatched_packages)

        return final_route, final_time, final_miles_travelled, final_dispatched_packages

