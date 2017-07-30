import os.path
import requests
from time import sleep
# Third party imports
import click
from hangoutsclient import HangoutsClient
from lxml import etree


@click.command()
@click.argument('bom_url')
@click.argument('search_string')
@click.argument('notify_user')
@click.option('--config_file', '-c',
              type=click.Path(exists=True), default=os.path.expanduser('~/.config/wynweather/config.ini'),
              help='path to config file.')
def main(config_file, bom_url, search_string, notify_user):
    """
    This script scrapes the weather warning feed given by BOM_URL, and if there are any current warning(s) that
    contain the keyword SEARCH_STRING, a message is sent to NOTIFY_USER using Google Hangouts.

    bom_url - URL for the BOM weather warning feed. See http://www.bom.gov.au/rss/.

    search_string - keyword used to trigger message being sent. e.g. "Hawthorn"

    notify_user - JID or full name of the Hangouts user to notify. e.g. "xxx@public.talk.google.com" or "Itiot Gimp"
    """
    message = None

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
        # Setup Hangouts bot instance, connect and send message
        hangouts = HangoutsClient(config_file)
        if hangouts.connect():
            hangouts.process(block=False)
        else:
            raise RuntimeError('Unable to connect to Hangouts.')
        sleep(5)  # need time for Hangouts roster to update
        hangouts.send_to([notify_user, ], message)
        hangouts.disconnect(wait=True)

if __name__ == '__main__':
    main()
