# Pydgeot
Pydgeot is a low-frills static website generator with fairly limited plugin support. It is still under active
development; any suggestions/criticisms/yellings are more than welcome.

### Features
- Tracks file changes, so only files that need to be updated are touched.
- File system watcher to build content on-the-fly.
- File processor and command plugins.
- Built-in [Jinja2 template](http://jinja.pocoo.org/docs/) and [LESS CSS](http://lesscss.org/) processors.

### Limitations
- Built-in processors do not track site structure, and no context variables are available.

### Requirements
- Python 3.*
- [DocOpt](https://github.com/docopt/docopt)

Additionally, the built-in Jinja2 and Lesscpy processors require [Jinja2](https://github.com/mitsuhiko/jinja2) and
[Lesscpy](https://github.com/robotis/Lesscpy), respectively.

### Installation
```bash
git clone https://github.com/broiledmeat/pydgeot.py pydgeot
cd pydgeot
python setup.py install
```

### Usage
Pydgeot not only needs content to generate, but a place to store working files and configuration for the associated
content. All this data is stored in what Pydgeot calls an 'app' directory. An app directory contains the source content,
the built content, configuration, working data, and any plugins specific to the app. A new
[app directory](#_app_directories) can be created with the 'create' command.

```bash
pydgeot create [PATH]
```

This generates an empty configuration, and without at least specifying some plugins, nothing will be generated. Read the
[configuration section](#_configuration) to get started.

Once configuration is done, and content has been placed in the source content directory, Pydgeot can build content with
the 'build' command.
```bash
pydgeot build -a [APP_PATH]
```
`APP_PATH` should be the location of your app directory generated with the 'create' command. By default `APP_PATH` is
the current working directory.

To have Pydgeot watch the source content directory, and build files as they are added or changed, use the 'watch'
command.
```bash
pydgeot watch -a [APP_PATH]
```

Running Pydgeot always requires a command as the first argument. To see a list of available commands, use 'commands'.
```bash
pydgeot commands
```

### App Directories<a id="_app_directories"></a>
A Pydgeot app directory contains the following directories and files.

- `source/` Source content
- `build/` Content built from the `source/` directory
- `store/` Working data store for Pydgeot and plugins
- `store/log/` Log files
- `plugins/` Plugins to be available
- `pydgeot.json` Configuration file

### Configuration<a id="_configuration"></a>
Pydgeot keeps a single JSON configuration file for itself and plugins. Before Pydgeot will do anything of use, the
configuration file must have at least the `plugins` field set (which is also the only field Pydgeot currently reads.)

- `plugins`
  A list of plugins load. The names must be the name of a python file, without an extension. A simple configuration
  file specifying only loading Pydgeots built-in plugins would look like:

  ```json
  {
    'plugins': ['jinja', 'lesscss', 'copyfallback']
  }
  ```

### Plugins
Pydgeot plugins are optional modules that may add commands and/or file processors. Pydgeot does come with a few built-in
plugins, but more can be loaded by including them in the apps plugin directory, and added them to the configurations
`plugins` list.

#### Built-In Plugins
- [Jinja2](https://github.com/mitsuhiko/jinja2)
  Simple Jinja2 template file processor. Does not add any context variables or keep track of site structure.
  `{% set template_only = True %}` can be added to a template file to cause it to not be built (but will still update
  any other template files that are based on it to render when updated.)
- [Lesscpy](https://github.com/robotis/Lesscpy)
  LessCPY file processor.
- CopyFallback
  Simply copies any files not handled by other file processors.
