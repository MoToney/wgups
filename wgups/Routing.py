from datetime import datetime, timedelta
from typing import Any

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

    def get_travel_time(self, current_stop: str, next_stop: str) -> timedelta:
        """
        Returns the travel time between two addresses

        :param current_stop: The current location of the truck
        :param next_stop: The next location of the truck
        :return: The travel time between the two addresses
        """
        distance = self.distance_map.get_distance(current_stop, next_stop) # gets the distance between the two stops
        return timedelta(hours=distance / 18.0) # returns the travel time between the two stops

    def get_estimated_delivery_time(self, current_time:datetime, current_location: str, address_w_zip: str) -> datetime:
        """
        Returns the estimated delivery time of a package

        :param current_time: The current time of the simulation
        :param current_location: The current location of the truck
        :param address_w_zip: The address of the package
        :return: The estimated delivery time of the package
        """
        return current_time + self.get_travel_time(current_location, address_w_zip) # returns the elapsed time between the current time and the estimated delivery time

    def update_address(self, package_id: int) -> None:
        """
        Updates the address of a package with the correct address

        :param package_id: The id of the package to update
        :return: None
        """
        package = self.packages[package_id] # gets the package from the hash map
        package.set_full_address("410 S. State St.", "Salt Lake City", "Utah", "84111") # sets the full address of the package (address, city, state, zip code)
        package.set_address_w_zip("410 S State St(84111)") # sets the address with zip code of the package for use in the distance map
        package.wrong_address = False # sets the wrong address flag to False

    def get_priority_queue(self, current_time:datetime, dispatched_packages: set, truck_id: int) -> list[tuple[int, Any]]:
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
                priority_queue.append((priority, group)) # add the grouped packages to the priority queue with the priority established above
                continue

            # if the package is required for this truck, the priority is 1  
            if package.required_truck == truck_id:
                priority_queue.append((1, package.package_id)) # add the package to the priority queue with the priority of 1
                continue

            """
            if the package has a deadline, and is not grouped with other packages, 
            add the package to the list of packages sorted by which package has the earliest deadline
            """
            if package.deadline and not package.must_be_delivered_with:
                priority_queue.append((3, package.package_id))
                continue
            # if the package has no deadline, not required for by any truck, and is not grouped with other packages, the priority is 5
            priority_queue.append((5, package.package_id))

        priority_queue.sort(key=lambda x: x[0], reverse=True) # sort in ascending order so more prioritized packages are first
        return priority_queue

    def select_packages_by_priority(self, priority_queue: list[tuple[int, Any]], current_time:datetime, dispatched_packages: set, max_size: int) -> list[int]:
        """ 
        Selects the packages to be delivered by the truck based on the priority of the package 
        and its distance from other packages that are also being delivered

        :param priority_queue: The priority queue of packages
        :param current_time: The current time of the simulation
        :param dispatched_packages: The set of packages that have already been dispatched to trucks
        :param max_size: The maximum size of the truck

        :return: A list of packages to be delivered by the truck
        """
        primary = [] # initializes the list of packages to be delivered by the truck
        current_location = "HUB" # initializes the current location of the truck
        p3_packages = [] # initializes the list of packages with a deadline
        p5_packages = [] # initializes the list of packages with no special conditions  
        mock_time = current_time # initializes the mock time of the truck


        # while the priority queue is not empty and the truck has not reached its maximum size
        while priority_queue and len(primary) < max_size:
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

                if len(package_id) > (max_size - len(primary)):
                    continue  # skip if group can't fit

                grouped_packages_w_deadline = [] # initializes the list of packages with a deadline
                # iterate through the packages in the group
                for pid in package_id:
                    pkg = self.packages[pid]
                    # if the package has a deadline, add it to the list of packages with a deadline
                    if pkg.deadline:
                        grouped_packages_w_deadline.append((pkg.deadline, pkg.package_id, pkg.address_w_zip))
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
                        if pid not in primary and len(primary) < max_size:
                            primary.append(pid)
                    mock_time = local_time # updates the mock time of the truck
                    current_location = local_location # updates the current location of the truck

            # check the packages that are already in the list of packages to be delivered to see if there are packages at the same address that are not already in the list
            for pid in primary:
                pkg = self.packages[pid]
                self.add_siblings_to_primary(pkg, primary, priority_queue, max_size)

            # if the package is not grouped with other packages and has a deadline
            if prio == 3:
                pkg = self.packages[package_id] # gets the package from the hash map
                if self.get_estimated_delivery_time(mock_time, current_location,
                                                      pkg.address_w_zip) <= pkg.deadline:
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
                if pkg.package_id not in primary and len(primary) < max_size:
                    eta = self.get_estimated_delivery_time(mock_time, current_location, pkg.address_w_zip)
                    if eta <= pkg.deadline:
                        primary.append(pkg.package_id)
                        mock_time = eta  # <-- important fix here
                        current_location = pkg.address_w_zip
                        self.add_siblings_to_primary(pkg, primary, priority_queue, max_size)

        # if the truck has not reached its maximum size, and there are packages with no special conditions, add the packages to the list of packages to be delivered
        if len(primary) < max_size and p5_packages:
            sorted_p5 = self.sort_nearest_neighbors(p5_packages, current_location) # sort the packages with no special conditions by the nearest neighbor
            # iterate through the sorted packages
            for pkg in sorted_p5:
                # if the package is not already in the list of packages to be delivered, and the truck has not reached its maximum size, add the package to the list of packages to be delivered
                if pkg.package_id not in primary and len(primary) < max_size:
                    primary.append(pkg.package_id) # add the package to the list of packages to be delivered
                    self.add_siblings_to_primary(pkg, primary, priority_queue, max_size)


        return primary
    
    def get_eligible_siblings(self, package: Package, primary: list[int], priority_queue: list[tuple[int, Any]], max_size: int) -> list[int]:
        """
        Gets eligible sibling packages that can be added to the delivery list
        
        :param package: The package to find siblings for
        :param primary: The current list of packages to be delivered
        :param priority_queue: The priority queue of packages
        :param max_size: The maximum size of the truck
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
                    len(primary) < max_size and # if the truck has not reached its maximum size
                    self.is_package_in_priority_queue(priority_queue, sid)):
                    eligible_siblings.append(sid) # add the sibling to the list of eligible siblings
        
        return eligible_siblings

    def add_siblings_to_primary(self, package: Package, primary: list[int], priority_queue: list[tuple[int, Any]], max_size: int) -> None:
        """
        Adds eligible sibling packages to the primary delivery list
        
        :param package: The package to find siblings for
        :param primary: The current list of packages to be delivered
        :param priority_queue: The priority queue of packages
        :param max_size: The maximum size of the truck
        """
        eligible_siblings = self.get_eligible_siblings(package, primary, priority_queue, max_size) # gets the eligible siblings
        for sid in eligible_siblings:
            primary.append(sid) # add the eligible sibling to the list of packages to be delivered

    def is_package_in_priority_queue(self, priority_queue: list[tuple[int, Any]], pid_to_find: int) -> bool:
        """
        Checks if a package is in the priority queue
        
        :param priority_queue: The priority queue of packages
        :param pid_to_find: The package ID to find
        :return: True if the package is in the priority queue, False otherwise
        """
        # iterate through the priority queue
        for priority, item in priority_queue:
            # if the item is a list
            if isinstance(item, list):
                # iterate through the list
                for sub in item:
                    # if the sub item is a tuple
                    if isinstance(sub, tuple):
                        # if the second item in the tuple is the package ID to find, return True
                        if sub[1] == pid_to_find:
                            return True
                    # if the sub item is the package ID to find, return True
                    elif sub == pid_to_find:
                        return True
            # if the item is the package ID to find, return True
            elif item == pid_to_find:
                return True
        return False

    def sort_packages_by_deadline(self, prioritized_packages: list[int]) -> tuple[list[tuple[datetime, list[Package]]], list[Package]]:
        deadline_groups = []
        regulars = [] # initializes the list of packages with no deadline

        # iterate through the prioritized packages
        for pid in prioritized_packages:
            pkg = self.packages[pid]
            # if the package has a deadline, add it to the dictionary of packages by deadline
            if pkg.deadline:
                found = False
                for group in deadline_groups:
                    # if the deadline is already in the list of deadline groups
                    if group[0] == pkg.deadline:
                        group[1].append(pkg) #add the pkg to the list of packages that share that deadline
                        found = True
                        break
                if not found:
                    deadline_groups.append([pkg.deadline, [pkg]])
            else:
                regulars.append(pkg) # add the package to the list of packages with no deadline

        return deadline_groups, regulars

    def build_prioritized_route(self, deadline_groups: list[tuple[datetime, list[Package]]], current_time: datetime, current_location: str) -> tuple[list[Package], timedelta]:
        base_route = [] # initializes the list of packages to be delivered
        slack_time = timedelta(hours=24) # initializes the slack time, this is the time that the truck can be late by

        deadline_groups.sort(key=lambda x: x[0])

        # iterate through the deadlines
        for deadline, group in deadline_groups:

            # if the deadline has only one package listed under it
            if len(group) == 1:
                package = group[0] # get the package from the group
                arrival_time = self.get_estimated_delivery_time(current_time, current_location, package.address_w_zip) 
                slack_time = min(slack_time, (package.deadline - arrival_time)) # update the slack time
                base_route.append(package) # add the package to the base route
                current_location = package.address_w_zip
                current_time = arrival_time
            else:
                # Sort packages by nearest neighbor and deliver them
                sorted_group = self.sort_nearest_neighbors(group, current_location) # sort the group by the nearest neighbor
                for package in sorted_group:
                    arrival_time = self.get_estimated_delivery_time(current_time, current_location, package.address_w_zip) # get the estimated delivery time of the package
                    slack_time = min(slack_time, (package.deadline - arrival_time)) # update the slack time
                    base_route.append(package) # add the package to the base route
                    current_location = package.address_w_zip
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
        
        for package in unprioritized_packages:
            previous_stop = starting_point
            time_prev_stop_to_package = None

            # Check each possible insertion point in the route
            for i, stop in enumerate(base_route):
                # Calculate travel time from previous stop to package (only once per package)
                if time_prev_stop_to_package is None:
                    if isinstance(starting_point, str):
                        time_prev_stop_to_package = self.get_travel_time("HUB", package.address_w_zip)
                    elif isinstance(starting_point, Package):
                        time_prev_stop_to_package = self.get_travel_time(previous_stop.address_w_zip, package.address_w_zip)

                # Calculate travel time from package to next stop
                time_package_to_next_stop = self.get_travel_time(package.address_w_zip, stop.address_w_zip)
                # Total additional time if package is inserted here
                time_added = time_prev_stop_to_package + time_package_to_next_stop

                # Check if insertion is feasible within slack time
                if time_added <= slack_time:
                    # Check if insertion is beneficial (reduces total route time)
                    should_insert = True
                    if isinstance(previous_stop, Package):
                        # Compare with original direct route time
                        original_time = self.get_travel_time(previous_stop.address_w_zip, stop.address_w_zip)
                        should_insert = time_added < original_time
                    
                    if should_insert:
                        choices.append((time_added, stop.package_id, previous_stop, stop, package))

                # Update for next iteration
                time_prev_stop_to_package = time_package_to_next_stop
                previous_stop = stop
        choices.sort(key=lambda x: x[0], reverse=True)
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
            travel_time, counter, prev_stop, next_stop, package = insertion_heap.pop()

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
            remaining_packages.remove(package)
            inserted_packages.add(package)
            
            # Check for new feasible insertions after this insertion
            if insert_idx + 1 < len(base_route):
                new_inserts = self.find_all_feasible_insertions(
                    starting_point=package, base_route=base_route,
                    unprioritized_packages=remaining_packages, slack_time=slack_time)

                for insertion in new_inserts:
                    if insertion[4] not in inserted_packages:  # package not already inserted
                        insertion_heap.append(insertion)
                insertion_heap.sort(key=lambda x: x[0], reverse=True)
                        
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
        Builds a regular route using nearest neighbor algorithm
        
        :param route: The route to build
        :param packages_not_in_route: Packages not yet in the route
        :param current_stop: Current location
        :return: Completed route
        """
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
                stop_address = stop.address_w_zip
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

    def get_nearest_neighbor(self, packages: list[Package], current_location: str) -> Package | None:
        """
        Finds the nearest neighbor package from current location
        
        :param packages: List of packages to search
        :param current_location: Current location
        :return: Nearest package or None if no packages
        """
        if not packages:
            return None
            
        nearest_neighbor = min(packages, key=lambda pkg: self.distance_map.get_distance(current_location, pkg.address_w_zip)) 
        return nearest_neighbor

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
            nearest = min(to_visit, key=lambda pkg: self.get_travel_time(current, pkg.address_w_zip))
            route.append(nearest)
            current = nearest.address_w_zip
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

            # Insert siblings of deadline packages into the prioritized route
            for index, stop in enumerate(prioritized_route):
                siblings = getattr(stop, 'packages_at_same_address', [])
                if siblings:
                    for sid in siblings:
                        sibling = self.packages[sid]
                        # If sibling is in regular packages, insert it right after the deadline package
                        if sibling and sibling in regular_packages:
                            prioritized_route.insert(index+1, sibling)
                            regular_packages.remove(sibling)

            # add the packages that have potential to be fit in between the expedited packages
            potential_package_insertions = self.find_all_feasible_insertions("HUB", prioritized_route,
                                                                             regular_packages, slack_time)

            base_route, new_slack_time, packages_not_in_route = (self.insert_best_feasible_packages
                                                                 (prioritized_route, potential_package_insertions,
                                                                  regular_packages, slack_time))

            current_stop = base_route[-1]

            completed_route = self.build_regular_route(route=base_route, packages_not_in_route=packages_not_in_route,
                                                       current_stop=current_stop)
        # if there are no deadline packages, build the route using only regular packages
        else:
            completed_route = self.build_regular_route(route=[], packages_not_in_route=regular_packages,
                                                       current_stop="HUB")

        completed_time, miles_travelled = self.get_mock_completion_time_and_distance(completed_route, current_time, current_location)

        return completed_route, completed_time, miles_travelled, dispatched_packages

    def build_route(self, route_id: int, current_time: datetime, dispatched_packages: set) -> tuple[list[Package], datetime, float, set[int]]:
        """
        Builds a route for a truck
        
        :param route_id: The ID of the truck
        :param current_time: The current time
        :param dispatched_packages: The packages that have been dispatched
        :return: The completed route, the completion time, the miles travelled, and the dispatched packages
        """
        priority_queue = self.get_priority_queue(current_time, dispatched_packages, route_id)
        priorities = self.select_packages_by_priority(priority_queue, current_time, dispatched_packages, 16)
        final_route, final_time, final_miles_travelled, final_dispatched_packages = self.sort_packages(priorities, current_time, dispatched_packages)

        return final_route, final_time, final_miles_travelled, final_dispatched_packages

