# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'epanetparser'
author = 'Paul Slavin, Tomasz Janus'
copyright = '2022-2026, Paul Slavin and Tomasz Janus'

# Read the version from the installed distribution rather than hardcoding it.
# `import epanetparser` is deliberately avoided: importing the package runs
# initialize(), which writes a user configuration file as a side effect of
# building the docs.
from importlib.metadata import PackageNotFoundError, version as _dist_version

try:
    # The full version, including alpha/beta/rc tags
    release = _dist_version('epanetparser')
except PackageNotFoundError:  # docs built from an uninstalled source tree
    release = '0.0.0'

# The short X.Y version
version = '.'.join(release.split('.')[:2])


# -- General configuration ---------------------------------------------------
# Extensions.
# The theme is activated by name in `extensions` and `html_theme` below, so it
# is not imported here; a bare import would only add a way for conf.py to fail.
#
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon'
]

autodoc_member_order = 'bysource'
napoleon_custom_sections = [('Returns', 'params_style')]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = ['theme_override.css']
