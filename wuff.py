#!/usr/bin/env python3
"""
This script provides a command line interface to search for dogs, retrieve
statistical information about those dogs, and to make up a new dog.
"""
import csv
import os
import random
from pathlib import Path
import click
import requests

# pylint: disable=line-too-long
URL_DOG_DATA = "https://data.stadt-zuerich.ch/dataset/sid_stapo_hundenamen_od1002/download/KUL100OD1002.csv"
URL_DOG_IMAGE_BASE = "https://random.dog"
URL_DOG_IMAGE_LIST = f"{URL_DOG_IMAGE_BASE}/doggos"
ALLOWED_IMAGE_SUFFIXES = [".png", ".jpg", ".jpeg"]


def get_dog_data(url):
    """Retrieve data from Zurich API."""
    r = requests.get(url, timeout=5)
    r.encoding = "utf-8-sig"
    return r.text.splitlines()


def parse_csv(lines):
    """Create csv.DictReader from data lines."""
    return csv.DictReader(lines)


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
    return (r.content, Path(image_url).suffix)


def sex_to_letter(dog):
    "Return m (male) or f (female) based on the dog's sex."
    sex = dog["SexHundCd"]
    return {"1": "m", "2": "f"}[sex]


@click.group()
@click.option("--year", help="Limit output to specific year.")
@click.pass_context
def cli(ctx, year):
    """Zürich Dog Tool"""
    ctx.ensure_object(dict)
    ctx.obj["year"] = year


@cli.command()
@click.pass_context
@click.argument("name")
def find(ctx, name):
    """Find a dog by its name."""
    reader = parse_csv(get_dog_data(URL_DOG_DATA))

    matching_name = [row for row in reader if row["HundenameText"] == name]

    if len(matching_name) == 0:
        click.echo(f"No result for name {name}.")
        return

    year = (
        ctx.obj["year"]
        or max(matching_name, key=lambda row: row["StichtagDatJahr"])["StichtagDatJahr"]
    )

    result = [row for row in matching_name if row["StichtagDatJahr"] == year]

    if len(result) == 0:
        click.echo(f"No result for year {year}.")
        return

    for row in result:
        sex_letter = sex_to_letter(row)
        click.echo(f"{row['HundenameText']} {row['GebDatHundJahr']} ({sex_letter})")


@cli.command()
@click.pass_context
def stats(ctx):
    """Print interesting stats about dog data."""
    # ***Pylint ist doof ;<<***
    # pylint: disable=too-many-locals
    reader = parse_csv(get_dog_data(URL_DOG_DATA))
    longest_name = ""
    shortest_name = None
    male_name_count = {}
    female_name_count = {}
    male_dog_count = 0
    female_dog_count = 0
    first_year = None
    last_year = 0

    data = (
        filter(lambda row: row["StichtagDatJahr"] == ctx.obj["year"], reader)
        if ctx.obj["year"]
        else reader
    )
    for row in data:
        if row["HundenameText"] == "?":
            continue
        if len(row["HundenameText"]) > len(longest_name):
            longest_name = row["HundenameText"]
        if shortest_name is None or len(row["HundenameText"]) < len(shortest_name):
            shortest_name = row["HundenameText"]
        if first_year is None or first_year > int(row["StichtagDatJahr"]):
            first_year = int(row["StichtagDatJahr"])
        if last_year < int(row["StichtagDatJahr"]):
            last_year = int(row["StichtagDatJahr"])
        if sex_to_letter(row) == "m":
            male_name_count[row["HundenameText"]] = male_name_count.get(
                row["HundenameText"], 0
            ) + int(row["AnzHunde"])
            male_dog_count += int(row["AnzHunde"])
        else:
            female_name_count[row["HundenameText"]] = female_name_count.get(
                row["HundenameText"], 0
            ) + int(row["AnzHunde"])
            female_dog_count += int(row["AnzHunde"])

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
    reader = parse_csv(get_dog_data(URL_DOG_DATA))
    sex = random.choice(["m", "f"])
    matching_dogs = [row for row in reader if sex_to_letter(row) == sex]
    if ctx.obj["year"]:
        matching_dogs = [
            row for row in matching_dogs if row["StichtagDatJahr"] == ctx.obj["year"]
        ]
    name = random.choice(matching_dogs)["HundenameText"]
    birth_year = random.choice(matching_dogs)["GebDatHundJahr"]
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
