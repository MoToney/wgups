import re
from collections import defaultdict

from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.Package import Package, PackageStatus
from datetime import datetime
from typing import Optional


class PackageLoader:
    """
    This class is used to load the packages from the csv file and build the groups and shared addresses.
    It also has methods to parse the deadline and note from the csv file.
    It also has methods to build the groups and shared addresses.
    It also has methods to get the map of the packages.
    It also has methods to build the groups and shared addresses.
    """
    def __init__(self, file:str, package_hash_map:PackageHashMap):
        """
        Initializes the PackageLoader class.
        """
        self.file = file
        self.package_hash_map = package_hash_map # the hash map of the packages

        self.address_groups = []

        self.load_from_file() # loads the packages from the csv file
        self.build_groups() # builds the groups of packages
        self.build_shared_addresses() # builds the shared addresses of packages


    def load_from_file(self) -> Optional[PackageHashMap]:
        """
        Loads the packages from the csv file.
        """
        import csv
        with open(self.file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            next(reader)
            for row in reader:
                if row:
                    self.package_hash_map.add_package(self.csv_to_package(row=row)) # adds the package to the hash map
            return self.package_hash_map

    def csv_to_package(self, row: list[str]) -> Package:
        """
        Converts a row from the csv file to a package.
        """
        package_id = int(row[0])
        address = row[1]
        city = row[2]
        state = row[3]
        zip_code = row[4]
        deadline = self.parse_deadline(row[5]) # parses the deadline from the csv file and returns a datetime object
        weight = float(row[6]) 
        required_truck, available_time, grouped_packages, wrong_address = self.parse_note(row[7])
        status = PackageStatus.NOT_READY # sets the status of the package to not ready

        package = Package(
            package_id=package_id, address=address, city=city, state=state, zip_code=zip_code,
            deadline=deadline, weight=weight, note=row[7], status=status) # creates a package object

        self.add_address_group(address, package_id) # adds the package id to the address dictionary

        # Set parsed note attributes
        if grouped_packages is not None:
            package.must_be_delivered_with = grouped_packages

        if available_time is not None:
            package.available_time = available_time
        else:
            package.status = PackageStatus.AT_HUB

        if required_truck is not None:
            package.required_truck = required_truck

        if wrong_address:
            package.wrong_address = True
            package.status = PackageStatus.NOT_READY

        return package

    def parse_deadline(self, deadline_str:str) -> Optional[datetime]:
        """
        Parses the deadline from the csv file and returns a datetime object.
        """
        # if the deadline is EOD, return None
        if deadline_str.strip().upper() == 'EOD':
            return None
        
        # if the deadline is not EOD, parse the deadline and return a datetime object
        try:
            return datetime.strptime(deadline_str.strip(), '%I:%M %p')
        except ValueError:
            raise ValueError('Invalid deadline string')

    def parse_note(self, note_str:str):
        """
        Parses the note from the csv file and returns a dictionary.
        """
        note_str = note_str.lower() # converts the note to lowercase
        required_truck = None
        available_time = None
        grouped_packages = None
        wrong_address = False

        # if the note contains the word "truck", parse the truck number and add it to the dictionary
        if "truck" in note_str:
            match = re.search(r'truck\s*(\d+)', note_str)
            if match:
                required_truck = int(match.group(1))

        # if the note contains the word "delayed", parse the time and add it to the dictionary
        if "delayed" in note_str:
            match = re.search(r'\b\d{1,2}:\d{2}\s*(?:am|pm)\b', note_str)
            if match:
                time_obj = datetime.strptime(match.group(), '%I:%M %p')
                available_time = time_obj

        # if the note contains the word "must be delivered with", parse the package ids and add them to the dictionary
        if "must be delivered with" in note_str:
            match = re.findall(r'\d+', note_str)
            if match:
                grouped_packages = list(map(int, match))

        # if the note contains the word "wrong address", set the wrong address to true
        if "wrong address" in note_str:
            wrong_address = True

        return required_truck, available_time, grouped_packages, wrong_address

    def get_map(self) -> PackageHashMap:
        """
        Returns the hash map of the packages.
        """
        return self.package_hash_map

    def build_groups(self) -> None:
        """
        Builds the groups of packages.
        """
        groups = []
        for package in self.package_hash_map.packages_table:
            if not isinstance(package, Package):
                continue
            # if the package is grouped, add the package id to the must be delivered with list
            if package.must_be_delivered_with:
                new_group = set([package.package_id] + package.must_be_delivered_with) # creates a new group with the package id and the package ids in the must be delivered with list

                merged = []

                for group in groups:
                    # if the group does not have any packages in common with the new group, add the group to the merged list
                    if not group.isdisjoint(new_group):
                        new_group.update(group) # update the new group with the group
                    # if the group has packages in common with the new group, update the new group with the group
                    else:
                        merged.append(group)
                merged.append(new_group) # add the new group to the merged list
                groups = merged
        # for each group, set the must be delivered with list to the group 
        for group in groups:
            # for each package in the group, set the must be delivered with list to the group
            for member_id in group:
                package = self.package_hash_map[member_id]
                package.must_be_delivered_with = group

    def add_address_group(self, address, package_id):
        for pair in self.address_groups:
            if pair[0] == address:
                pair[1].append(package_id)
                return
            # If address not found, add new
        self.address_groups.append([address, [package_id]])

    def get_package_ids_for_address(self, address):
        for pair in self.address_groups:
            if pair[0] == address:
                return pair[1]
        return []

    def build_shared_addresses(self):
        """
        Builds the shared addresses of packages.
        """
        visited = set() # initializes an empty set

        # for each package
        for package in self.package_hash_map.packages_table:

            # if the package is not a package, continue
            if not isinstance(package, Package):
                continue

            # if the package has already been visited, continue
            if package.address in visited:
                continue

            # if the package has packages at the same address
            package_ids = self.get_package_ids_for_address(package.address)
            if len(package_ids) == 1:
                visited.add(package.address)
                package.set_packages_at_same_address(None)
                continue

            if len(package_ids) > 1:
                package.set_packages_at_same_address(package_ids)
                for pid in package_ids:
                    other_package = self.package_hash_map.search_package(pid)
                    other_package.set_packages_at_same_address(package_ids)
                visited.add(package.address)