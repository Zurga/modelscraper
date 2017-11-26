#!/usr/bin/python

import importlib
import os

import click

available_models = [f[:-3] for f in os.listdir('scrape_models')
                  if f.endswith('.py') and not f.startswith('__')]
@click.command()
@click.argument('model', nargs=-1)
@click.option('--dummy', default=False, help='Whether to do a dummy run')
def main(model, dummy):
    dispatcher = Dispatcher()
    if model not in available_models:
        print('Model', model, 'is not in the folder "scrape_models".')
        os.exit(1)

    scrape_model = importlib.import_module(f'scrape_models.{model}')
    for variable in vars(scrape_model):
        if type(variable) == ScrapeModel:
            dispatcher.add_scraper(variable, dummy=dummy)

    dispatcher.run()

if __name__ == '__main__':
    main()
