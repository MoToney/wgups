import csv
from datetime import datetime, time



string = '10:30 PM'

print(datetime.strptime(string.strip(),'%I:%M %p'))