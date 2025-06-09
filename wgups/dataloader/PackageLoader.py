import re
from collections import defaultdict

from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.Package import Package, PackageStatus
from datetime import datetime
from typing import Optional


class PackageLoader:
    def __init__(self, file:str, package_hash_map:PackageHashMap):
        self.file = file
        self.package_hash_map = package_hash_map
        self.address_dict = defaultdict(list)

        self.load_from_file()
        self.build_groups()
        self.build_shared_addresses()


    def load_from_file(self) -> Optional[PackageHashMap]:
        import csv
        with open(self.file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            next(reader)
            for row in reader:
                if row:
                    self.package_hash_map.add_package(self.csv_to_package(row=row))
            return self.package_hash_map

    def csv_to_package(self, row: list[str]) -> Package:
        package_id = int(row[0])
        address = row[1]
        city = row[2]
        state = row[3]
        zip_code = row[4]
        deadline = PackageLoader.parse_deadline(row[5])
        weight = float(row[6])
        special_notes = PackageLoader.parse_note(row[7])
        status = PackageStatus.NOT_READY

        package = Package(
            package_id=package_id, address=address, city=city, state=state, zip_code=zip_code,
            deadline=deadline, weight=weight, note=special_notes, status=status)

        self.address_dict[address].append(package_id)

        if "grouped_packages" in special_notes:
            package.must_be_delivered_with = special_notes["grouped_packages"]

        if "available_time" in special_notes:
            package.available_time = special_notes["available_time"]
        else:
            package.status = PackageStatus.AT_HUB

        if "required_truck" in special_notes:
            package.required_truck = special_notes["required_truck"]

        if "wrong_address" in special_notes:
            package.wrong_address = True
            package.status = PackageStatus.NOT_READY

        return package

    @staticmethod
    def parse_deadline(deadline_str) -> Optional[datetime]:
        if deadline_str.strip().upper() == 'EOD':
            return None

        try:
            return datetime.strptime(deadline_str.strip(), '%I:%M %p')
        except ValueError:
            raise ValueError('Invalid deadline string')

    @staticmethod
    def parse_note(note_str):
        note_str = note_str.lower()
        parsed = {}

        if "truck" in note_str:
            match = re.search(r'truck\s*(\d+)', note_str)
            if match:
                parsed["required_truck"] = int(match.group(1))

        if "delayed" in note_str:
            match = re.search(r'\b\d{1,2}:\d{2}\s*(?:am|pm)\b', note_str)
            if match:
                time_obj = datetime.strptime(match.group(), '%I:%M %p')
                parsed["available_time"] = time_obj

        if "must be delivered with" in note_str:
            match = re.findall(r'\d+', note_str)
            if match:
                parsed["grouped_packages"] = list(map(int, match))

        if "wrong address" in note_str:
            parsed["wrong_address"] = True

        return parsed

    def get_map(self) -> PackageHashMap:
        return self.package_hash_map

    def build_groups(self):
        groups = []
        for package in self.package_hash_map.packages_table:
            if not isinstance(package, Package):
                continue

            if package.must_be_delivered_with:
                new_group = set([package.package_id] + package.must_be_delivered_with)

                merged = []

                for group in groups:
                    if not group.isdisjoint(new_group):
                        new_group.update(group)
                    else:
                        merged.append(group)
                merged.append(new_group)
                groups = merged
        for group in groups:
            for member in group:
                package = self.package_hash_map.search_package(member)
                package.must_be_delivered_with = group

    def build_shared_addresses(self):
        visited = set()
        for package in self.package_hash_map.packages_table:
            if not isinstance(package, Package):
                continue
            if package.address in visited:
                continue
            if package.address in self.address_dict.keys():
                if len(self.address_dict[package.address]) == 1:
                    visited.add(package.address)
                    continue
                if len(self.address_dict[package.address]) > 1:
                    print(f"{package} shares address with {self.address_dict[package.address]}multiple addresses")
                    package.set_packages_at_same_address(self.address_dict[package.address])
                    for pid in self.address_dict[package.address]:
                        other_package = self.package_hash_map.search_package(pid)
                        other_package.set_packages_at_same_address(self.address_dict[other_package.address])
                    visited.add(package.address)





# test


