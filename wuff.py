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
    click.echo(f"TODO: STATS {ctx.obj['year']}")


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
