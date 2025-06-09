from wgups.Package import Package
from collections import deque

import csv
from datetime import datetime, time, timedelta

from wgups.Routing import Routing
from wgups.TimeManager import TimeManager
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap


class Truck:
    def __init__(self, truck_id:int = 0, capacity:int = 16, distance_map:DistanceMap = None, clock:TimeManager = None):
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
            if self.truck_id == 1:
                package.mark_truck1()
            elif self.truck_id == 2:
                package.mark_truck2()
            elif self.truck_id == 3:
                package.mark_truck3()
            else:
                print("Invalid Truck ID")
                break
            self.packages_in_truck.append(package)
        return self.packages_in_truck

    def add_package(self, package:Package):
        if self.truck_id == 1:
            package.mark_truck1()
        elif self.truck_id == 2:
            package.mark_truck2()
        elif self.truck_id == 3:
            package.mark_truck3()
        else:
            print("Invalid Truck ID")
        self.packages_in_truck.append(package)

    def deliver_package(self, package:Package):
        dist = self.distance_map.get_distance(self.location, package.address_w_zip)

        travel_time = timedelta(hours= dist/18.0)
        self.clock.advance(travel_time)

        package.mark_delivered()
        package.set_delivery_time(self.clock.current_time)

        self.distance_travelled += dist
        self.location = package.address_w_zip

    def return_to_hub(self):
        if self.location == 'HUB':
            return "truck is already at HUB"
        dist = self.distance_map.get_distance('HUB', self.location)
        travel_time = timedelta(hours=dist / 18.0)
        self.clock.advance(travel_time)
        self.distance_travelled += dist
        self.location = 'HUB'
        return "truck is now at HUB"

    def drive(self):
        self.test_packages_in_truck()
        for package in self.packages_in_truck:
            self.deliver_package(package)
            if package.deadline and package.delivery_time > package.deadline:
                print(f"{package.package_id, package.delivery_time.time(), package.deadline.time()}Missed deadline")
            print(package.delivery_time.time())
            self.delivery_log.append(package)
        self.return_to_hub()
        self.packages_in_truck.clear()

    def test_packages_in_truck(self):
        print_list = [str(package) for package in self.packages_in_truck]
        print(print_list)

"""packies = PackageLoader("../data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
disties = DistanceMap("../data/distances.csv")
routing = Routing(disties, packies)
global_clock = TimeManager(datetime.strptime("8:00 AM", "%I:%M %p"))
current_clock = global_clock.current_time
clockies = current_tha_time = datetime(1900,1,1,8,0)
route, final_time, visited_ids = routing.build_route(1, clockies, set())

package_list = []

for stop in route:
    package_list.append(packies.packages_table[int(stop.package_id)])

truck = Truck(1, 16, disties, global_clock)
truck.load_packages(package_list)
truck.drive()

route2, second_time, more_visited_ids = routing.build_route(2, final_time, visited_ids)
"""

