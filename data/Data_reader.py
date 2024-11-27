import csv


class Data_reader:

    configurations =[]
    def __init__(self):
        with open("data/config.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                print(row)
                self.configurations.append(row)