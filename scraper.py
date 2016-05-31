from bs4 import BeautifulSoup
from datetime import datetime, timezone
from collections import OrderedDict
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
        "dteBallot": "201602",
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

def unit_from_soup(soup):
  # Unbooked
  if soup.find('a'):
      u = soup.find('font')
      unit_no = u.get('id')
      cost, size = u.get('title').replace('\xa0',' ').replace('<br/>', '\n').split('____________________')
      return Unit(unit_no, False, cost.strip(), size.strip())
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

    unit_json = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "units": all_units
    }

    with open(filename, 'w') as out:
        out.write(json.dumps(unit_json, default=lambda obj: OrderedDict(sorted(obj.__dict__.items()))))

def write_csv(filename, all_units):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    rows = [unit.row() for unit in all_units]
    with open(filename, 'w', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(Unit.row_header())
        writer.writerows(rows)

def flat_stats(flat_type, units):
    available = len(list(filter(lambda unit: unit.flat_type == flat_type, units)))
    booked = len(list(filter(lambda unit: unit.flat_type == flat_type and unit.booked, units)))
    return [booked, available]

def write_stats(filename, all_units, blocks_and_flat_types, expected_count):
    flat_type_count = OrderedDict()

    flat_types = sorted(expected_count.keys())

    with open(filename, 'w') as out:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        out.write("Time: {}\n".format(timestamp))

        out.write("Health check\n")
        for flat_type in flat_types:
            flat_type_count[flat_type] = len(list(filter(lambda unit: unit.flat_type == flat_type, all_units)))

        if tuple(flat_type_count.items()) == tuple(expected_count.items()):
            out.write("###OK###\n")
        else:
            out.write("\n\tTotal retrieved flats did not match expected count.\n")
            out.write("\tRetrieved: {}\n".format(tuple(flat_type_count.items())))
            out.write("\tExpected: {}\n".format(tuple(expected_count.items())))
            return

        out.write("\nCumulative Selected Stats\n")
        for flat_type in flat_types:
            booked, available = flat_stats(flat_type, all_units)
            out.write("\t{}: {}/{} ({:.2f}%) selected\n".format(flat_type, booked, available, (booked / available)*100))

        out.write("\nPer Block Selected Stats\n")
        for block, flat_types in blocks_and_flat_types.items():
            out.write("\t{}\n".format(block))
            units = list(filter(lambda unit: unit.block == block, all_units))

            for flat_type in flat_types:
                booked, available = flat_stats(flat_type, units)
                out.write("\t{}: {}/{} ({:.2f}%) selected\n".format(flat_type, booked, available, (booked / available)*100))

            out.write("\n")


if __name__ == "__main__":
    url = "http://services2.hdb.gov.sg/webapp/BP13AWFlatAvail/BP13EBSFlatSearch"

    blocks_and_flat_types = {
        "107A": ["5-Room/3Gen"],
        "107B": ["5-Room/3Gen"],
        "108B": ["5-Room/3Gen"],
        "109A": ["5-Room/3Gen"],
        "109B": ["5-Room/3Gen"],
        "110A": ["5-Room/3Gen"],
        "110B": ["5-Room/3Gen"]
    }
    blocks_and_flat_types = OrderedDict(sorted(blocks_and_flat_types.items()))

    contracts = {
        "107A": "C1",
        "107B": "C1",
        "108B": "C1",
        "109A": "C1",
        "109B": "C1",
        "110A": "C1",
        "110B": "C1"
    }

    expected_count = {
        "5-Room/3Gen": 236
    }
    expected_count = OrderedDict(sorted(expected_count.items()))

    s = requests.Session()
    # Need to make an initial request to grab the cookies
    s.get("http://services2.hdb.gov.sg/webapp/BP13AWFlatAvail/BP13EBSFlatSearch?Town=Toa%20Payoh&Flat_Type=BTO&DesType=A&ethnic=Y&Flat=5-Room/3Gen&ViewOption=A&dteBallot=201602&projName=A&brochure=false")

    all_units = []
    debug = ""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    print("[{}] Start".format(datetime.now()))
    for block, flat_types in blocks_and_flat_types.items():
        contract = contracts[block]

        for flat_type in flat_types:
            payload = new_payload(block, flat_type, contract)

            units = fetch_and_parse(s, url, payload)
            print("[{}] {} {}: Found {} units".format(datetime.now(), block, flat_type, len(units)))

            for i, unit in enumerate(units):
                unit.update(block, flat_type)
                units[i] = unit

            all_units.extend(units)
            time.sleep(random.uniform(0, 3))

    all_units = sorted(all_units, key=lambda unit: unit.sort_key())

    write_json("data/bidadari.json", all_units)
    write_csv("data/bidadari.csv", all_units)
    write_stats("data/bidadari.log", all_units, blocks_and_flat_types, expected_count)
    print("[{}] End".format(datetime.now()))
    print("======================================\n")
