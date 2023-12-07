#!/usr/bin/env python3
"""
This script provides a command line interface to search for dogs, retrieve
statistical information about those dogs, and to make up a new dog.
"""
import csv
import requests

# pylint: disable=line-too-long
URL_DOG_DATA = "https://data.stadt-zuerich.ch/dataset/sid_stapo_hundenamen_od1002/download/KUL100OD1002.csv"


def get_dog_data(url):
    """Gets data from zurich api"""
    r = requests.get(url, timeout=5)
    r.encoding = "utf-8-sig"
    return r.text.splitlines()


def parse_csv(lines):
    """Create csv.DictReader from data lines"""
    return csv.DictReader(lines)


if __name__ == "__main__":
    reader = parse_csv(get_dog_data(URL_DOG_DATA))
    for row in reader:
        print(row["HundenameText"])
