# Pydgeot
Pydgeot is a low-frills static content generator. It aims to be as simplistic as possible, primarily providing a core
set of functionality made available to plugins.

### Features
- Dependency tracking for content rebuilding.
- On-the-fly content building for development.

### Requirements
- Python 3.*
- [DocOpt](https://github.com/docopt/docopt)

### Installation
Pydgeot can be installed via pip:
```bash
pip install pydgeot
```

Or via source:
```bash
git clone https://github.com/broiledmeat/pydgeot.git pydgeot
cd pydgeot
python setup.py install
```

### Usage
Pydgeot not only needs content to generate, but a place to store working files and configuration for the associated
content. All this data is stored in an 'app' directory. An app directory contains the source and built content
subdirectories, a working and log directory, and a base configuration file. A new [app directory](#_app_directories) can
be created with the 'create' command.

```bash
pydgeot create [PATH]
```

This creates the given path, the required subdirectories, and an empty configuration file. The configuration file does
not load any plugins, and without modification, Pydgeot won't have anything to build. Read the
[configuration section](#_configuration) to get started modifying the configuration file.

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
- `pydgeot.json` Root configuration file

### Configuration<a id="_configuration"></a>
Pydgeot keeps a single JSON configuration file in the app directory, but allows nesting additional configuration files
within source directories. Configurations in source directories will be merged with parent configurations, overriding
any already set dictionary keys or values. Configuration files can be used by plugins, but Pydgeot itself only watches a
few directives.

- `plugins`
  Used only in the app directory configuration file. A list of Pydgeot plugins to load.

  ```json
  {
    "plugins": ["example", "other.example"]
  }
  ```

- `processors`
  A list of file processors to use for the containing directory and any subdirectories. These may be from the built in
  processors, or from additional loaded plugins.

  ```json
  {
    "plugins": ["jinja", "lesscss", "copy"]
  }
  ```

- `ignore`
  A list of [glob patterns](#_glob_patterns). Any file matching one of the patterns will not be processed.


### Glob Patterns<a id="_glob_patterns"></a>
Globs support the following special characters (which may be escaped, to ignore the special meaning.)

  - `?`  Match any single character (excluding path separator)
  - `*`  Match 0 or more characters (excluding path separators)
  - `**` Match 0 or more characters

  ```json
  {
    "ignore": ["*.pyc", "**.png", "**/example.py", "examp??.txt"]
  }
  ```

  - `*.pyc` Will match any `.pyc` file in the containing directory
  - `**.png` Will match any `.png` file in the containing directory, and any subdirectories
  - `**/example.py` Will match `example.py` files in subdirectories, but not the containing directory.
  - `examp??.txt` Will match `example.txt` and `examp00.txt` in the containing directory, but not `examp.txt` or
                  `examples.txt`


### Plugins
Pydgeot plugins are Python modules that may add commands and file processors. Pydgeot does come with a few built-in
plugins, but more can be loaded by adding them to the configurations `plugins` list.

#### Built-In Plugins
A minimal set of processors come built in. They do not need to be included in the configurations `plugins` list, but
must be enabled in the `processors` list.

- Copy Fallback, (configuration processor name: `copy`)
  Copies any files not handled by other file processors.
- Symlink Fallback, (configuration processor name: `symlink`)
  Creates symlinks for files not handled by other file processors.
