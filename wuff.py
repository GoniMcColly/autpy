#!/usr/bin/env python3
"""
This script provides a command line interface to search for dogs, retrieve
statistical information about those dogs, and to make up a new dog.
"""
import csv
import os
import random
from pathlib import Path
from enum import Enum
import click
import requests

# pylint: disable=line-too-long
URL_DOG_DATA = "https://data.stadt-zuerich.ch/dataset/sid_stapo_hundenamen_od1002/download/KUL100OD1002.csv"
URL_DOG_IMAGE_BASE = "https://random.dog"
URL_DOG_IMAGE_LIST = f"{URL_DOG_IMAGE_BASE}/doggos"
ALLOWED_IMAGE_SUFFIXES = [".png", ".jpg", ".jpeg"]


class Dog:
    """Dog entity, has getters to read dog data from."""

    class Sex(Enum):
        """Sex enumeration defines male and female."""

        MALE = "m"
        FEMALE = "f"

        def __str__(self):
            return f"{self.value}"

    def __init__(self, data):
        self.data = data

    @property
    def name(self):
        """The dog's name."""
        return self.data["HundenameText"]

    @property
    def sex(self):
        """The dog's sex."""
        sex = self.data["SexHundCd"]
        return {"1": Dog.Sex.MALE, "2": Dog.Sex.FEMALE}[sex]

    @property
    def birth_year(self):
        """The dog's birth year."""
        return int(self.data["GebDatHundJahr"])

    @property
    def record_year(self):
        """The year this data was recorded in."""
        return int(self.data["StichtagDatJahr"])

    @property
    def count(self):
        """The number of duplicate dogs."""
        return int(self.data["AnzHunde"])


class DogData:
    """DogData provides a reusable iterator over dog statistics."""

    @staticmethod
    def retrieve(url):
        """Retrieve data from an API."""

        def get_dog_data(url):
            r = requests.get(url, timeout=5)
            r.encoding = "utf-8-sig"
            return r.text.splitlines()

        def parse_csv(lines):
            return csv.DictReader(lines)

        reader = parse_csv(get_dog_data(url))
        return DogData(reader)

    def __init__(self, data):
        self.current = 0
        self.data = list(data)

    def __iter__(self):
        self.current = 0
        return self

    def __next__(self):
        cur = self.current
        if cur < len(self.data):
            self.current += 1
            return Dog(self.data[cur])
        raise StopIteration


# @from: https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
class Singleton(type):
    """Metaclass to create singletons."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# pylint: disable=too-few-public-methods
class DogDataCache(metaclass=Singleton):
    """Caches the API response."""

    def __init__(self):
        self.dog_data = DogData.retrieve(URL_DOG_DATA)

    def __call__(self):
        return self.dog_data


def get_dog_image(url_image_base, url_list, allowed_suffixes):
    """
    Downloads a randomly chosen dog picture.
    Returns the raw image data and the image type (extension) as a tuple.
    """
    r = requests.get(url_list, timeout=5)
    image_list = r.json()
    actually_images = [
        url for url in image_list if Path(url).suffix in allowed_suffixes
    ]
    image_url = random.choice(actually_images)
    r = requests.get(f"{url_image_base}/{image_url}", timeout=5)
    return r.content, Path(image_url).suffix


@click.group()
@click.option("--year", help="Limit output to specific year.")
@click.pass_context
def cli(ctx, year):
    """Zürich Dog Tool"""
    ctx.ensure_object(dict)
    ctx.obj["year"] = int(year) if year else None


@cli.command()
@click.pass_context
@click.argument("name")
def find(ctx, name):
    """Find a dog by its name."""
    dog_data = DogDataCache()()

    matching_name = [dog for dog in dog_data if dog.name == name]

    if len(matching_name) == 0:
        click.echo(f"No result for name {name}.")
        return

    year = (
        ctx.obj["year"]
        or max(matching_name, key=lambda dog: dog.record_year).record_year
    )

    result = [dog for dog in matching_name if dog.record_year == year]

    if len(result) == 0:
        click.echo(f"No result for year {year}.")
        return

    for dog in result:
        click.echo(f"{dog.name} {dog.birth_year} ({dog.sex})")


@cli.command()
@click.pass_context
def stats(ctx):
    """Print interesting stats about dog data."""
    # ***Pylint ist doof ;<<***
    # pylint: disable=too-many-locals
    dog_data = DogDataCache()()
    longest_name = ""
    shortest_name = None
    male_name_count = {}
    female_name_count = {}
    male_dog_count = 0
    female_dog_count = 0
    first_year = None
    last_year = 0

    dog_data = (
        filter(lambda dog: dog.record_year == ctx.obj["year"], dog_data)
        if ctx.obj["year"]
        else dog_data
    )
    for dog in dog_data:
        if dog.name == "?":
            continue
        if len(dog.name) > len(longest_name):
            longest_name = dog.name
        if shortest_name is None or len(dog.name) < len(shortest_name):
            shortest_name = dog.name
        if first_year is None or first_year > dog.record_year:
            first_year = dog.record_year
        if last_year < dog.record_year:
            last_year = dog.record_year
        if dog.sex == Dog.Sex.MALE:
            male_name_count[dog.name] = male_name_count.get(dog.name, 0) + dog.count
            male_dog_count += dog.count
        else:
            female_name_count[dog.name] = female_name_count.get(dog.name, 0) + dog.count
            female_dog_count += dog.count

    top_male_name_sorted = sorted(
        male_name_count.items(), key=lambda x: x[1], reverse=True
    )[:10]
    top_female_name_sorted = sorted(
        female_name_count.items(), key=lambda x: x[1], reverse=True
    )[:10]
    top_overall_name_sorted = sorted(
        top_male_name_sorted + top_female_name_sorted, key=lambda x: x[1], reverse=True
    )[:10]
    top_male_name_string = ", ".join(
        [f"{name} ({count})" for name, count in top_male_name_sorted]
    )
    top_female_name_string = ", ".join(
        [f"{name} ({count})" for name, count in top_female_name_sorted]
    )
    top_overall_name_string = ", ".join(
        [f"{name} ({count})" for name, count in top_overall_name_sorted]
    )

    if first_year is None:
        click.echo(f"No data available for year: {ctx.obj['year']}")
        return

    if ctx.obj["year"]:
        click.echo(f"Showing stats for year: {ctx.obj['year']}")
    else:
        click.echo(f"Showing stats for years: {first_year} to {last_year}")

    click.echo(f"The longest dog name is: {longest_name}")
    click.echo(f"The shortest dog name is: {shortest_name}")
    click.echo(f"Top ten most common names overall: {top_overall_name_string}")
    click.echo(f"Top ten most common female names: {top_female_name_string}")
    click.echo(f"Top ten most common male names: {top_male_name_string}")
    click.echo(f"Total number of female dogs: {female_dog_count}")
    click.echo(f"Total number of male dogs: {male_dog_count}")
    click.echo(f"Total number of dogs: {female_dog_count+male_dog_count}")


@cli.command()
@click.option(
    "--output-dir", "-o", default=os.getcwd(), help="Directory to save dog picture to."
)
@click.pass_context
def create(ctx, output_dir):
    """Make up a new dog at random."""
    dog_data = DogDataCache()()
    sex = random.choice([Dog.Sex.MALE, Dog.Sex.FEMALE])
    matching_dogs = [dog for dog in dog_data if dog.sex == sex]
    if ctx.obj["year"]:
        matching_dogs = [
            dog for dog in matching_dogs if dog.record_year == ctx.obj["year"]
        ]
    name = random.choice(matching_dogs).name
    birth_year = random.choice(matching_dogs).birth_year
    (image_data, image_ext) = get_dog_image(
        URL_DOG_IMAGE_BASE, URL_DOG_IMAGE_LIST, ALLOWED_IMAGE_SUFFIXES
    )
    image_name = f"{name}_{birth_year}{image_ext}"
    save_path = Path(output_dir) / image_name
    with open(save_path, "wb") as f:
        f.write(image_data)
    click.echo(f"{name} {birth_year} ({sex}) [{save_path}]")


if __name__ == "__main__":
    cli(obj={})
