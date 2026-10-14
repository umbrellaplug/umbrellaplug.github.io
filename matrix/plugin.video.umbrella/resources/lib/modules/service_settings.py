"""One-time migration of shared service preferences."""
PROVIDERS = ('trakt', 'simkl', 'mdblist', 'custom', 'floppy', 'scrob', 'punchplay')
DEFAULTS = {'trakt.directProgress.scrape': 'false', 'simkl.directProgress.scrape': 'false', 'mdblist.directProgress.scrape': 'false', 'custom.directProgress.scrape': 'false', 'floppy.directProgress.scrape': 'false', 'scrob.directProgress.scrape': 'false', 'punchplay.directProgress.scrape': 'false', 'trakt.progressFlatten': 'true', 'simkl.progressFlatten': 'false', 'mdblist.progressFlatten': 'false', 'custom.progressFlatten': 'true', 'trakt.paginate.lists': 'true', 'simkl.paginate.lists': 'true', 'mdblist.paginate.lists': 'true', 'custom.paginate.lists': 'true', 'floppy.paginate.lists': 'true', 'scrob.paginate.lists': 'true', 'punchplay.paginate.lists': 'true', 'trakt.general.notifications': 'true', 'simkl.general.notifications': 'false', 'mdblist.general.notifications': 'false', 'custom.general.notifications': 'true', 'floppy.general.notifications': 'true', 'scrob.general.notifications': 'true', 'punchplay.general.notifications': 'true'}
SUFFIXES = ('directProgress.scrape', 'progressFlatten', 'paginate.lists', 'general.notifications')


def choose(suffix, values):
    selected = values.get('indicators.alt', '0')
    provider = PROVIDERS[int(selected) - 1] if selected in ('1', '2', '3', '4', '5', '6', '7') else None
    key = (provider + '.' + suffix) if provider else ''
    if key in DEFAULTS and values.get(key) in ('true', 'false'):
        return values[key]
    for provider in PROVIDERS:
        key = provider + '.' + suffix
        if key in DEFAULTS and values.get(key) in ('true', 'false') and values[key] != DEFAULTS[key]:
            return values[key]
    return 'true' if suffix in ('progressFlatten', 'paginate.lists') else 'false'


def migrate(addon, profile):
    from xml.dom.minidom import parse
    import os
    path = os.path.join(profile, 'settings.xml')
    if not os.path.isfile(path): return
    nodes = parse(path).getElementsByTagName('setting')
    values = {node.getAttribute('id'): node.firstChild.data if node.firstChild else '' for node in nodes}
    for suffix in SUFFIXES:
        key = 'services.' + suffix
        if key not in values:
            addon.setSetting(key, choose(suffix, values))
