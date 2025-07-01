from wgups.Package import Package, TruckCarrier
from collections import deque
from typing import List, Optional

import csv
from datetime import datetime, time, timedelta

from wgups.Routing import Routing
from wgups.SimulationClock import SimulationClock
from wgups.Package import TruckCarrier, PackageStatus
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap


class Truck:
    """
    A class representing a truck in the WGUPS simulation.
    
    The truck manages package loading, delivery, and route execution.
    It tracks its location, distance traveled, and delivery status.
    """
    def __init__(self, truck_id: int = 0, distance_map: Optional[DistanceMap] = None, clock: Optional[SimulationClock] = None):
        """
        Initializes a Truck object.
        
        :param truck_id: The ID of the truck (1, 2, or 3)
        :param distance_map: The distance map for calculating travel times
        :param clock: The simulation clock for scheduling events
        """
        self.packages_in_truck = [] # Queue of packages to be delivered
        self.delivery_log = []  # List of delivered packages for tracking
        self.truck_id = truck_id
        self.CAPACITY = 16
        self.SPEED = 18.0
        self.distance_map = distance_map
        self.clock = clock
        self.location = 'HUB'  # Current location, starts at HUB
        self.distance_travelled = 0.0  # Total distance traveled in miles

    def load_packages(self, packages: List[Package]) -> list:
        """
        Loads packages onto the truck and schedules the first delivery.
        
        This method marks packages as in route, assigns them to the specific truck,
        sets their departure time, and schedules the delivery sequence.
        
        :param packages: List of packages to load onto the truck
        :return: The queue of packages now on the truck
        """
        for package in packages:
            package.set_status(PackageStatus.IN_ROUTE)
            # Assign package to specific truck (affects delivery tracking)
            if self.truck_id == 1:
                package.truck_carrier = TruckCarrier.TRUCK_1
            elif self.truck_id == 2:
                package.truck_carrier = TruckCarrier.TRUCK_2
            elif self.truck_id == 3:
                package.truck_carrier = TruckCarrier.TRUCK_3
            else:
                print("Invalid Truck ID")
                break
            package.set_departure_time(self.clock.now())  # Record when truck left HUB
            self.packages_in_truck.append(package)

        # Schedule the first delivery to start the delivery sequence
        self.clock.schedule_event(self.clock.now(), self.deliver_package, 0)
        return self.packages_in_truck

    def add_package(self, package: Package) -> None:
        """
        Adds a single package to the truck without starting delivery.
        
        This is used for adding packages to an already loaded truck.
        
        :param package: The package to add to the truck
        """
        package.set_status(PackageStatus.IN_ROUTE)
        # Assign package to specific truck (affects delivery tracking)
        if self.truck_id == 1:
            package.set_truck(TruckCarrier.TRUCK_1)
        elif self.truck_id == 2:
            package.set_truck(TruckCarrier.TRUCK_2)
        elif self.truck_id == 3:
            package.set_truck(TruckCarrier.TRUCK_3)
        else:
            print("Invalid Truck ID")
        self.packages_in_truck.append(package)

    def deliver_package(self, index: int = 0) -> None:
        """
        Delivers a package at the specified index and schedules the next delivery.
        
        This method calculates travel time, updates truck location and distance,
        marks the package as delivered, and schedules the next delivery.
        If all packages are delivered, it schedules return to HUB.
        
        :param index: Index of the package to deliver in the truck's package queue
        """
        # Check if all packages have been delivered
        if index >= len(self.packages_in_truck):
            self.packages_in_truck.clear()  # Clear the package list
            print(f"Truck {self.truck_id} delivered all packages in route at {self.clock.now().strftime('%H:%M')} and drives to HUB")
            # Schedule return to HUB after all deliveries complete
            self.clock.schedule_event(self.clock.now(), self.return_to_hub)
            return

        package = self.packages_in_truck[index]
        # Calculate distance and travel time to package destination
        dist = self.distance_map.get_distance(self.location, package.address_w_zip)
        self.distance_travelled += dist
        travel_time = timedelta(hours=dist / 18.0)  # 18 mph average speed
        delivery_time = self.clock.now() + travel_time
        self.location = package.address_w_zip  # Update truck location

        # Mark package as delivered and record delivery time
        package.set_status(PackageStatus.DELIVERED)
        package.set_delivery_time(delivery_time)
        
        # Check if package missed its deadline
        if package.deadline and package.delivery_time > package.deadline:
            print(f"Package: {package.package_id} missed Deadline: {package.deadline.time()} it was Delivered at: {package.delivery_time.time()}")
        
        self.delivery_log.append((delivery_time, self.distance_travelled, str(package), self.location))  # Add to delivery log for tracking

        # Schedule the next delivery at the computed delivery time
        self.clock.schedule_event(
            delivery_time,
            self.deliver_package, index + 1
        )
        print(
            f"[{delivery_time.strftime('%H:%M')}] (scheduled) Truck {self.truck_id} delivered package {package.package_id} to {package.address_w_zip}")

    def return_to_hub(self) -> str:
        """
        Returns the truck to the HUB after completing all deliveries.
        
        Calculates travel time and distance back to HUB, updates truck location,
        and schedules the return journey.
        
        :return: Status message indicating truck location
        """
        if self.location == 'HUB':
            return "truck is already at HUB"
        
        # Calculate distance and travel time back to HUB
        dist = self.distance_map.get_distance('HUB', self.location)
        travel_time = timedelta(hours=dist / 18.0)  # 18 mph average speed
        finish_time = self.clock.now() + travel_time
        self.distance_travelled += dist
        self.location = 'HUB'  # Update truck location to HUB

        self.delivery_log.append(
            (finish_time, self.distance_travelled, "HUB", self.location))  # Add to delivery log for tracking
        
        print(f"[{finish_time.strftime('%H:%M')}] (scheduled) Truck {self.truck_id} returns to HUB")
        return "truck is now at HUB"

    def test_packages_in_truck(self) -> None:
        """
        Prints all packages currently loaded on the truck for debugging purposes.
        """
        print_list = [str(package) for package in self.packages_in_truck]
        print(print_list)

'''packies = PackageLoader("../data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
clock = SimulationClock(datetime(1900,1,1,8,0))
disties = DistanceMap("../data/distances.csv")
routing = Routing(disties, packies, clock)
"""global_clock = TimeManager(datetime.strptime("8:00 AM", "%I:%M %p"))
current_clock = global_clock.current_time
clockies = current_tha_time = datetime(1900,1,1,8,0)
route, final_time, visited_ids = routing.build_route(1, clockies, set())

package_list = []

for stop in route:
    package_list.append(packies.packages_table[int(stop.package_id)])

truck = Truck(1, 16, disties, global_clock)
truck.load_packages(package_list)
truck.drive()
"""

CAPACITY = 16

routing = Routing(disties, packies, clock)
clock.schedule_event(datetime(1900,1,1,9,5), routing.make_available, 6)
clock.schedule_event(datetime(1900,1,1,10,20), routing.update_address, 9)

start_time = datetime(1900,1,1,8,0)
clock.run_until(start_time)
route2, time2, miles2, vis2 = routing.build_route(2, start_time, set({1, 8, 13, 14, 15, 16, 19, 20, 21, 29, 30, 31, 34, 37, 39, 40}))
truck2 = Truck(2, CAPACITY, disties, clock)
clock.schedule_event(start_time, truck2.load_packages, route2)
print(miles2, time2, len(route2), end="\n\n")

clock.run_until(datetime(1900,1,1,17,0))
print(truck2.distance_travelled)'''

