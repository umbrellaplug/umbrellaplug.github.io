"""Episode-specific air dates for display labels."""
from datetime import datetime, timezone


def date_label(meta, include_schedule, zone, short_day, time_format, convert):
	value = meta.get('premiered') or meta.get('firstaired')
	if not isinstance(value, str) or not value: return ''
	try:
		stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
	except ValueError:
		return ''
	has_time = 'T' in value or ' ' in value
	zone_from = meta.get('airzone')
	if stamp.tzinfo is not None:
		stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
		zone_from = 'utc'
	elif not has_time and meta.get('airtime') and zone_from:
		try:
			clock = datetime.strptime(meta['airtime'][:5], '%H:%M')
			stamp = stamp.replace(hour=clock.hour, minute=clock.minute)
			has_time = True
		except (ValueError, TypeError): pass
	parts = ['%Y-%m-%d']
	if include_schedule:
		parts.append('%a' if short_day else '%A')
		if has_time: parts.append({'1': '%I:%M', '2': '%I:%M %p'}.get(time_format, '%H:%M'))
	pattern = ' '.join(parts)
	if has_time and zone_from:
		zone_to = (meta.get('airzone') or zone_from) if zone == '1' else 'utc' if zone == '2' else 'local'
		result = convert(stringTime=stamp.strftime('%Y-%m-%dT%H:%M'), zoneFrom=zone_from,
			zoneTo=zone_to, formatInput='%Y-%m-%dT%H:%M', formatOutput=pattern)
		if result: return result
	return stamp.strftime(pattern)
