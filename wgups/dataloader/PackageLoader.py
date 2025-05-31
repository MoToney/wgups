import re

from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.Package import Package, PackageStatus
from datetime import datetime
from typing import Optional


class PackageLoader(object):

    @staticmethod
    def load_from_file(file: str, package_hash_map: PackageHashMap) -> Optional[PackageHashMap]:
        import csv
        with open(file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            next(reader)
            for row in reader:
                if row:
                    package_hash_map.add_package(PackageLoader.csv_to_package(row=row))
            return package_hash_map

    @staticmethod
    def csv_to_package(row: list[str]) -> Package:
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

        if "grouped_packages" in special_notes:
            package.must_be_delivered_with = special_notes["grouped_packages"]

        if "available_time" in special_notes:
            package.available_time = special_notes["available_time"]

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
                time_obj = datetime.strptime(match.group(), '%I:%M %p').time()
                parsed["available_time"] = time_obj

        if "must be delivered with" in note_str:
            match = re.findall(r'\d+', note_str)
            if match:
                parsed["grouped_packages"] = list(map(int, match))

        if "wrong address" in note_str:
            parsed["wrong_address"] = True

        return parsed


# test


