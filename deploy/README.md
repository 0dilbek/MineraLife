# MineraLife VPS deployment

This deployment runs Gunicorn on private port `8027`. Nginx sends only requests
for `mineralife.uz` to that port, so other virtual hosts on the server remain
independent.

## 1. DNS

Create an `A` record for `mineralife.uz` pointing to the VPS public IPv4 address.
Wait until this command returns that address:

```bash
getent ahostsv4 mineralife.uz
```

## 2. Install the application

Run as a sudo-enabled user on the VPS. The repository is expected at
`/home/MineraLife`.

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libjpeg-dev zlib1g-dev postgresql postgresql-contrib nginx certbot python3-certbot-nginx

sudo useradd --system --home-dir /home/MineraLife --shell /usr/sbin/nologin mineralife 2>/dev/null || true
sudo chown -R mineralife:mineralife /home/MineraLife

sudo -u mineralife python3 -m venv /home/MineraLife/.venv
sudo -u mineralife /home/MineraLife/.venv/bin/pip install --upgrade pip
sudo -u mineralife /home/MineraLife/.venv/bin/pip install -r /home/MineraLife/requirements.txt
```

## 3. Create the PostgreSQL database

Keep PostgreSQL bound to localhost; port `5432` does not need to be opened in the
VPS firewall. Start PostgreSQL and open its administrative console:

```bash
sudo systemctl enable --now postgresql
sudo -u postgres psql
```

Run the following inside `psql`. The `\password` command prompts securely for a
password; use the same password later in `/etc/mineralife.env`.

```sql
CREATE ROLE mineralife LOGIN;
\password mineralife
CREATE DATABASE mineralife OWNER mineralife ENCODING 'UTF8' TEMPLATE template0;
\q
```

Test the new login (it will ask for the password):

```bash
psql -h 127.0.0.1 -U mineralife -W -d mineralife -c 'SELECT 1;'
```

If the role or database already exists, do not recreate it. Reset only the role
password with `sudo -u postgres psql` followed by `\password mineralife`.

## 4. Configure the application

Use the existing `.env.production` if it already contains the correct secrets.
Otherwise start from `deploy/environment.example`. Install the final file outside
the Git checkout as `/etc/mineralife.env`. It must contain at least:

```dotenv
DEBUG=False
SECRET_KEY=a-long-random-value
ALLOWED_HOSTS=mineralife.uz
CSRF_TRUSTED_ORIGINS=https://mineralife.uz
DB_ENGINE=postgresql
DB_NAME=mineralife
DB_USER=mineralife
DB_PASSWORD=the-password-entered-in-psql
DB_HOST=127.0.0.1
DB_PORT=5432
```

Install the environment file. For a brand-new installation, use the example
instead of `.env.production`:

```bash
sudo install -o root -g mineralife -m 640 /home/MineraLife/.env.production /etc/mineralife.env
# Fresh installation alternative:
# sudo install -o root -g mineralife -m 640 /home/MineraLife/deploy/environment.example /etc/mineralife.env
```

If MySQL or SQLite already contains application data, export it before editing
the database settings. Stop writes, preserve the old environment, and create a
Django fixture:

```bash
sudo systemctl stop mineralife 2>/dev/null || true
sudo cp --preserve=mode,ownership /etc/mineralife.env /etc/mineralife.env.before-postgresql
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env.before-postgresql /home/MineraLife/.venv/bin/python /home/MineraLife/manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --output /tmp/mineralife-data.json
```

Skip those three commands for an empty installation. Now edit the production
copy, create the PostgreSQL schema, and collect static files:

```bash
sudoedit /etc/mineralife.env
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env /home/MineraLife/.venv/bin/python /home/MineraLife/manage.py check --deploy
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env /home/MineraLife/.venv/bin/python /home/MineraLife/manage.py migrate
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env /home/MineraLife/.venv/bin/python /home/MineraLife/manage.py collectstatic --noinput
```

If `/tmp/mineralife-data.json` was created, load it after `migrate`:

```bash
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env /home/MineraLife/.venv/bin/python /home/MineraLife/manage.py loaddata /tmp/mineralife-data.json
```

Check record counts and the admin panel before deleting the old database, its
native backup, or the temporary JSON export.

In `sudoedit`, verify that the production copy has these exact domain values:

```dotenv
ALLOWED_HOSTS=mineralife.uz
CSRF_TRUSTED_ORIGINS=https://mineralife.uz
```

Also remove an old `USE_MYSQL=True` line or set it to `False`. `DB_ENGINE` takes
priority, but removing the obsolete setting avoids confusion.

## 5. Enable Gunicorn and Nginx

First confirm that port `8027` is free. If it is occupied, change `8027` in both
deployment files to another unused localhost port.

```bash
sudo ss -ltnp | grep ':8027 ' || true
sudo cp /home/MineraLife/deploy/mineralife.service /etc/systemd/system/mineralife.service
sudo systemctl daemon-reload
sudo systemctl enable --now mineralife
sudo systemctl status mineralife --no-pager

sudo cp /home/MineraLife/deploy/mineralife.nginx /etc/nginx/sites-available/mineralife.uz
sudo ln -s /etc/nginx/sites-available/mineralife.uz /etc/nginx/sites-enabled/mineralife.uz
sudo nginx -t
sudo systemctl reload nginx
```

Do not add `default_server` to this Nginx site: `server_name mineralife.uz` is what
keeps traffic for the server's other domains separate.

## 6. HTTPS

After DNS resolves and HTTP works, request and install the certificate:

```bash
sudo certbot --nginx -d mineralife.uz
sudo certbot renew --dry-run
```

## Updates

Back up the database, then run:

```bash
cd /home/MineraLife
sudo -u mineralife git pull --ff-only
sudo -u mineralife .venv/bin/pip install -r requirements.txt
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env .venv/bin/python manage.py migrate
sudo -u mineralife env DJANGO_ENV_FILE=/etc/mineralife.env .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart mineralife
sudo systemctl reload nginx
```

## Secret files

`.env` and `.env.production` are already tracked by Git in this repository even
though `.gitignore` lists them. After `/etc/mineralife.env` is in place, rotate
all exposed credentials and remove both files from Git tracking in the development
checkout:

```bash
git rm --cached .env .env.production
git commit -m "Stop tracking environment secrets"
```

This keeps local copies but removes them from future commits. Existing Git history
still contains the old values, which is why credential rotation is required.

Useful diagnostics:

```bash
sudo journalctl -u mineralife -n 100 --no-pager
sudo tail -n 100 /var/log/nginx/error.log
curl -I -H 'Host: mineralife.uz' http://127.0.0.1
```
