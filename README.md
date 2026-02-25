# turbines

A static site generator built with Jinja2.

Inspired by [Cactus](https://github.com/koenbok/Cactus), a project that is no longer maintained.

## What is turbines?

Turbines is a static site generator that allows you to create websites using Jinja-based HTML templates and markdown files. Turbines makes it easy to deploy your site to services like Cloudflare Pages or AWS S3. It supports live reloading during development.

## Usage

To install turbines, run:

```bash
pip install turbines
```

or

```bash
uv add turbines
```

To create a new site, run:

```bash
turbines create mysite
cd mysite
```

To build the site, run:

```bash
turbines build
```

To serve the site with live reloading, run:

```bash
turbines serve
```

## Templates

Templates are written in Jinja2. You can use any Jinja2 syntax in your templates.

### Variables

The `site` variable is available in all templates and contains information about the site current site, such as the `url` and the `title`.
The `pages` variable is also available and contains a map of tags and the pages that have those tags.
For example, `pages.tages.articles` would give you a list of all pages that have the `articles` tag.
The `context` variable contains the context set in `config.yaml`.

### Functions

The `url_for` function is available in all templates and can be used to generate URLs for pages. For example, `{% url "test.md" %}` would give you the URL for the page generated from `test.md`.

The `static` function is also available and can be used to generate URLs for static files. For example, `{% static "style.css" %}` would give you the URL for the `style.css` file in the `static` directory.

## Examples

None yet. Coming soon!

## Compatibility

Turbines is built with Python 3.12.
