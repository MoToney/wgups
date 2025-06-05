import csv
from datetime import datetime, time

from wgups.Routing import Routing
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap


packages = PackageLoader("data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
distances = DistanceMap("data/distances.csv")
routing = Routing(distances)
availables = routing.get_available_packages(packages, set(),
                                            datetime(1900, 1, 1, 8, 0), 2)
distance=0
visited = set()
route_id = 1
time = datetime(1900,1,1,8,0)

while route_id < 4:
    route, group_map, visited_ids, end_time, dist, availables = routing.build_route(route_id=route_id, start="HUB", packages=packages, visited_ids=visited,
                                current_time=time, max_capacity=16)
    time = end_time
    distance += dist
    print(time)
    print(route)
    route_id += 1
print(distance)

if __name__ == '__main__':
    main()

