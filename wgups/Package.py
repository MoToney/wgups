'''
a.	Has a status to see if delivered, in route, or at hub
b.	Has a specific truck
c.	Has a specific time ready
d.	40 packages in total
e.	Gets loaded into the truck
f.	Gets loaded into the data structure containing all packages

'''

from enum import Enum
from datetime import datetime
from typing import Optional

class PackageStatus(Enum):
    """
    returns the status of the package throughout the delivery cycle
    """
    NOT_READY = 0
    AT_HUB = 1
    IN_ROUTE = 2
    DELIVERED = 3

class TruckCarrier(Enum):
    """
    returns the truck that is associated with the object
    """
    NEITHER = 0
    TRUCK_1 = 1
    TRUCK_2 = 2
    TRUCK_3 = 3

class Package:
    """
    represents a package that will be delivered to an address via a truck object
    """
    def __init__(self, package_id: int = 0, address: str = None, city: str = None, zip_code: str = None,
                 state: str = "Utah",
                 deadline: datetime = None, weight:float = None, note: dict = None,
                 status: PackageStatus = PackageStatus.NOT_READY
                 ):
        """
        constructor which takes several package characteristics as parameters


        :param package_id: id of the package
        :param address: the street and house number of the package
        :param city: the city of the package
        :param zip_code: the zip code of the package
        :param state: the state of the package
        :param deadline: the time the package must be delivered by
        :param weight: the weight of the package
        :param note: the note of the package, denoting special handling guidelines
        :param status: the status of the package, which is a phase in the PackageStatus Enum

        :keyword state: set to the State of Utah by default
        :keyword status: set to Not Ready by default
        """

        self.package_id = package_id
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.deadline = deadline
        self.weight = weight
        self.special_note = note
        self.status = status

        self.address_w_zip = self.get_address_w_zip() # this is for standardization with the addresses in distances.csv

        self.must_be_delivered_with: Optional[list[int]] = None # stores the ids of packages that must be delivered at the same time as the package
        self.available_time: Optional[datetime] = None
        self.required_truck: Optional[int] = None
        self.wrong_address: Optional[bool] = False

        self.packages_at_same_address: Optional[Package] = None

        self.delivery_time = None
        self.departure_time = None
        self.truck_carrier = TruckCarrier.NEITHER

    def set_status(self, status):
        # manually set status
        self.status = status
    def mark_not_ready(self):
        self.status = PackageStatus.NOT_READY
    def mark_at_hub(self):
        self.status = PackageStatus.AT_HUB
    def mark_in_route(self):
        self.status = PackageStatus.IN_ROUTE
    def mark_delivered(self):
        self.status = PackageStatus.DELIVERED

    def on_truck1(self):
        self.truck_carrier = TruckCarrier.TRUCK_1
    def on_truck2(self):
        self.truck_carrier = TruckCarrier.TRUCK_2
    def on_truck3(self):
        self.truck_carrier = TruckCarrier.TRUCK_3

    def get_truck_carrier(self):
        if self.truck_carrier == TruckCarrier.TRUCK_1:
            return "Truck 1"
        elif self.truck_carrier == TruckCarrier.TRUCK_2:
            return "Truck 2"
        elif self.truck_carrier == TruckCarrier.TRUCK_3:
            return "Truck 3"
        return self.truck_carrier

    def set_delivery_time(self, delivery_time: datetime.time):
        self.delivery_time = delivery_time

    def set_departure_time(self, departure_time: datetime.time):
        self.departure_time = departure_time

    def get_address_w_zip(self):
        """returns address that is usable when referencing the listed address for the Package in DistanceMap"""
        address_w_zip = (f"{self.address}({self.zip_code})")
        return address_w_zip

    def set_address_w_zip(self, address_w_zip):
        self.address_w_zip = address_w_zip

    def set_full_address(self, address, city, state, zip_code):
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code


    def get_siblings(self):
        return self.packages_at_same_address

    def set_packages_at_same_address(self, other_packages):
        self.packages_at_same_address = other_packages

    def __str__(self):
        return (f"Package {self.package_id}: | "
                f"Address: {self.address}, {self.city}, {self.state}, {self.zip_code} | "
                f"Deadline: {self.deadline.strftime('%I:%M %p') if self.deadline else 'EOD'} | "
                f"Weight: {self.weight} | "
                f"Status: {self.status.name.replace('_', ' ').title()} | "
                f"Delivery Time: {self.delivery_time} | "
                f"Note: {self.special_note}")



"""package = Package(2, "2510 South Vernice Drive", "Copperas Cove", "76522", "Utah", deadline=datetime.now(), weight=3.0,
                  note="",status=PackageStatus.NOT_READY)
print(package)"""
