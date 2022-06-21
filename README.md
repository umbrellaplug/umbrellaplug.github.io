Tutorial and example repository for setting up a GitHub-hosted Kodi repo. For an example of a repo created using this method (including submodules), see https://www.github.com/jurialmunkey/repository.jurialmunkey/.

# BASIC - How to setup for hosting on GitHub Pages

In order to follow this tutorial, first [use this repository as a template](https://github.com/drinfernoo/repository.example/generate) for a new repository, and then clone your newly created repository locally. For the simplest file manager source URL, it is recommended to name your newly created repository as `YOUR_USERNAME_HERE.github.io`.

### Creating your repository add-on
---
First, you'll need to edit the `addon.xml` file within the `/repo/repository.example` folder with your chosen add-on ID, a version number, and your username (or whatever you'd like) for `provider`, as seen on line 2:

```XML
<addon id="ADDON_ID_HERE" name="REPO_NAME_HERE" version="VERSION_NUMBER_HERE" provider-name="YOUR_USERNAME_HERE">
```

You also need to replace `YOUR_USERNAME_HERE`, `REPOSITORY_NAME_HERE`, and `BRANCH_NAME_HERE` with your GitHub username, this repository's name, and the name of the branch (it's recommended to use the default branch, ususally `master` or `main`) respectively, as seen on lines 4-8:

```XML
<dir>
    <info compressed="false">https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/BRANCH_NAME_HERE/repo/zips/addons.xml</info>
    <checksum>https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/BRANCH_NAME_HERE/repo/zips/addons.xml.md5</checksum>
    <datadir zip="true">https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/BRANCH_NAME_HERE/repo/zips/</datadir>
</dir>
```

You should also change the summary and description of your repository, as seen on lines 11-12:

```XML
<summary>REPO_NAME_HERE</summary>
<description>DESCRIPTION OF YOUR REPO HERE</description>
```

While not required, it is also recommended to replace `icon.png` and `fanart.jpg` in the `repository.example` folder with art relevant to your repository or the add-ons contained within. `icon.png` should be 512x512 px, and `fanart.jpg` should be 1920x1080 px, or a similar ratio.

Finally, rename the `repository.example` folder to match whatever add-on ID you chose earlier.

### Adding add-ons to your repository
---
To build the repository, first place the add-on source folders for whichever add-ons you'd like to be contained in your Kodi repo inside this repository. For ease of updating included add-ons, the recommended method of doing this is via [Git Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules), which are supported by many Git clients, as well as the Git terminal. If you choose not to use submodules, you'll need to simply copy the source folders directly into this repository.

The `_repo_xml_generator.py` script included in this repository with build `.zip` files for each included add-on, as well as generating the necessary `addons.xml` and `addons.xml.md5` files, so that Kodi can infer the contents of the repo. It is designed to handle multiple versions of Kodi (for example, to serve different add-ons to Leia than are served to Matrix), and single repositories that serve the same add-ons to all Kodi versions.

##### Same add-ons to all versions (default)
---
Place your add-on source folders in the `repo` folder of this repository.
##### Different add-ons to different versions (advanced)
---
Place your add-on source folders into a folder named after the version of Kodi you wish to serve from it, instead of `/repo`. For example, `/leia` for a Leia-focused repo, or `/matrix` for a Matrix-focused one. In order for your repository to be able to differentiate which add-ons to serve, you'll need to add a new `dir` section to your `addon.xml`, that defines which versions should be served.

For example, to serve Leia only:
```XML
<dir minversion="18.0.0" maxversion="18.9.9">
    <info compressed="false">https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/DEFAULT_BRANCH_NAME_HERE/leia/zips/addons.xml</info>
    <checksum>https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/DEFAULT_BRANCH_NAME_HERE/leia/zips/addons.xml.md5</checksum>
    <datadir zip="true">https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/DEFAULT_BRANCH_NAME_HERE/leia/zips/</datadir>
</dir>
```
And for Matrix and up:
```XML
<dir minversion="19.0.0">
    <info compressed="false">https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/DEFAULT_BRANCH_NAME_HERE/matrix/zips/addons.xml</info>
    <checksum>https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/DEFAULT_BRANCH_NAME_HERE/matrix/zips/addons.xml.md5</checksum>
    <datadir zip="true">https://raw.githubusercontent.com/YOUR_USERNAME_HERE/REPOSITORY_NAME_HERE/DEFAULT_BRANCH_NAME_HERE/matrix/zips/</datadir>
</dir>
```
---
After adding your source folders, simply run `_repo_generator.py`. This will create `.zip`s of all of the desired add-ons, and place them in subfolders called `zips`, along with the generated `addons.xml` and `addons.xml.md5`. As of version 3, this script can create distributions for Krypton, Leia, Matrix, and Nexus, as well as the generic "repo", which is intended to serve to any version (like for the repository itself, or any cross-version libraries and dependencies).

### Make your repository zip installable inside Kodi
---
Copy the zip file of your repository, located at `REPO_FOLDER/zips/ADDON_ID_HERE/ADDON_ID_HERE-VERSION_NUMBER_HERE.zip`,
and paste it into the root folder.

Edit the link inside `index.html` to reflect your add-on's filename, as seen on line 1:

```HTML
<a href="ADDON_ID_HERE-VERSION_NUMBER_HERE.zip">ADDON_ID_HERE-VERSION_NUMBER_HERE.zip</a>
```

After committing and pushing these changes to your repo, go to the "Settings" section for this repository on GitHub. In the first box, labeled "Repository name", change your repository's name. Generally, GitHub Pages repositories are named `YOUR_USERNAME_HERE.github.io`,  but it can be whatever you'd like.
Next, scroll down to the "GitHub Pages" section, choose the default branch (or whichever you chose when modifying your `addon.xml`) as the source, and click "Save".

After that, you should be all done!

If you named this repository `YOUR_USERNAME_HERE.github.io` (as recommended), your file manager source will be:

`https://YOUR_USERNAME_HERE.github.io/`

If you named it something else, it will be:

`https://YOUR_USERNAME_HERE.github.io/REPOSITORY_NAME_HERE/`

# ADVANCED - How to set up for hosting without GitHub Pages

If you want to host your Kodi repo on a different host besides GitHub Pages, simply download this repository as a `.zip`, and unzip it, rather than using it as a template. Continue to follow the rest of the setup procedure, except for the setting up of GitHub Pages. The only differences will be in your `addon.xml` file, as it will need to reference your host, rather than GitHub:

```XML
<dir>
    <info compressed="false">https://YOUR_HOST_URL_HERE/repo/zips/addons.xml</info>
    <checksum>https://YOUR_HOST_URL_HERE/repo/zips/addons.xml.md5</checksum>
    <datadir zip="true">https://YOUR_HOST_URL_HERE/repo/zips/</datadir>
</dir>
```

And upload the contents of this repository to your host. It is **very important** that `YOUR_HOST_URL_HERE` is the URL to the *root* folder of this repository.

After doing so, your file manager source will be:

`https://YOUR_HOST_URL_HERE/`
