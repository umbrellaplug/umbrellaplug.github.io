"""Identify paused movie/episode sessions without depending on local bookmarks."""

def matching_sessions(items, imdb='', tmdb='', tvdb='', season=None, episode=None):
	if not isinstance(items, list): raise ValueError('Incomplete playback response')
	is_episode = episode not in (None, '', 'None')
	if not is_episode and season not in (None, '', 'None'):
		raise ValueError('Select an individual episode to clear its playback progress')
	ids = {k: str(v) for k, v in (('imdb', imdb), ('tmdb', tmdb), ('tvdb', tvdb)) if v not in (None, '', 'None', '0', 0)}
	if not ids: raise ValueError('Missing media identity')
	matches = []
	for item in items:
		if not isinstance(item, dict): raise ValueError('Invalid playback item')
		if item.get('type') != ('episode' if is_episode else 'movie'): continue
		remote = (item.get('show' if is_episode else 'movie') or {}).get('ids') or {}
		shared = [key for key in ('tmdb', 'imdb', 'tvdb') if key in ids and remote.get(key)]
		if not shared or ids[shared[0]] != str(remote[shared[0]]): continue
		if is_episode:
			ep = item.get('episode') or {}
			if int(ep.get('season', -1)) != int(season) or int(ep.get('number', ep.get('episode', -1))) != int(episode): continue
		if not item.get('id'): raise ValueError('Missing playback ID')
		matches.append(item)
	return matches
