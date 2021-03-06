"""This module contains functions to scrape imdb.com and put that data into a
pandas dataframe.

These functions are specifically designed for scraping imdb.com. They will not
work on other websites.
"""

import re
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import requests
import dateutil.parser
from forex_python.converter import CurrencyRates


JAPAN_BASE_URL = 'https://www.imdb.com/search/title/?title_type=feature&release_date=,' \
                 '2020-07-01&genres=animation&countries=jp&sort=release_date,desc&count=' \
                 '100&view=simple'

JAPAN_NEXT_URL = 'https://www.imdb.com/search/title/?title_type=feature&release_date=,' \
                 '2020-07-01&genres=animation&countries=jp&view=simple&sort=release_date,' \
                 'desc&count=100&start=101&ref_=adv_nxt'

AMERICAN_BASE_URL = 'https://www.imdb.com/search/title/?title_type=feature&release_date=,' \
                    '2020-07-01&genres=animation&countries=us&sort=release_date,desc&count=' \
                    '100&view=simple'

AMERICAN_NEXT_URL = 'https://www.imdb.com/search/title/?title_type=feature&release_date=,' \
                    '2020-07-01&genres=animation&countries=us&view=simple&sort=release_date,' \
                    'desc&count=100&start=101&ref_=adv_nxt'


def get_movie_df(links):
    """Returns a dataframe after scraping data from a list of links.

    Accepts list of links, scrapes data for each link, puts data into
    dicts, and converts list of dicts into a dataframe.

    Args:
        links: A list of movie title links (that are appended to imdb.com).
    """
    movie_dicts = []
    counter = 0
    for link in links:
        movie_dicts.append(get_movie_dict(link))
        counter += 1
        print(counter)
    movie_df = pd.DataFrame(movie_dicts)
    return movie_df


def get_movie_dict(link):
    """Returns a dictionary after scraping data from a link.

    Args:
        link: A movie title link (that is appended to imdb.com).
    """"
    base_url = 'https://www.imdb.com'
    url = base_url + link
    soup = create_soup(url)

    headers = ['title', 'country', 'runtime_minutes', 'budget', 'global_gross',
               'mpaa_rating', 'japan_release_date', 'usa_release_date', 'genres',
               'imdb_user_rating', 'imdb_user_rating_count', 'oscar_wins',
               'non_oscar_wins', 'metascore']

    title = get_title(soup)
    country = get_country(soup)
    runtime = get_runtime(soup)
    budget = get_budget(soup)
    global_gross = get_global_gross(soup)
    mpaa_rating = get_mpaa_rating(soup)

    release_info_url = url + 'releaseinfo'
    release_info_soup = create_soup(release_info_url)

    if country == 'Japan':
        japan_release_date = get_japan_release_date(release_info_soup)
        usa_release_date = None
    elif country == 'USA':
        usa_release_date = get_usa_release_date(release_info_soup)
        japan_release_date = None
    else:
        japan_release_date = None
        usa_release_date = None

    genres = get_genres(soup)
    imdb_user_rating = get_user_rating(soup)
    imdb_user_rating_count = get_user_rating_count(soup)
    oscar_wins = get_oscar_wins(soup)
    non_oscar_wins = get_non_oscar_wins(soup)
    metascore = get_metascore(soup)

    movie_dict = dict(
        zip(headers, [title, country, runtime, budget, global_gross,
                      mpaa_rating, japan_release_date,
                      usa_release_date, genres, imdb_user_rating,
                      imdb_user_rating_count, oscar_wins,
                      non_oscar_wins, metascore]))

    return movie_dict


def get_search_urls(base_url, next_url):
    """Returns a list of URLs that correspond to imdb.com search pages.

    For example, when searching for all Japanese animated films, will get a
    search page that corresponds to films 1-100 and can click through other
    search pages that correspond to films 101-200, 201-300, etc. This function
    retrieves the URLs for all search pages.

    Args:
        base_url: The URL of the first search page.
        next_url: The URL of the second search page.
    """
    search_urls = [base_url, next_url]
    num_titles = get_num_titles(base_url)

    for i in range(num_titles//100-1):
        search_urls.append(
            next_url.replace('101', str(201+100*i)))
    return search_urls


def get_num_titles(base_url):
    """Returns the number of titles that correspond to a single
    search on imdb.com.

    For example, a search for all Japanese animated films may yield 1,400 titles.
    This function returns the number of titles as an int.

    Args:
        base_url: The URL of the first search page.
    """
    soup = create_soup(base_url)
    mini_header = soup.find('div', class_='desc').findNext().text.split()
    num_titles = int(
        mini_header[mini_header.index('titles.')-1].replace(',', ''))
    return num_titles


def create_soup(url):
    """Creates a BeautifulSoup object for a given URL."""
    response_text = requests.get(url).text
    soup = BeautifulSoup(response_text, 'html5lib')
    return soup


def create_soups(urls):
    """Creates a list of BeautifulSoup objects for a list of URLs."""
    soups = []
    for url in urls:
        response_text = requests.get(url).text
        soup = BeautifulSoup(response_text, 'html5lib')
        soups.append(soup)
    return soups


def get_title_urls(soups):
    """Returns a list of movie title links (that are appended to imdb.com).

    Args:
        soups: A list of soups created from search URLs.
    """
    titles_links = []
    for soup in soups:
        title_spans = soup.find(
            'div', class_='lister-list').find_all('span', class_='lister-item-header')
        for element in title_spans:
            titles_links.append(element.find('a').get('href'))
    return titles_links


def get_title(soup):
    """Returns the movie's title if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find('h1'):
        raw_text = soup.find('h1').text.strip()
        return clean_title(raw_text)
    return None


def get_country(soup):
        """Returns the movie's country(ies).

        Only returns a specified list of countries: Japan, USA, or Japan/USA.
        Otherwise, returns None.

        Args:
            soup: The soup object for that movie's imdb.com page.
        """
    for element in soup.find_all('h4'):
        if 'Country:' in element:
            raw_text = element.findParent().text.strip()
            if ('Japan' in raw_text) and ('USA' in raw_text):
                return 'Japan, USA'
            if 'Japan' in raw_text:
                return 'Japan'
            if 'USA' in raw_text:
                return 'USA'
    return None


def get_runtime(soup):
    """Returns the movie's runtime if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    for element in soup.find_all('h4'):
        if 'Runtime:' in element:
            raw_text = element.findNext().text
            runtime = int(raw_text.split()[0])
            return runtime
    return None


def get_budget(soup):
    """Returns the movie's budget if available.

    Any budget not denominated in USD is converted to USD.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find(text='Budget:'):
        raw_text = soup.find(
            text='Budget:').findParent().findParent().text.strip()
        budget = clean_budget(raw_text)
        if '$' in budget:
            return dollars_to_int(budget)
        return fx_to_dollars_int(budget)
    return None


def get_global_gross(soup):
    """Returns the movie's worldwide box office gross if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    for element in soup.find_all('h4'):
        if 'Cumulative Worldwide Gross:' in element:
            raw_text = element.findParent().text.strip()
            raw_text = raw_text.replace('Cumulative Worldwide Gross: ', '')
            raw_text = remove_commas(raw_text)
            return dollars_to_int(raw_text)
    return None


def get_mpaa_rating(soup):
    """Returns the movie's MPAA rating if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    ratings = ['G', 'PG', 'PG-13', 'R', 'TV-Y', 'TV-Y7', 'TV-Y7 FV',
               'TV-G', 'TV-PG', 'TV-14' 'TV-MA']
    if soup.find('div', class_='subtext'):
        rating = soup.find('div', class_='subtext').text.strip().split()[0]
        if rating in ratings:
            return rating
    return None


def get_japan_release_date(soup):
    """Returns the movie's Japan release date if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find(href='/calendar/?region=jp'):
        raw_text = soup.find(href='/calendar/?region=jp').findNext().text
        return to_datetime(raw_text)
    return None


def get_usa_release_date(soup):
    """Returns the movie's USA release date if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find(title='See more release dates'):
        raw_text = soup.find(
            title='See more release dates').text.strip().replace(' (USA)', '')
        return raw_text
    return None


def get_genres(soup):
    """Returns a string of the movie's genres if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find(text='Genres:'):
        raw_text = soup.find(
            text='Genres:').findParent().findParent().text.strip()
        return clean_genres(raw_text)
    return None


def get_user_rating(soup):
    """Returns the movie's imdb.com user rating if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find('span', itemprop='ratingValue'):
        return float(soup.find('span', itemprop='ratingValue').text)
    return None


def get_user_rating_count(soup):
    """Returns the movie's imdb.com user rating count (i.e. the number of user
    ratings) if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find(itemprop='ratingCount'):
        raw_text = soup.find(itemprop='ratingCount').text
        return int(remove_commas(raw_text))
    return None


def get_oscar_wins(soup):
    """Returns the number of Oscar (aka Academy Award) wins for a movie
    if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find('span', class_='awards-blurb'):
        if 'Won' in soup.find('span', class_='awards-blurb').text:
            raw_text = soup.find('span', class_='awards-blurb').text.strip()
            for string in raw_text.split():
                if string.isdigit():
                    return int(string)
    return None


def get_non_oscar_wins(soup):
    """Returns the number of non-Oscar wins for a movie if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find('span', class_='awards-blurb'):
        if ('Oscar' in soup.find('span', class_='awards-blurb').text) and \
                (soup.find('span', class_='awards-blurb').findNextSibling()):
            raw_text = soup.find(
                'span', class_='awards-blurb').findNextSibling().text.strip()
            if 'win' in raw_text:
                for string in raw_text.split():
                    if string.isdigit():
                        return int(string)
        raw_text = soup.find('span', class_='awards-blurb').text.strip()
        if 'win' in raw_text:
            for string in raw_text.split():
                if string.isdigit():
                    return int(string)
    return None


def get_metascore(soup):
    """Returns the movie's metascore if available.

    Args:
        soup: The soup object for that movie's imdb.com page.
    """
    if soup.find('div', class_='metacriticScore'):
        return int(soup.find('div', class_='metacriticScore').text.strip())
    return None


def clean_title(string):
    return re.sub('\\xa0.+', '', string)


def clean_budget(string):
    string = string.replace('Budget:', '')
    string = remove_commas(string)
    return re.sub('\\n.+', '', string)


def remove_commas(string):
    return string.replace(',', '')


def clean_genres(string):
    string = string.replace('Genres:', '')
    string = re.sub('\\n ', '', string)
    return re.sub('\\xa0\|', ', ', string)


def to_datetime(datestring):
    return dateutil.parser.parse(datestring)


def dollars_to_int(dollars_string):
    dollars_string = dollars_string.replace('$', '')
    return int(dollars_string)


def fx_to_dollars_int(budget):
    """Converts a non-USD denominated budget into USD.

    Accepts budget as a str and returns budget as an int denominated in USD.

    Args:
        budget: The non-USD denominated budget as a str.
    """
    c = CurrencyRates()
    jul_10_2020 = datetime(2020, 7, 10)
    budget = c.convert(budget[:3], 'USD', int(budget[3:]), jul_10_2020)
    return budget
