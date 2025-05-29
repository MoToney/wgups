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

class PackageStatus(Enum):
    NOT_READY = 0
    AT_HUB = 1
    ON_TRUCK1 = 2
    ON_TRUCK2 = 3
    DELIVERED = 4

class Package:
    def __init__(self, package_id:int = 0, address:str = None, city:str =None, zip_code:str =None, state:str ="Utah", deadline:datetime.time =None, weight:float =0, note:str =None, status:PackageStatus =PackageStatus.NOT_READY):
        self.package_id = package_id
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.deadline = deadline
        self.weight = weight
        self.special_note = note
        self.status = status

    def set_status(self, status):
        self.status = status
    def mark_at_hub(self):
        self.status = PackageStatus.AT_HUB
    def mark_truck1(self):
        self.status = PackageStatus.ON_TRUCK1
    def mark_truck2(self):
        self.status = PackageStatus.ON_TRUCK2
    def mark_delivered(self):
        self.status = PackageStatus.DELIVERED
    def set_full_address(self, address, city, state, zip_code):
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code

    @staticmethod
    def parse_deadline(deadline_str):
        if deadline_str.strip().upper() == 'EOD':
            return None
        try:
            return datetime.strptime(deadline_str.strip(), '%H %M %p')
        except ValueError:
            raise ValueError('Invalid deadline string')

    def __str__(self):
        pass




