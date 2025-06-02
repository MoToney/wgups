from wgups.Package import Package


class Truck:
    def __init__(self, truck_id:int = 0, capacity:int = 16, packages_in_truck=None, location:str = None):
        if packages_in_truck is None:
            packages_in_truck = []
        self.truck_id = truck_id
        self.capacity = capacity
        self.packages_in_truck = packages_in_truck
        self.location = location

    def load_package(self, package:Package):
        pass

    def load_packages(self, packages:list):
        pass

