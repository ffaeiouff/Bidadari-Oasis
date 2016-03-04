from bs4 import BeautifulSoup
from datetime import datetime
import requests, time, json, csv, os, random

def new_payload(block, flat_type, contract):
    return {
        "Flat": flat_type,
        "Block": block,
        "Contract": contract,
        "Town": "Toa Payoh",
        "Flat_Type": "BTO",
        "ethnic": "Y",
        "ViewOption": "A",
        "projName": "A",
        "DesType": "A",
        "EthnicA": "Y",
        "EthnicM": "",
        "EthnicC": "",
        "EthnicO": "",
        "numSPR": "",
        "dteBallot": "201511",
        "Neighbourhood": "N9",
        "BonusFlats1": "N",
        "searchDetails": "",
        "isTownChange": "No",
        "brochure": "false"
    }

class Unit:
    def __init__(self, unit_no, booked, cost="", size=""):
        self.unit_no = unit_no
        self.booked = booked
        self.cost = cost
        self.size = size
        self.floor, self.stack = unit_no[1:].split('-')

    def update(self, block, flat_type):
        self.block = block
        self.flat_type = flat_type

    def sort_key(self):
        return [self.block, self.flat_type, self.stack, self.floor]

    def row(self):
        status = 'booked' if self.booked else 'available'
        return [self.block, self.flat_type, self.unit_no, self.floor, self.stack, status, self.size, self.cost]

    @staticmethod
    def row_header():
        return ['block', 'flat_type', 'unit_no', 'floor', 'stack', 'status', 'size', 'cost']

    def __repr__(self):
        return json.dumps(self.__dict__)

def unit_from_soup(soup):
  # Unbooked
  if soup.find('a'):
      u = soup.find('font')
      unit_no = u.get('id')
      cost, _, size = u.get('title').replace('\xa0',' ').split('<br/>')
      return Unit(unit_no, False, cost, size)
  else:
      unit_no = soup.find('font').text.strip()
      return Unit(unit_no, True)

def parse(html):
    soup = BeautifulSoup(html, 'html.parser')

    block_details = soup.find(id='blockDetails')
    unit_details = block_details.find_all(class_='row')[4].find_all('td')

    return [unit_from_soup(unit) for unit in unit_details]

def fetch(s, url, payload):
    return s.get(url, params=payload)

def fetch_and_parse(s, url, payload):
    r = fetch(s, url, payload)
    units = parse(r.text)
    return units

def write_json(filename, all_units):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w') as out:
        out.write(str(all_units))

def write_csv(filename, all_units):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    rows = [unit.row() for unit in all_units]
    with open(filename, 'w', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(Unit.row_header())
        writer.writerows(rows)

def write_stats(filename, all_units, stats, expected_count):
    flat_type_count = {
        "2-Room Flexi (Short Lease/99-Year Lease)": 0,
        "3-Room": 0,
        "4-Room": 0,
        "5-Room": 0
    }

    for block, flat_types in stats.items():
        for flat_type, count in flat_types.items():
            flat_type_count[flat_type] += count

    with open(filename, 'w') as out:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        out.write("Time: {}\n".format(timestamp))

        if tuple(flat_type_count.items()) == tuple(expected_count.items()):
            out.write("###OK###\n")

        out.write("Health check\n")
        out.write("\tRetrieved: {}\n".format(flat_type_count))
        out.write("\tExpected: {}\n".format(expected_count))

        if tuple(flat_type_count.items()) != tuple(expected_count.items()):
            out.write("\n\tTotal retrieved flats did not match expected count.\n")
            return
        else:
            out.write("\n\tData should be healthy\n")

        out.write("\nTake up percentage\n")
        flat_types = sorted(expected_count.keys())

        for flat_type in flat_types:
            available = expected_count[flat_type]
            booked = len(list(filter(lambda unit: unit.flat_type == flat_type and unit.booked, all_units)))
            out.write("\t{}: {}/{} = {:.2f}%\n".format(flat_type, booked, available, (booked / available)*100))

if __name__ == "__main__":
    url = "http://services2.hdb.gov.sg/webapp/BP13AWFlatAvail/BP13EBSFlatSearch"

    blocks_and_flat_types = {
        "101A": ["2-Room Flexi (Short Lease/99-Year Lease)", "3-Room", "4-Room"],
        "102A": ["2-Room Flexi (Short Lease/99-Year Lease)", "4-Room"],
        "102B": ["3-Room", "4-Room"],
        "103A": ["3-Room", "4-Room"],
        "103B": ["3-Room", "4-Room"],
        "104A": ["2-Room Flexi (Short Lease/99-Year Lease)", "3-Room", "4-Room"],
        "105A": ["4-Room", "5-Room"],
        "105B": ["4-Room", "5-Room"],
        "106A": ["4-Room", "5-Room"],
        "106B": ["4-Room", "5-Room"],
        "115A": ["3-Room", "4-Room"],
        "115C": ["3-Room", "4-Room"],
        "118A": ["3-Room", "4-Room"]
    }
    contracts = {
        "101A": "C1",
        "102A": "C1",
        "102B": "C1",
        "103A": "C1",
        "103B": "C1",
        "104A": "C1",
        "105A": "C4",
        "105B": "C4",
        "106A": "C4",
        "106B": "C4",
        "115A": "C3",
        "115C": "C3",
        "118A": "C3"
    }

    expected_count = {
        "2-Room Flexi (Short Lease/99-Year Lease)": 192,
        "3-Room": 567,
        "4-Room": 1229,
        "5-Room": 151
    }

    s = requests.Session()
    # Need to make an initial request to grab the cookies
    s.get("http://services2.hdb.gov.sg/webapp/BP13AWFlatAvail/BP13EBSFlatSearch?Town=Toa%20Payoh&Flat_Type=BTO&DesType=A&ethnic=Y&Flat=4-Room&ViewOption=A&dteBallot=201511&projName=A&brochure=false")

    stats = {}
    all_units = []
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    for block, flat_types in blocks_and_flat_types.items():
        stats[block] = {}
        contract = contracts[block]

        for flat_type in flat_types:
            payload = new_payload(block, flat_type, contract)

            print("Fetching {} {}".format(block, flat_type))
            units = fetch_and_parse(s, url, payload)
            print("\tFound {} units".format(len(units)))

            stats[block][flat_type] = len(units)

            for i, unit in enumerate(units):
                unit.update(block, flat_type)
                units[i] = unit

            all_units.extend(units)
            time.sleep(random.uniform(0, 3))

    all_units = sorted(all_units, key=lambda unit: unit.sort_key())

    write_json("data/bidadari.json", all_units)
    write_csv("data/bidadari.csv", all_units)
    write_stats("data/bidadari.log", all_units, stats, expected_count)
