import html
import re
import requests

from instaloader import Instaloader
from instaloader.structures import Profile


def get_domain(url):
    # get domain
    m = re.match('[http|https]+:\/\/([\w\-.]+)', url)
    domain = m.groups()[0]
    print(f'domain: {domain}')
    return domain


def get_emails(txt):
    # get what looks like email from a given text
    return set(re.findall('[\w\-\_]+@[\w\-\_]+\.[a-zA-Z]+', txt))


def get_links(txt):
    # get what looks like websites from a given text
    links = re.findall('([http|https]+:\/\/[\w\-\/\=\?\.]+)', txt)
    # get those with .com
    coms = re.findall('([\w\-\.\/\:]+\.com[\w\-\/\=\?\.]+)', txt)
    links.extend(coms)
    # exclude truncated urls (with ...)
    links = [link for link in links if not re.findall('\.{3}', link)]
    # exclude goodreads site
    links = [link for link in links if not re.match('.*goodreads.*', link)]
    return set(links)


def get_emails_links_by_url(url):
    try:
        r = requests.get(url)
        # print(f"status code: {r.status_code}")
    except requests.exceptions.ConnectionError:
        print(f'ERROR: Unable to reach url: {url}')
        return [], []
    except requests.exceptions.MissingSchema:
        # missing http:// so add and try again
        url = f'http://{url}'
        try:
            r = requests.get(url)
        except Exception as e:
            print(e)
            print(f'ERROR connecting to {url}. Skipping..')
            return [], []
    except Exception as e:
        print(e)
        print(f'ERROR connecting to {url}. Skipping..')
        return [], []

    # unescape html characters
    txt = html.unescape(r.text)

    # find what looks like email
    emails = get_emails(txt)
    if emails:
        return emails, []  # if there's email, no need to find links

    links = get_links(txt)
    print(f'Total {len(links)} links found.')

    return emails, links


def hunt_emails(url):
    """ Hunt emails by a given url.
    It will try to find emails from the url, and from likely links found on 
    the first url.
    """
    print(f'\nSearch for emails from URL: {url}')
    emails, links = get_emails_links_by_url(url)
    if len(emails) >= 1:
        # got email(s), no need to look further
        return emails

    # filter links and get those with potential
    valid_links = []
    for link in links:
        # ignore the files
        if re.match('.*(\.[a-zA-Z]{2,})$', link):
            continue
        elif re.match('.*profile.*', link):
            valid_links.append(link)
        elif re.match('.*about.*', link):
            valid_links.append(link)
        elif re.match('.*contact.*', link):
            valid_links.append(link)

    if valid_links:
        print('Potentially good links:')
        for link in valid_links:
            print(f' {link}')
            emails, _ = get_emails_links_by_url(link)
            if len(emails) >= 1:
                # found emails!
                return emails

    return []


def get_insta_profile(url, loader):
    """ 
    loader: instance of Instaloader

    Return: insta profile (dict) and emails (list)
    """
    m = re.match('.*instagram.com\/([\w\.]+)', url)
    if not m:
        print(f'ERROR: Unable to get instagram username from: {url}')
        return None, []

    username = m.groups()[0]
    profile = Profile.from_username(loader.context, username)

    insta = {}
    insta['biography'] = profile.biography
    insta['external_url'] = profile.external_url
    insta['followers'] = profile.followers
    insta['following'] = profile.followees

    # check if there's email in bio
    emails = get_emails(profile.biography)
    if len(emails) >= 1:
        # got email(s), no need to look further
        return insta, emails

    # if not found, search in the external url
    if profile.external_url:
        emails, _ = get_emails_links_by_url(profile.external_url)

    return insta, emails
