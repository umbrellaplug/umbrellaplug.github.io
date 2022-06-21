# repository.myaccounts

# Welcome to the *My Accounts* Project
Kodi developers one stop shop for common account information accessed under one roof that all addons can share.  This allows users to setup accounts once and addons access that data.
```
<dir>
    <info compressed="false">https://raw.githubusercontent.com/a4k-openproject/repository.myaccounts/master/zips/addons.xml</info>
    <checksum>https://raw.githubusercontent.com/a4k-openproject/repository.myaccounts/master/zips/addons.xml.md5</checksum>
    <datadir zip="true">https://raw.githubusercontent.com/a4k-openproject/repository.myaccounts/master/zips/</datadir>
</dir>
```

To add *My Accounts* as a deppendecy
add the following to your addon's addon.xml file between the `<requires></requires>` tag.

`<import addon="script.module.myaccounts" version="1.0.0" />`
Addon developers can access *My Accounts* as simply as

# How to call *My Accounts* settings 

You can use `import myaccounts` once the dependecy is added to your addon.  The following lists the functions that can be called that will respond with a dictionary and the supplied key and value.

### myaccount.getAll()
This function call will provide all available accounts as a dictionary for each account handled.  If we called `accounts = myaccounts.getAll()` The returned data will be as follows.
`accounts ={'premiumize': {'enabled': '', username': '', 'token': ''}, 'alldebrid': {'enabled': '', 'username': '', 'token': ''}, 'tmdb': {'username': '', 'password': '', 'api_key': '', 'session_id': ''},
	'realdebrid': {'enabled': '', 'username': '', 'token': '', 'secret': '', 'refresh': '', 'client_id': ''}, 'ororo': {'password': '', 'email': ''}, 'tvdb': {'api_key': ''}, 'filepursuit': {'api_key': ''},
	'trakt': {'username': '', 'token': '', 'expires': '', 'refresh': ''}, 'imdb': {'user': ''}, 'easyNews': {'username': '', 'password': ''}, 'furk': {'username': '', 'api_key': '', 'password': ''},
	'fanart_tv': {'api_key': ''}}`

### myaccount.getTrakt()
Returns trakt only account info
```trakt': {'username': '', 'token': '', 'expires': '', 'refresh': ''}```

### myaccount.getAllDebrid()
Returns all debrid account information supported (currently All-Debrid, Premiumize.me, Real-Debrid)
There is an addional key for each dictionary `'enabled'`.  This key could be used by the adon developer that the debrid service is temporarily disabled by the user.
`{premiumize': {'enabled': '', 'username': '', 'token': ''}, 'alldebrid': {'enabled': '', 'username': '', 'token': ''}, 'realdebrid': {'enabled': '', 'username': '', 'token': '', 'secret': '', 'refresh': '', 'client_id': ''}}`

### myaccount.getAD()
`alldebrid': {'enabled': '', 'username': '', 'token': ''}`
 
### myaccount.getPM()
`premiumize': {'enabled': '', 'username': '', 'token': ''}`
  
### myaccount.getRD()
`realdebrid': {'enabled': '', 'username': '', 'token': '', 'secret': '', 'refresh': '', 'client_id': ''}`

### myaccount.getAllMeta()
`{'tmdb': {'username': '', 'password': '', 'api_key': '', 'session_id': ''}, 'tvdb': {'api_key': ''}, 'imdb': {'user': ''}, 'fanart_tv': {'api_key': ''}}`

### myaccount.getFanart_tv()
`fanart_tv': {'api_key': ''}`

### myaccount.getTMDb()
`tmdb': {'username': '', 'password': '', 'api_key': '', 'session_id': ''}`

### myaccount.getTVDb()
`tvdb': {'api_key': ''}`

### myaccount.getIMDb()
`imdb': {'user': ''}`

### getAllScraper()
`{'ororo': {'password': '', 'email': ''}, 'filepursuit': {'api_key': ''}, 'easyNews': {'username': '', 'password': ''}, 'furk': {'username': '', 'api_key': '', 'password': ''}}`

### getFilepursuit()
`filepursuit: {'api_key': ''}`

### myaccount.getFurk()
`furk: {'username': '', 'api_key': '', 'password': ''}`

### myaccount.getEasyNews()
`easyNews: {'username': '', 'password': ''}`

### myaccount.getOrro()
`ororo: {'password': '', 'email': ''}`
