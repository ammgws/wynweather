import os.path
import requests
from configparser import ConfigParser
from pathlib import Path
from time import sleep
# Third party
import click
from hangoutsclient import HangoutsClient
from lxml import etree

APP_NAME = 'wynweather'


def create_dir(ctx, param, directory):
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    return directory


@click.command()
@click.argument('bom_url')
@click.argument('search_string')
@click.argument('notify_user')
@click.option(
    '--config-path',
    type=click.Path(),
    default=os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')), APP_NAME),
    callback=create_dir,
    help='Path to directory containing config file. Defaults to XDG config dir.',
)
@click.option(
    '--cache-path',
    type=click.Path(),
    default=os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), APP_NAME),
    callback=create_dir,
    help='Path to directory to store logs and such. Defaults to XDG cache dir.',
)
def main(config_path, cache_path, bom_url, search_string, notify_user):
    """
    This script scrapes the weather warning feed given by BOM_URL, and if there are any current warning(s) that
    contain the keyword SEARCH_STRING, a message is sent to NOTIFY_USER using Google Hangouts.

    bom_url - URL for the BOM weather warning feed. See http://www.bom.gov.au/rss/.

    search_string - keyword used to trigger message being sent. e.g. "Hawthorn"

    notify_user - JID or full name of the Hangouts user to notify. e.g. "xxx@public.talk.google.com" or "Itiot Gimp"
    """
    config_file = os.path.join(config_path, 'config.ini')
    config = ConfigParser()
    config.read(config_file)
    client_id = config.get('Hangouts', 'client_id')
    client_secret = config.get('Hangouts', 'client_secret')
    token_file = os.path.join(cache_path, 'hangouts_cached_token')
    if not os.path.isfile(token_file):
        Path(token_file).touch()

    message = ''

    response = requests.get(bom_url)
    if response.status_code == 200:
        tree = etree.fromstring(response.content)
        warning_titles = tree.xpath("//item/title/text()")
        warning_links = tree.xpath("//item/link/text()")
    else:
        response.raise_for_status()

    for title, link in zip(warning_titles, warning_links):
        response = requests.get(link)
        if response.status_code == 200:
            if search_string in response.text:
                message = f"Watch out wyn! ({title}: {link})"
        else:
            response.raise_for_status()

    if message:
        hangouts = HangoutsClient(client_id, client_secret, token_file)
        if hangouts.connect():
            hangouts.process(block=False)
        else:
            raise RuntimeError('Unable to connect to Hangouts.')
        sleep(5)  # need time for Hangouts roster to update
        hangouts.send_to([notify_user, ], message)
        hangouts.disconnect(wait=True)

if __name__ == '__main__':
    main()
