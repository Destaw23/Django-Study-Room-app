# Deployment

## Local development

Install dependencies and run the development server from the repository root:

```powershell
python -m pip install -r requirements.txt
$env:DJANGO_DEBUG = "true"
python manage.py migrate
python manage.py runserver
```

For a quick local start, `python manage.py runserver` enables debug mode when `DJANGO_DEBUG` is unset. Other management commands use the configured environment, so set `DJANGO_DEBUG=true` before running migrations or creating an admin account locally. SQLite is used when `DATABASE_URL` is unset, and a temporary development-only secret is generated automatically. Production WSGI deployments still require explicit production settings.

## Production environment

Set these environment variables in the hosting provider's secret/configuration settings:

| Variable | Required | Example |
| --- | --- | --- |
| `DJANGO_DEBUG` | Yes | `false` |
| `DJANGO_SECRET_KEY` | Yes | Generate a unique value with the command below |
| `DJANGO_ALLOWED_HOSTS` | Yes | `studyroom.example.com,www.studyroom.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | For cross-origin forms | `https://studyroom.example.com` |
| `DATABASE_URL` | Yes | PostgreSQL: `postgresql://user:password@host:5432/studyroom`; SQLite for a single-host, low-traffic deployment: `sqlite:////absolute/path/db.sqlite3` |
| `DJANGO_TRUST_X_FORWARDED_PROTO` | If TLS ends at a trusted proxy | `true` |
| `DJANGO_MEDIA_ROOT` | If using a persistent media volume | `/var/lib/studyroom/media` |
| `DJANGO_HSTS_INCLUDE_SUBDOMAINS` | Only if every subdomain uses HTTPS | `true` |
| `DJANGO_HSTS_PRELOAD` | Only if meeting browser preload requirements | `true` |

Generate a secret locally, then store its output as `DJANGO_SECRET_KEY` in the hosting provider. Do not commit it:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Production settings reject missing secret keys, hostnames, or database URLs. SQLite is supported when `DATABASE_URL` contains an absolute filesystem path; use it only for a small, single-host deployment. For production workloads needing concurrent writes, multiple app instances, or easier managed backups, use PostgreSQL. `DJANGO_TRUST_X_FORWARDED_PROTO=true` is only safe when the trusted proxy overwrites the forwarded-protocol header. HTTPS redirection and secure session/CSRF cookies are enabled when debug mode is off. HSTS is enabled for one year; deploy only after HTTPS is working for the domain.

Subdomain HSTS and browser preload are disabled by default; enable them only after verifying that all affected hostnames support HTTPS. Django's deploy check reports these as advisory warnings until then.

## Release and start

Run these commands as the hosting provider's release/build steps, then start the web process with the included `Procfile`:

```sh
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Create the initial admin account with `python manage.py createsuperuser`. Static assets are served by WhiteNoise. User-uploaded media needs durable storage: configure `DJANGO_MEDIA_ROOT` to a persistent volume or integrate an object-storage service before relying on profile uploads in production.

Use the platform's managed PostgreSQL backups, HTTPS, environment-variable storage, and application logs. Do not deploy with `DEBUG=true` or commit `.env`, database files, or uploaded media.

## PythonAnywhere free plan

PythonAnywhere serves Django through a Web-tab WSGI configuration. The free Beginner plan is suitable for trying the site or a small demo, not a dependable production service: current limits include one web app, 100 CPU seconds, 512 MB of disk, restricted outbound internet, and an account that expires after one month. Free accounts created on or after 15 January 2026 (8 January for EU accounts) do not include MySQL, so this guide uses SQLite. Check PythonAnywhere's [current plan comparison](https://www.pythonanywhere.com/pricing/) before deployment because plan limits can change.

### 1. Push the project to GitHub

PythonAnywhere can clone a GitHub repository. Push the version you intend to deploy first, including `media/icon/Studyroom.png`. Do not push `.env`, secrets, a local database, or user-uploaded media. Confirm that your intended deployment changes are committed; do not blindly commit generated files or database deletions.

### 2. Create the project and virtual environment

Create a free PythonAnywhere account, then open a **Bash console** and clone your repository:

```sh
git clone https://github.com/Destaw23/StudyRoom-by-using-Django.git StudyRoom
cd ~/StudyRoom
```

In the Web tab, add a web app using **Manual configuration** and choose a Python version offered there. In the Bash console, create the virtual environment with that same version (replace `3.X`):

```sh
mkvirtualenv --python=/usr/bin/python3.X studyroom-venv
cd ~/StudyRoom
pip install -r requirements.txt
```

If `mkvirtualenv` is unavailable, follow PythonAnywhere's [virtualenv setup instructions](https://help.pythonanywhere.com/pages/VirtualenvsExplained/). In the Web tab, set the virtualenv to `studyroom-venv`; set both **Source code** and **Working directory** to `/home/USERNAME/StudyRoom`.

### 3. Configure the PythonAnywhere WSGI file

Open the WSGI file linked from the Web tab. This is a separate file under `/var/www/`; it is **not** `studybud/wsgi.py`. Replace `USERNAME` below with your PythonAnywhere username and set a unique secret generated by `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` inside the virtualenv:

```python
import os
import sys

project_home = '/home/USERNAME/StudyRoom'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'studybud.settings'
os.environ['DJANGO_DEBUG'] = 'false'
os.environ['DJANGO_SECRET_KEY'] = 'PASTE_YOUR_GENERATED_SECRET_HERE'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'USERNAME.pythonanywhere.com'
os.environ['DATABASE_URL'] = 'sqlite:////home/USERNAME/StudyRoom/db.sqlite3'
os.environ['DJANGO_MEDIA_ROOT'] = '/home/USERNAME/StudyRoom/media'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Use the same secret and values in the Bash console before running management commands; WSGI environment variables are not automatically available in a separate console. Do not commit this WSGI file or secret to GitHub. HTTPS redirection is enabled in production. Only set `DJANGO_TRUST_X_FORWARDED_PROTO=true` if PythonAnywhere confirms that its trusted proxy overwrites the forwarded-protocol header; do not enable it based on an untrusted client header.

### 4. Run setup commands

In the Bash console, activate the virtualenv and export the same values (replace the username and secret):

```sh
workon studyroom-venv
cd ~/StudyRoom
export DJANGO_DEBUG=false
export DJANGO_SECRET_KEY='PASTE_THE_SAME_GENERATED_SECRET_HERE'
export DJANGO_ALLOWED_HOSTS='USERNAME.pythonanywhere.com'
export DATABASE_URL='sqlite:////home/USERNAME/StudyRoom/db.sqlite3'
export DJANGO_MEDIA_ROOT='/home/USERNAME/StudyRoom/media'
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

The SQLite URL must use four slashes before `/home/...` so Django receives an absolute Linux path. Keep the database and `media/` directory in your home directory; back them up regularly.

### 5. Map static files and uploads

After `collectstatic` finishes, in the Web tab's **Static files** section add:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/USERNAME/StudyRoom/staticfiles` |
| `/media/` | `/home/USERNAME/StudyRoom/media` |

This serves the project's collected CSS/JavaScript and uploaded profile images. Files in `/media/` are publicly retrievable by URL, so keep private files outside that directory. Click **Reload** in the Web tab after saving the mappings and WSGI file.

### 6. Verify the deployment

Open `https://USERNAME.pythonanywhere.com/`, sign in, test profile-image uploads, and visit `/admin/`. If the site fails, inspect the **error log** linked from the Web tab. If you update the code later, pull the changes, run migrations and `collectstatic` when needed, then reload the web app.

For official details, see PythonAnywhere's guides for [deploying an existing Django project](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/) and [Django static files](https://help.pythonanywhere.com/pages/DjangoStaticFiles/).
