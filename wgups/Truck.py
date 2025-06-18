from wgups.Package import Package
from collections import deque

import csv
from datetime import datetime, time, timedelta

from wgups.Routing import Routing
from wgups.SimulationClock import SimulationClock
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap


class Truck:
    def __init__(self, truck_id:int = 0, capacity:int = 16, distance_map:DistanceMap = None, clock:SimulationClock = None):
        self.packages_in_truck = deque()
        self.truck_id = truck_id
        self.capacity = capacity
        self.distance_map = distance_map
        self.clock = clock
        self.location = 'HUB'
        self.distance_travelled = 0.0
        self.delivery_log = []

    def load_packages(self, packages):
        for package in packages:
            package.mark_in_route()
            if self.truck_id == 1:
                package.on_truck1()
            elif self.truck_id == 2:
                package.on_truck2()
            elif self.truck_id == 3:
                package.on_truck3()
            else:
                print("Invalid Truck ID")
                break
            package.set_departure_time(self.clock.now())
            self.packages_in_truck.append(package)

        self.clock.schedule_event(self.clock.now(), self.deliver_package, 0)
        return self.packages_in_truck

    def add_package(self, package:Package):
        if self.truck_id == 1:
            package.on_truck1()
        elif self.truck_id == 2:
            package.on_truck2()
        elif self.truck_id == 3:
            package.on_truck3()
        else:
            print("Invalid Truck ID")
        self.packages_in_truck.append(package)

    def deliver_package(self, index=0):
        if index >= len(self.packages_in_truck):
            self.packages_in_truck.clear()
            print(f"Truck {self.truck_id} delivered all packages in route at {self.clock.now().strftime('%H:%M')} and drives to HUB")
            self.clock.schedule_event(self.clock.now(),
                                      self.return_to_hub)
            return

        package = self.packages_in_truck[index]
        dist = self.distance_map.get_distance(self.location, package.address_w_zip)
        self.distance_travelled += dist
        travel_time = timedelta(hours=dist / 18.0)
        delivery_time = self.clock.now() + travel_time
        self.location = package.address_w_zip

        package.mark_delivered()
        package.set_delivery_time(delivery_time)
        if package.deadline and package.delivery_time > package.deadline:
            print(f"Package: {package.package_id} missed Deadline: {package.deadline.time()} it was Delivered at: {package.delivery_time.time()}")
        self.delivery_log.append(package)

        # Schedule the actual delivery event at the computed time
        self.clock.schedule_event(
            delivery_time,
            self.deliver_package, index + 1
        )
        print(
            f"[{delivery_time.strftime('%H:%M')}] (scheduled) Truck {self.truck_id} delivered package {package.package_id} to {package.address_w_zip}")

    def return_to_hub(self):
        if self.location == 'HUB':
            return "truck is already at HUB"
        dist = self.distance_map.get_distance('HUB', self.location)
        travel_time = timedelta(hours=dist / 18.0)
        finish_time = self.clock.now() + travel_time
        self.distance_travelled += dist
        self.location = 'HUB'
        print(
            f"[{finish_time.strftime('%H:%M')}] (scheduled) Truck {self.truck_id} returns to HUB")
        return "truck is now at HUB"

    def test_packages_in_truck(self):
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

