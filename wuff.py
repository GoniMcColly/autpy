#!/usr/bin/env python3
"""
Mit Wuff und Wau!

This script provides a CLI tool to explore data about dogs from the city of
Zurich.

The following functions are available:
- Search for a dog by name
- Collect and calculate various statistics
- Make up a new dog based on real data
"""

# 🙄
# pylint: disable=multiple-imports
# import pdb; pdb.set_trace() # allows debugging when running pytest
import csv
import os, sys, subprocess
import random
from pathlib import Path
from enum import Enum
import logging
from dataclasses import dataclass
from typing import Optional, Dict
import requests
import pytest
import responses
from dotenv import load_dotenv
import click
import rich
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress
from rich.traceback import install

install(show_locals=True)


__version_info__ = ("0", "1", "0")
__version__ = ".".join(__version_info__)


console = Console()


load_dotenv()
URL_DOG_DATA = os.getenv("URL_DOG_DATA")
URL_DOG_IMAGE_BASE = os.getenv("URL_DOG_IMAGE_BASE")
URL_DOG_IMAGE_LIST = os.getenv("URL_DOG_IMAGE_LIST")
ALLOWED_IMAGE_SUFFIXES = [
    s.strip() for s in os.getenv("ALLOWED_IMAGE_SUFFIXES").split(",")
]


@dataclass(frozen=True)
class Dog:
    """Dog entity, has getters to read dog data from."""

    class Sex(Enum):
        """Sex enumeration defines male and female."""

        MALE = "m"
        FEMALE = "f"

        def __str__(self):
            return f"{self.value}"

    name: str
    sex: Sex
    birth_year: int
    record_year: int
    count: int

    @staticmethod
    def from_dict(dic):
        """Create a dog from dictionary data."""
        return Dog(
            name=dic["HundenameText"],
            sex={"1": Dog.Sex.MALE, "2": Dog.Sex.FEMALE}[dic["SexHundCd"]],
            birth_year=int(dic["GebDatHundJahr"]),
            record_year=int(dic["StichtagDatJahr"]),
            count=int(dic["AnzHunde"]),
        )


class TestDog:
    """Test the Dog class."""

    def test_from_dict(self):
        """
        It should be possible to create a dog from a dictionary, as long as
        that dictionary contains all the necessary keys.
        """
        dog = Dog.from_dict(
            {
                "HundenameText": "Shoto",
                "SexHundCd": "1",
                "GebDatHundJahr": "2005",
                "StichtagDatJahr": "2024",
                "AnzHunde": 1,
            }
        )
        assert dog.name == "Shoto"
        assert dog.sex == Dog.Sex.MALE
        assert dog.birth_year == 2005
        assert dog.record_year == 2024
        assert dog.count == 1

    def test_from_dict_with_additional_keys(self):
        """
        Creating a dog from a dictionary should work as long as the necessary
        keys exist.
        The presence of additional keys should be ignored.
        """
        dog = Dog.from_dict(
            {
                "HundenameText": "Shoto",
                "Spitzname": "Sho",  # additional field
                "SexHundCd": "1",
                "GebDatHundJahr": "2005",  # additional field
                "GebDatHundTag": 12,
                "StichtagDatJahr": "2024",
                "AnzHunde": 1,
            }
        )
        assert dog.name == "Shoto"
        assert dog.sex == Dog.Sex.MALE
        assert dog.birth_year == 2005
        assert dog.record_year == 2024
        assert dog.count == 1

    def test_from_dict_invalid(self):
        """Test creating a dog from an invalid dictionary (should fail)."""
        with pytest.raises(KeyError):
            Dog.from_dict(
                {
                    "HundenameText": "Shoto",
                    "Hello": "World",
                    "SomeNumber": 5,
                }
            )


class DogData:
    """DogData provides a reusable iterator over dog statistics."""

    @staticmethod
    def retrieve(url, encoding=None):
        """Retrieve data from an API."""

        def get_dog_data(url):
            r = requests.get(url, timeout=5)
            if encoding:
                r.encoding = encoding
            return r.text.splitlines()

        def parse_csv(lines):
            return csv.DictReader(lines)

        reader = parse_csv(get_dog_data(url))
        return DogData(reader)

    def __init__(self, data):
        self.current = 0
        self.data = [Dog.from_dict(row) for row in data]
        if len(self.data) == 0:
            raise ValueError("no dog data provided")

    def __iter__(self):
        # Reset iterator so that it can be reused.
        self.current = 0
        return self

    def __next__(self):
        cur = self.current
        if cur < len(self.data):
            self.current += 1
            return self.data[cur]
        raise StopIteration


class TestDogData:
    """Test the DogData class."""

    @responses.activate
    def test_retrieve(self):
        """Test retrieving API data."""
        responses.add(
            responses.GET,
            URL_DOG_DATA,
            # pylint: disable=line-too-long
            body=""""StichtagDatJahr","DatenstandCd","HundenameText","GebDatHundJahr","SexHundCd","SexHundLang","SexHundSort","AnzHunde"
2015,"D","(Karl) Kaiser Karl vom Edersee",2013,"1","männlich",1,1
2015,"D","?",2009,"2","weiblich",2,1
2015,"D","?",2010,"2","weiblich",2,2
2017,"D","Rexi",2015,"2","weiblich",2,1
2017,"D","Rexli",1998,"1","männlich",1,1
2017,"D","Rey",2006,"1","männlich",1,1
2017,"D","Rey",2016,"1","männlich",1,1
2022,"D","Chloé",2021,"2","weiblich",2,1
2022,"D","Chloë",2016,"2","weiblich",2,1
2022,"D","Choco",2011,"1","männlich",1,1""",
            status=200,
        )
        dog_data = DogData.retrieve(URL_DOG_DATA)
        assert isinstance(dog_data, DogData)
        assert len(list(dog_data)) == 10

    @responses.activate
    def test_retrieve_incorrect_csv(self):
        """Test retrieving invalid data."""
        wrong_url = "https://www.example.com/no-dog-data-here/"
        responses.add(
            responses.GET,
            wrong_url,
            body="""This,Data,Is,Wrong
1,2,3,4
5,6,7,8""",
            status=200,
        )
        with pytest.raises(KeyError):
            DogData.retrieve(wrong_url)

    @responses.activate
    def test_retrieve_this_data_isnt_even_csv(self):
        """Test retrieving invalid data."""
        wrong_url = "https://www.example.com/no-dog-data-here/"
        responses.add(
            responses.GET,
            wrong_url,
            body="This is not dog data!",
            status=200,
        )
        with pytest.raises(ValueError):
            DogData.retrieve(wrong_url)

    @responses.activate
    def test_retrieve_wrong_url(self):
        """Test retrieving data from an invalid URL."""
        wrong_url = "https://this-page-does-not.exist/"
        with pytest.raises(requests.exceptions.RequestException):
            DogData.retrieve(wrong_url)

    def test_iterator(self):
        """Test that the iterator can be reused."""
        dogs = DogData(
            [
                {
                    "HundenameText": "Shoto",
                    "SexHundCd": "1",
                    "GebDatHundJahr": "2005",
                    "StichtagDatJahr": "2024",
                    "AnzHunde": 1,
                },
                {
                    "HundenameText": "Poppy",
                    "SexHundCd": "2",
                    "GebDatHundJahr": "2006",
                    "StichtagDatJahr": "2025",
                    "AnzHunde": 2,
                },
            ]
        )
        assert len(list(dogs)) == 2
        assert len(list(dogs)) == 2  # use twice to make sure, iterator is reusable


# @from: https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
class Singleton(type):
    """Metaclass to create singletons."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# 🙄
# pylint: disable=too-few-public-methods
class DogDataCache(metaclass=Singleton):
    """Caches the API response."""

    def __init__(self):
        logging.debug("retrieving dog data from API")
        self.dog_data = DogData.retrieve(URL_DOG_DATA, encoding="utf-8-sig")

    def __call__(self):
        return self.dog_data


@click.group()
@click.option("--year", help="Limit output to specific year.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
@click.pass_context
def cli(ctx, year, verbose):
    """Zürich Dog Tool"""
    ctx.ensure_object(dict)
    ctx.obj["year"] = int(year) if year else None

    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)
    logging.debug("verbose logging enabled")

    logging.debug("Read environment:")
    logging.debug("URL_DOG_DATA: %s", URL_DOG_DATA)
    logging.debug("URL_DOG_IMAGE_BASE: %s", URL_DOG_IMAGE_BASE)
    logging.debug("URL_DOG_IMAGE_LIST: %s", URL_DOG_IMAGE_LIST)
    logging.debug("ALLOWED_IMAGE_SUFFIXES: %s", ALLOWED_IMAGE_SUFFIXES)
    logging.debug("year set to %s", str(ctx.obj["year"]))


@cli.command()
def version():
    """Print version and exit."""
    console.print(__version__)
    sys.exit()


@cli.command()
@click.pass_context
@click.argument("name")
def find(ctx, name):
    """Find a dog by its name."""
    try:
        dog_data = DogDataCache()()
    except ValueError:
        logging.exception("failed to retrieve dog data")
        sys.exit(-1)

    matching_name = [dog for dog in dog_data if dog.name == name]

    if len(matching_name) == 0:
        console.rule(f"[red]No result for name {name}.[/red]", style="red b")
        return

    year = (
        ctx.obj["year"]
        or max(matching_name, key=lambda dog: dog.record_year).record_year
    )

    result = [dog for dog in matching_name if dog.record_year == year]

    def create_dog_search_table(title, dogs):
        table = Table(title=title, box=box.HEAVY_HEAD, show_lines=True)
        table.add_column("Name", style="bold cyan", min_width=12)
        table.add_column("Birth Year", style="bold green")
        table.add_column("Sex", style="bold magenta")

        for dog in dogs:
            table.add_row(dog.name, str(dog.birth_year), dog.sex.value)

        return table

    if len(result) == 0:
        console.rule(f"[red]No result for year {year}.[/red]", style="red b")
        return

    console.rule()
    console.print(create_dog_search_table("results", result), justify="center")


# 🙄
# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class DogStats:
    """Various statistics about dog data."""

    name_longest: str
    name_shortest: str
    top_names_male: Dict[str, int]
    top_names_female: Dict[str, int]
    dog_count_male: int
    dog_count_female: int
    first_year: Optional[int]
    last_year: int
    top_limit: int = 10

    @property
    def dog_count_overall(self) -> int:
        """Overall dog count (male and female)."""
        return self.dog_count_male + self.dog_count_female

    @property
    def top_names_overall(self) -> Dict[str, int]:
        """Top names overall (male and female)."""
        return sorted(
            self.top_names_male + self.top_names_female,
            key=lambda x: x[1],
            reverse=True,
        )[: self.top_limit]


def analyze(dog_data: DogData, year: Optional[int] = None) -> DogStats:
    """
    Calculate various statistics about dog data.
    Limit statistics to a specific year if `year` is set.
    """
    # 🙄
    # pylint: disable=too-many-locals
    longest_name = ""
    shortest_name = None
    male_name_count = {}
    female_name_count = {}
    male_dog_count = 0
    female_dog_count = 0
    first_year = None
    last_year = 0

    dog_data = (
        filter(lambda dog: dog.record_year == year, dog_data) if year else dog_data
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

    return DogStats(
        name_longest=longest_name,
        name_shortest=shortest_name,
        top_names_male=top_male_name_sorted,
        top_names_female=top_female_name_sorted,
        dog_count_male=male_dog_count,
        dog_count_female=female_dog_count,
        first_year=first_year,
        last_year=last_year,
    )


class TestAnalyze:
    """Unit tests for the analyze function."""

    def test_analyze(self):
        """Test the analyze function."""
        test_dogs = [
            Dog("Max", Dog.Sex.MALE, 2003, 2020, 3),
            Dog("Leila", Dog.Sex.FEMALE, 2016, 2021, 1),
            Dog("Mia", Dog.Sex.FEMALE, 2015, 2023, 2),
        ]
        s = analyze(test_dogs)

        assert s.name_longest == "Leila"
        assert s.name_shortest == "Max"  # first shortest name is used
        assert s.top_names_male == [("Max", 3)]
        assert s.top_names_female == [("Mia", 2), ("Leila", 1)]
        assert s.top_names_overall == [("Max", 3), ("Mia", 2), ("Leila", 1)]
        assert s.dog_count_male == 3
        assert s.dog_count_female == 3
        assert s.dog_count_overall == 6
        assert s.first_year == 2020
        assert s.last_year == 2023

    def test_analyze_with_year(self):
        """Test the analyze function. Provide a year value."""
        test_dogs = [
            Dog("Max", Dog.Sex.MALE, 2003, 2020, 3),
            Dog("Leila", Dog.Sex.FEMALE, 2016, 2021, 1),
            Dog("Leila", Dog.Sex.FEMALE, 2015, 2020, 2),
            Dog("Mi", Dog.Sex.FEMALE, 2015, 2023, 2),
        ]
        s = analyze(test_dogs, year=2020)

        assert s.name_longest == "Leila"
        assert s.name_shortest == "Max"  # Mi is ignored, bc wrong year
        assert s.top_names_male == [("Max", 3)]
        assert s.top_names_female == [("Leila", 2)]
        assert s.top_names_overall == [("Max", 3), ("Leila", 2)]
        assert s.dog_count_male == 3
        assert s.dog_count_female == 2
        assert s.dog_count_overall == 5
        assert s.first_year == 2020
        assert s.last_year == 2020


@cli.command()
@click.pass_context
def stats(ctx):
    """Print interesting stats about dog data."""
    try:
        dog_data = DogDataCache()()
    except ValueError:
        logging.exception("failed to retrieve dog data")
        sys.exit(-1)

    s = analyze(dog_data, ctx.obj["year"])

    print("")
    if s.first_year is None:
        console.print(f"No data available for year: {ctx.obj['year']}", style="red")
        return

    if ctx.obj["year"]:
        console.rule(f"Showing stats for year: {ctx.obj['year']}")
    else:
        console.rule(
            f"Showing stats for years: {s.first_year} to {s.last_year}", style="b"
        )
        print("")

    console.rule("[blue]The longest dog name is:[/blue]")
    console.print(f"[cyan]{s.name_longest}[/cyan]", style="b", justify="center")
    print("")
    console.rule("[blue]The shortest dog name is:[/blue]")
    console.print(f"[cyan]{s.name_shortest}[/cyan]", style="b", justify="center")
    print("")
    console.rule("[blue]Total number of female dogs:[/blue]")
    console.print(f"[cyan]{s.dog_count_female}[/cyan]", style="b", justify="center")
    print("")
    console.rule("[blue]Total number of male dogs:[/blue]")
    console.print(f"[cyan]{s.dog_count_male}[/cyan]", style="b", justify="center")
    print("")
    console.rule("[blue]Total number of dogs:[/blue]")
    console.print(f"[cyan]{s.dog_count_overall}[/cyan]", style="b", justify="center")

    def create_name_table(title, name_data):
        table = Table(title=title, box=box.HEAVY_HEAD, show_lines=True)
        table.add_column("Rank", style="dim bold blue", width=6)
        table.add_column("Name", style="bold cyan", min_width=12)
        table.add_column("Count", justify="right", style="green")
        for i, (name, count) in enumerate(name_data, start=1):
            table.add_row(str(i), name, str(count))
        return table

    print("")
    table1 = create_name_table(
        "[bold]Top Ten Most Common Names Overall[/bold]", s.top_names_overall
    )
    table2 = create_name_table(
        "[bold]Top Ten Most Common Female Names[/bold]", s.top_names_female
    )
    table3 = create_name_table(
        "[bold]Top Ten Most Common Male Names[/bold]", s.top_names_overall
    )
    tables_columns = rich.columns.Columns([table1, table2, table3], expand=True)
    console.print(tables_columns)


def get_dog_image_urls(url_list, allowed_suffixes):
    """Get a list of dog picture URLs."""
    r = requests.get(url_list, timeout=5)
    r.raise_for_status()
    image_list = r.json()
    actually_images = [
        url for url in image_list if Path(url).suffix in allowed_suffixes
    ]
    return actually_images


def download_file(file_url, save_path, progress_start=None, progress_update=None):
    """
    Download a file from `file_url` and save it to `save_path`.
    `progress_start` will be passed the total file size before downloading starts.
    `progress_update` is periodically called with the amount of bytes
    downloaded in that period.
    """
    # @from: https://stackoverflow.com/a/37573701
    r = requests.get(file_url, stream=True, timeout=5)
    r.raise_for_status()
    image_size = int(r.headers.get("Content-Length", 0))
    if progress_start:
        progress_start(image_size)
    downloaded_size = 0
    with open(save_path, "wb") as f:
        for data in r.iter_content(1024):
            f.write(data)
            if progress_update:
                progress_update(len(data))
            downloaded_size += len(data)
    if downloaded_size != image_size:
        raise ValueError(
            f"could not download file {file_url}, file is {image_size} bytes, got {downloaded_size}"
        )


@responses.activate
def test_download_image_file(tmp_path):
    """Test downloading a dog picture."""
    responses.add(
        responses.GET,
        URL_DOG_IMAGE_LIST,
        json=[
            "00186969-c51d-462b-948b-30a7e1735908.jpg",
            "00564ba3-e5cb-4b2b-8d97-c65a9ef26c23.png",
            "00b417af-0b5f-42d7-9ad0-6aab6c3db491.jpg",
        ],
        status=200,
    )
    png_content = b"""\x89\x50\x4E\x47\x0D\x0A\x1A\x0A<-PNG magic number.
This is definitely real PNG data!
Did you know that PNG is pronounced Ping which means 'Ping is not GIF'?"""
    responses.add(
        responses.GET,
        f"{URL_DOG_IMAGE_BASE}/00564ba3-e5cb-4b2b-8d97-c65a9ef26c23.png",
        body=png_content,
        content_type="image/png",
        headers={"Content-Length": str(len(png_content))},
        status=200,
    )
    image_urls = get_dog_image_urls(URL_DOG_IMAGE_LIST, ALLOWED_IMAGE_SUFFIXES)
    image_url = image_urls[1]
    download_path = tmp_path / Path(image_url).name
    download_file(f"{URL_DOG_IMAGE_BASE}/{image_url}", download_path)

    with open(download_path, "rb") as fd:
        content = fd.read()
        assert len(content) == len(png_content)
        assert content == png_content


@cli.command()
@click.option(
    "--output-dir", "-o", default=os.getcwd(), help="Directory to save dog picture to."
)
@click.pass_context
# 🙄
# pylint: disable=too-many-locals
def create(ctx, output_dir):
    """Make up a new dog at random using data from real dogs."""

    def open_default(file):
        """Opens file with the associated default application."""
        if sys.platform == "win32":
            os.startfile(file)
        else:
            subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", file])

    try:
        dog_data = DogDataCache()()
    except ValueError:
        logging.exception("failed to retrieve dog data")
        sys.exit(-1)

    sex = random.choice([Dog.Sex.MALE, Dog.Sex.FEMALE])
    matching_dogs = [dog for dog in dog_data if dog.sex == sex]
    if ctx.obj["year"]:
        matching_dogs = [
            dog for dog in matching_dogs if dog.record_year == ctx.obj["year"]
        ]
    name = random.choice(matching_dogs).name
    birth_year = random.choice(matching_dogs).birth_year

    try:
        image_urls = get_dog_image_urls(URL_DOG_IMAGE_LIST, ALLOWED_IMAGE_SUFFIXES)
        image_url = random.choice(image_urls)
        image_ext = Path(image_url).suffix
        image_name = f"{name}_{birth_year}{image_ext}"
        save_path = Path(output_dir) / image_name

        with Progress(transient=True) as progress:
            download_task = None

            def progress_start(amount):
                nonlocal download_task
                download_task = progress.add_task(
                    "Downloading dog picture", total=amount
                )

            def progress_update(amount):
                nonlocal download_task
                progress.update(download_task, advance=amount)

            download_file(
                f"{URL_DOG_IMAGE_BASE}/{image_url}",
                save_path,
                progress_start,
                progress_update,
            )

    except requests.exceptions.RequestException:
        logging.exception("failed to download dog picture")
        sys.exit(-1)

    console.print(f"{name} {birth_year} ({sex}) \\[{save_path}]")
    open_default(save_path)


if __name__ == "__main__":
    cli(obj={})
