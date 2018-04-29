#!/usr/bin/python3

import importlib
import os
import pprint

import click

from modelscraper.components import ScrapeModel


if 'banner.txt' in os.listdir():
    with open('banner.txt') as fle:
        print(fle.read())

available_models = sorted([f[:-3] for f in os.listdir('scrape_models')
                  if f.endswith('.py') and not f.startswith('__')])
@click.command()
@click.argument('model', nargs=-1)
@click.option('--dummy', default=False, help='Whether to do a dummy run')
def main(model, dummy):
    if len(model) == 1:
        model = model[0]
    if model not in available_models:
        print('Model', model, 'is not in the folder "scrape_models".')
        print('These models are available:')
        pprint.pprint(available_models, compact=True)
        return
    imported = vars(importlib.import_module('scrape_models.%s' % model)).values()
    scrape_models = (model for model in imported
                     if type(model) == ScrapeModel)
    for model in scrape_models:
        model.run(dummy=dummy)

if __name__ == '__main__':
    main()
