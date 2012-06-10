# Pydgeot
Pydgeot is a low-frills static website generator. It updates files as needed,
and passes some things through file handlers, and not much else.

Pydgeot is still under active development, and any
suggestions/criticisms/yelling is more than welcome.

***

### Features
- Tracks file changes, so only files that need to be updated are touched.
- [Jinja2](http://jinja.pocoo.org/docs/) template and
  [LESS](http://lesscss.org/) CSS support.
- A mostly superfluous simple development server.

### Limitations
- Content is not updated on the fly.
- Site structure is not tracked, and no context variables are available to
  templates. Note that template dependency *is* tracked, and parent/child
  templates will update appropriately.

### Planned
- Load user-definable file handler modules.
- Config files for source directories.

***

### Requirements
- Python 3.*
- Jinja2 *(Optional)*
- Lesscpy *(Optional)*

### Installation
    git clone https://github.com/broiledmeat/pydgeot.py pydgeot
    cd pydgeot
    python setup.py install

### Usage
The simplest use is to just generate contents from a source directory over to a
target directory.

    pydgeot-gen ~/source ~/target

On first use, this will copy (or pass things through file handlers) everything
over to the target directory. On subsequent uses, only files that need to be
updated will be changed.

By default, generation will check a '/.templates' directory for changes, but
will not copy over contents to a target directory. To change the list of ignored
file paths, a comma seperated list of regexes can be passed to pydgeot-gen.

    pydgeot-gen --ignore-matches ^\.templates(/.*)?$,^hiddenstuff\.*$ ~/source ~/target
