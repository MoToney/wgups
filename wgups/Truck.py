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
        self.current_location = package.address_w_zip

    def return_to_hub(self):
        if self.current_location == 'HUB':
            return "truck is at HUB"
        dist = self.distance_map.get_distance('HUB', self.current_location)
        travel_time = timedelta(hours=dist / 18.0)
        self.clock.advance(travel_time)
        self.distance_travelled += dist
        self.current_location = 'HUB'

    def drive(self):
        self.test_packages_in_truck()
        for package in self.packages_in_truck:
            self.deliver_package(package)
            self.delivery_log.append(package)
        self.return_to_hub()
        self.packages_in_truck.clear()






    def test_packages_in_truck(self):
        print_list = [str(package) for package in self.packages_in_truck]
        print(print_list)




packages = PackageLoader("../data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
distances = DistanceMap("../data/distances.csv")
routing = Routing(distances)
timely = datetime(1900,1,1,8,0)
availables = routing.get_available_packages(packages, set(),time, 1)
route, group, visited, time1, dist,available = routing.build_route(route_id=1, start="HUB", packages=packages, visited_ids=set(), current_time=timely,
                            max_capacity=16)
global_clock = TimeManager(datetime.strptime("8:00 AM", "%I:%M %p"))
package_list = []
for id, address in route:
    if address == 'HUB':
        continue
    package_list.append(packages.packages_table[int(id)])


truck = Truck(1, 16, distances, global_clock)
truck.load_packages(package_list)
truck.drive()


