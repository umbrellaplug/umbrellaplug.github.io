"""Year discovery queries, independent of Kodi UI and metadata enrichment."""
import json
import re
from datetime import date
from urllib.parse import urlencode

import requests

IMDB_ENDPOINT = 'https://caching.graphql.imdb.com/'
SORTS = ('votes', 'popular', 'rating')


def minimum_votes(value, default):
    try:
        return max(0, min(int(value), 1000000))
    except (TypeError, ValueError):
        return default


def validate(year, sort):
    year = int(year)
    if not 1901 <= year <= date.today().year or sort not in SORTS:
        raise ValueError('Invalid movie year or sort')
    return year


def tmdb_url(base, today, year, sort, votes=500, language='', countries='', media='movie'):
    year = validate(year, sort)
    params = {'language': 'en-US', 'region': 'US', 'primary_release_year': year,
              'primary_release_date.lte': today, 'include_adult': 'false',
              'sort_by': {'votes': 'vote_count.desc', 'popular': 'popularity.desc',
                          'rating': 'vote_average.desc'}[sort],
              'vote_count.gte': minimum_votes(votes, 500)}
    if media == 'tv':
        params.pop('region')
        params.pop('primary_release_year')
        params.pop('primary_release_date.lte')
        params.update({'first_air_date_year': year, 'first_air_date.lte': today,
                       'include_null_first_air_dates': 'false'})
    if language:
        params['with_original_language'] = language
    if countries:
        params['with_origin_country'] = countries
    # Umbrella's TMDb indexer advances pages by replacing the final &page= suffix.
    params['page'] = 1
    return base + '/3/discover/%s?api_key=%%s&' % media + urlencode(params, safe='|')


def imdb_query(year, sort, votes=10000, language='', countries='', cursor='', limit=20, media='movie'):
    year = validate(year, sort)
    constraints = {
        'titleTypeConstraint': {'anyTitleTypeIds': ['tvSeries', 'tvMiniSeries'] if media == 'tv' else ['movie', 'tvMovie']},
        'releaseDateConstraint': {'releaseDateRange': {
            'start': '%s-01-01' % year, 'end': min('%s-12-31' % year, date.today().isoformat())}},
        'userRatingsConstraint': {'ratingsCountRange': {'min': minimum_votes(votes, 10000)}}}
    if language:
        constraints['languageConstraint'] = {'anyPrimaryLanguages': [language]}
    if countries:
        constraints['originCountryConstraint'] = {'anyCountries': countries.split('|')}
    # GraphQL input object keys are unquoted; JSON retains safe escaping for values.
    inputs = re.sub(r'"([A-Za-z][A-Za-z0-9]*)":', r'\1:', json.dumps(constraints))
    sort_by, order = {'votes': ('USER_RATING_COUNT', 'DESC'),
                      'popular': ('POPULARITY', 'ASC'), 'rating': ('USER_RATING', 'DESC')}[sort]
    after = ', after: %s' % json.dumps(cursor) if cursor else ''
    return '''{ advancedTitleSearch(first: %d%s, sort: {sortBy: %s, sortOrder: %s},
        constraints: %s) { pageInfo { hasNextPage endCursor }
        edges { node { title { id titleText { text } originalTitleText { text }
        releaseYear { year } ratingsSummary { aggregateRating voteCount } } } } } }''' % (
            max(1, min(int(limit), 100)), after, sort_by, order, inputs)


def imdb_page(year, sort, votes=10000, language='', countries='', cursor='', limit=20, media='movie'):
    response = requests.post(IMDB_ENDPOINT, json={'query': imdb_query(
        year, sort, votes, language, countries, cursor, limit, media)}, headers={
            'User-Agent': 'Mozilla/5.0', 'Origin': 'https://www.imdb.com',
            'Referer': 'https://www.imdb.com/', 'Accept-Language': 'en-US,en;q=0.9'}, timeout=(10, 20))
    response.raise_for_status()
    payload = response.json()
    if payload.get('errors'):
        raise ValueError('IMDb returned GraphQL errors')
    result = payload['data']['advancedTitleSearch']
    items = []
    for edge in result['edges']:
        title = edge['node']['title']
        if not re.fullmatch(r'tt\d+', title.get('id', '')):
            continue
        name = title['titleText']['text']
        ratings = title.get('ratingsSummary') or {}
        items.append({'title': name, 'originaltitle': (title.get('originalTitleText') or {}).get('text') or name,
                      'year': str((title.get('releaseYear') or {}).get('year') or year),
                      'imdb': title['id'], 'tmdb': '', 'tvdb': '',
                      'rating': ratings.get('aggregateRating') or '', 'votes': ratings.get('voteCount') or 0})
    page = result['pageInfo']
    next_cursor = page.get('endCursor') if page.get('hasNextPage') else ''
    if page.get('hasNextPage') and (not next_cursor or next_cursor == cursor):
        raise ValueError('IMDb returned an invalid pagination cursor')
    return items, next_cursor or ''
