#!/usr/bin/env python3
"""
This script provides a command line interface to search for dogs, retrieve
statistical information about those dogs, and to make up a new dog.
"""
from datetime import datetime
import csv
import os
import click
import requests

# pylint: disable=line-too-long
URL_DOG_DATA = "https://data.stadt-zuerich.ch/dataset/sid_stapo_hundenamen_od1002/download/KUL100OD1002.csv"


def get_dog_data(url):
    """Retrieve data from Zurich API."""
    r = requests.get(url, timeout=5)
    r.encoding = "utf-8-sig"
    return r.text.splitlines()


def parse_csv(lines):
    """Create csv.DictReader from data lines."""
    return csv.DictReader(lines)


def sex_to_letter(dog):
    "Return m (male) or f (female) based on the dog's sex."
    sex = dog["SexHundCd"]
    return {"1": "m", "2": "f"}[sex]


@click.group()
@click.option(
    "--year", default=datetime.now().year, help="Limit output to specific year."
)
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
    for row in filter(
        lambda row: row["HundenameText"] == name
        # todo: use last year from which there is a result
        and row["StichtagDatJahr"] == str(ctx.obj["year"]),
        reader,
    ):
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
    click.echo(f"TODO: CREATE {ctx.obj['year']}, {output_dir}")


if __name__ == "__main__":
    cli(obj={})
