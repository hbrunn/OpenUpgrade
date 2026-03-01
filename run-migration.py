#!/usr/bin/env python3
"""
Provide a oneliner to run a migration.
Consult the readme for details.
"""
import argparse
import getpass
import http.client
import json
import logging
import os
import shutil
import string
import subprocess
import sys
import tempfile
import time
import zipfile
from textwrap import dedent, indent
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# this is the version currently under development
# if you increase this, you'll have to update the
# templates dictionary below
experimental_version = "19.0"


def main(args):
    if not docker_compose:
        raise ValueError("no docker found")

    if os.path.exists("docker/docker-compose.yml"):
        logging.info("stopping existing containers")
        docker_compose("down", logfile=False, check=False)

    target_version = args.target_version
    if args.experimental:
        target_version = experimental_version
        supported_versions.append(target_version)
        for line in dedent(
            """\
            you chose to run the experimental migration.
            be warned that this will not give you a production ready database,
            is meant to help with the development of upgrade scripts, will
            most likely fail and is only helpful if you can interpret the
            resulting logs and contribute meaningful bug reports"""
        ).split("\n"):
            logging.warning(line)
    if (
        target_version not in supported_versions
        or target_version not in templates["compose"]["odoo_versions"].keys()
    ):
        raise ValueError(f"version {target_version} is not supported")

    get_backup(args)

    db_name, source_version = extract_backup(args)
    if source_version not in supported_versions:
        raise ValueError(f"version {source_version} is not supported")

    to_run = supported_versions[
        supported_versions.index(source_version) + 1 : supported_versions.index(
            target_version
        )
        + 1
    ]
    if not to_run:
        raise ValueError(
            f"cannot migrate your database any further than {source_version}"
        )

    logging.info(f"current version is {source_version}")
    logging.info(f"will download and run migrations for version(s) {', '.join(to_run)}")

    os.makedirs("docker", exist_ok=True)
    with open("docker/docker-compose.yml", "w+") as docker_compose_yml:
        docker_compose_yml.write(
            templates["compose"]["base"].substitute(
                {
                    "db": db_name,
                    "odoo_versions": "\n".join(
                        templates["compose"]["odoo_versions"][version]
                        for version in to_run
                    ),
                }
            )
        )

    os.makedirs("logs", exist_ok=True)

    restore_db(args, db_name, source_version)
    detect_oca_repos(args, db_name)

    if args.experimental:
        apply_prs(args)

    for version in to_run:
        prepare_dockerfiles(args, version)

    for version in to_run:
        if not args.skip_container_build:
            build_containers(args, version)
        else:
            docker_compose("up", "-d", version, logfile=False)

    for version in to_run:
        run_migration(args, db_name, version)

    export_backup(args, db_name, target_version)

    docker_compose("down", logfile=False)
    logging.info(f"done, enjoy {target_version}")


def get_backup(args):
    """
    If args.backup looks like an url, download it
    """
    try:
        url = urlparse(args.backup)
    except Exception:
        return
    if not url.scheme:
        return

    if url.username:
        dbname = url.username
    else:
        sys.stdout.write("fill in your database name: ")
        sys.stdout.flush()
        dbname = sys.stdin.readline().strip()

    if url.password is not None:
        password = url.password
    else:
        password = getpass.getpass("fill in your database admin password: ")

    post_data = urlencode(
        [
            ("master_pwd", password),
            ("name", dbname),
            ("backup_format", "zip"),
        ]
    ).encode("utf8")

    url = url._replace(
        netloc=url.hostname + ((":%s" % url.port) if url.port else ""),
        path="web/database/backup",
    )

    logging.info("downloading backup")
    request = Request(urlunparse(url), data=post_data, method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            if response.code != 200 or "application/octet-stream" not in dict(
                response.getheaders()
            ).get("Content-Type", ""):
                raise ValueError("password or database name seems to be incorrect")

            os.makedirs("source", exist_ok=True)
            with tempfile.NamedTemporaryFile(delete=False) as backup_file:
                buffer = bytearray(1000 * 1000)
                while True:
                    buffer_len = response.readinto(buffer)
                    if not buffer_len:
                        break
                    backup_file.write(buffer[:buffer_len])
                args.backup = backup_file.name
    except HTTPError as e:
        if e.code == 403:
            raise ValueError('list_db seems to be false (%s)' % str(e))
        raise ValueError(str(e)) from e


def extract_backup(args):
    """
    Extract the backup. Return db_name, db_version
    """
    dump = args.backup
    if not zipfile.is_zipfile(dump):
        raise ValueError(
            f"{dump} does not seem to be a backup made with the Odoo database "
            "manager!\nNote you need to choose format 'zip'"
        )
    os.makedirs("source", exist_ok=True)
    logging.info("extracting backup")
    with zipfile.ZipFile(dump) as zip_handle:
        zip_handle.extractall("source")
        with open("source/manifest.json") as manifest_handle:
            manifest = json.loads(manifest_handle.read())
    filestore_link = f"source/{manifest['db_name']}"
    if os.path.islink(filestore_link):
        os.remove(filestore_link)
    os.symlink("filestore", filestore_link)
    return manifest["db_name"], manifest.get("major_version", manifest["version"])


def prepare_dockerfiles(args, version):
    """
    Write Dockerfile to docker/$version,
    repos.yml and requirements.txt to docker/$version/src
    """
    dirname = f"docker/{version}"
    os.makedirs(dirname, exist_ok=True)
    with open(f"{dirname}/Dockerfile", "w+") as dockerfile:
        dockerfile.write(templates["dockerfile"][version])
    with open(f"{dirname}/.dockerignore", "w+") as dockerignore:
        dockerignore.write("src/*/*")
    src = f"{dirname}/src"
    os.makedirs(f"{src}", exist_ok=True)
    with open(f"{src}/repos.yml", "w+") as ymlfile:
        ymlfile.write(templates["gitaggregate"][version])
        for repo in args.repos:
            ymlfile.write(
                gitaggregate_oca_repo_template.substitute(version=version, repo=repo)
            )
    requirements = templates.get("requirements", {}).get(version, [])
    with open(f"{src}/requirements.txt", "w+") as reqfile:
        reqfile.write("\n".join(requirements))
    constraints = templates.get("constraints", {}).get(version, [])
    with open(f"{src}/pip.constraint", "w+") as reqfile:
        reqfile.write("\n".join(constraints))



def build_containers(args, version):
    """
    Build container from docker/$version, run gitaggregate and pip install in them
    """
    logging.info(f"downloading & installing {version}")

    docker_compose("build", version, logfile=f"logs/{version}-build.log")
    docker_compose("up", "-d", version, logfile=False)


def apply_prs(args):
    """
    Apply given prs or all open prs on github to docker/$version/src/openupgrade
    """
    prs = args.prs
    if not prs:
        client = http.client.HTTPSConnection("api.github.com")
        client.request(
            "GET",
            url="/repos/oca/openupgrade/pulls?state=open",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "oca/openupgrade run-migration.py",
            },
        )
        response = client.getresponse()
        prs = [
            pr["number"]
            for pr in json.load(response)
            if (pr.get("milestone", {}) or {}).get("title", "") == experimental_version
        ]

    if not prs:
        raise ValueError("no prs given and none found")

    gitaggregate = templates['gitaggregate'][experimental_version].replace(
        'openupgrade:\n    defaults:\n        depth: 1', 'openupgrade:'
    )

    gitaggregate += '\n'.join(
        f'        - oca refs/pull/{pr}/head'
        for pr in prs
    ) + '\n'

    templates['gitaggregate'][experimental_version] = gitaggregate


def restore_db(args, db_name, version):
    """
    Restore the database dump we got in db container
    """
    docker_compose("up", "-d", "db", logfile="logs/docker-db-up.log")
    while docker_compose_run(
        "db", "pg_isready", "--host db --user odoo", check=False
    ).returncode:
        time.sleep(1)
    logging.info(f"restoring database {db_name}")
    docker_compose_run("db", "dropdb", f"--if-exists --host db --user odoo {db_name}")
    docker_compose_run("db", "createdb", f"--host db --user odoo {db_name}")
    docker_compose_run(
        "db",
        "psql",
        f"--host db --user odoo --file /tmp/dump.sql {db_name}",
        dockercommand_args=["-v", f"{os.path.abspath('source')}:/tmp", "-T"],
        logname="db-restore",
    )


def detect_oca_repos(args, db_name):
    """
    If not given in args, estimate used OCA repositories from installed modules
    """
    if args.repos:
        return

    process = docker_compose(
        "run",
        "-e",
        f"PGPASSWORD={db_password}",
        "db",
        "psql",
        "--host",
        "db",
        "--user",
        "odoo",
        "-d",
        db_name,
        "--tuples-only",
        "--no-align",
        "-c",
        "select website from ir_module_module where state='installed'",
        logfile=False,
        check=False,
    )
    urls = process.stdout.decode("utf8").splitlines()
    args.repos = set(
        filter(
            None,
            (
                "".join(url.path.split("/")[2:3])
                for url in map(urlparse, urls)
                if url.netloc == "github.com" and url.path.lower().startswith("/oca")
            ),
        )
    )
    if args.repos:
        logging.info(f"detected OCA repositories {' '.join(args.repos)}")


def run_migration(args, db_name, version):
    """
    Run migration in $version container
    """
    logging.info(f"running migration {version}")
    addons_path = ",".join(
        ["/odoo/odoo/odoo/addons", "/odoo/odoo/addons"]
        + docker_compose_exec(
            version,
            "find",
            "/odoo -maxdepth 1 -mindepth 1 -not -name odoo -type d",
            logfile=False,
        )
        .stdout.decode("utf8")
        .split()
    )
    server_wide_modules = ""
    try:
        docker_compose_exec(
            version, "ls", "/odoo/openupgrade/openupgrade_framework", logfile=False
        )
        server_wide_modules = "--load openupgrade_framework "
    except subprocess.CalledProcessError:  # pylint: disable=except-pass
        pass
    docker_compose_exec(
        version,
        "odoo/odoo-bin",
        server_wide_modules + f"--addons-path {addons_path} "
        f"--db_host db --db_user {db_user} --db_password {db_password} "
        f"--max-cron-threads 0 -d {db_name} -u all --stop-after-init",
        logname=f"{version}-migration",
    )


def export_backup(args, db_name, target_version):
    """
    Write a zipfile for import in $target_version
    """
    backup_filename = f"{db_name}-migrated-{target_version}.zip"

    export_script = dedent(
        f"""\
        from odoo.tools import config
        from odoo.service import db
        config['db_host'] = 'db'
        config['db_user'] = '{db_user}'
        config['db_password'] = '{db_password}'
        db.dump_db(
            '{db_name}',
            open(config['data_dir'] + '/filestore/{backup_filename}', 'wb+')
        )
        """
    )

    subprocess.run(
        docker_compose_cmd
        + f"exec -w /odoo -T {target_version} odoo/odoo-bin shell".split(),
        cwd="docker",
        check=True,
        env=compose_env,
        input=export_script,
        text=True,
        stdout=open("logs/db-export.log", "w+"),
        stderr=subprocess.STDOUT,
    )

    shutil.move(f"source/{backup_filename}", backup_filename)
    logging.info(f"exported migrated database to {os.getcwd()}/{backup_filename}")


compose_env = {
    "COMPOSE_PROJECT_NAME": "openupgrade",
}
docker_compose_cmd = (
    shutil.which("docker-compose")
    and ["docker-compose"]
    or shutil.which("docker")
    and ["docker", "compose"]
)


def docker_compose(subcommand, *args, logfile=None, check=True):
    """Run docker compose with some default parameters"""
    logging.debug(
        "running %s", " ".join(docker_compose_cmd + [subcommand] + list(args))
    )
    return subprocess.run(
        docker_compose_cmd + [subcommand] + list(args),
        cwd="docker",
        check=check,
        env=compose_env,
        **{
            "stderr": logfile and subprocess.STDOUT or None,
            "stdout": logfile and open(logfile, "w+") or None,
        }
        if logfile is not False
        else {"capture_output": True},
    )


def docker_compose_run_exec(
    service,
    docker_command,
    command,
    *args,
    dockercommand_args=None,
    logname=None,
    root=False,
    **kwargs,
):
    """
    Add default parameters to docker compose run/exec, split one string commandlines
    """
    command_args = list(args)
    if len(command_args) == 1:
        command_args = command_args[0].split(" ")
    return docker_compose(
        docker_command,
        "-e",
        f"PGPASSWORD={db_password}",
        "-w",
        "/odoo",
        *(dockercommand_args or []),
        *(["-u", "root"] if root else []),
        service,
        command,
        *command_args,
        logfile=f"logs/{logname or f'{service}-{command}'}.log"
        if "logfile" not in kwargs
        else kwargs["logfile"],
        **{k: v for k, v in kwargs.items() if k != "logfile"},
    )


def docker_compose_run(service, command, *args, dockercommand_args=None, **kwargs):
    return docker_compose_run_exec(
        service,
        "run",
        command,
        *args,
        dockercommand_args=["--rm"] + (dockercommand_args or []),
        **kwargs,
    )


def docker_compose_exec(service, command, *args, dockercommand_args=None, **kwargs):
    return docker_compose_run_exec(
        service,
        "exec",
        command,
        *args,
        dockercommand_args=["-T"] + (dockercommand_args or []),
        **kwargs,
    )


db_user = db_password = "odoo"
dockerfile_template = string.Template(
    f"""\
FROM python:$python_version
RUN groupadd -g {os.getgid()} -o openupgrade
RUN useradd -m -u {os.getuid()} -g {os.getgid()} -o -s /bin/bash openupgrade\
    --groups root
RUN apt update && apt -yq install \
    build-essential \
    libfreetype6-dev \
    libfribidi-dev \
    libghc-zlib-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    liblcms2-dev \
    libldap2-dev \
    libopenjp2-7-dev \
    libpq-dev \
    libsasl2-dev \
    libtiff5-dev \
    libwebp-dev \
    libxml2-dev \
    libxslt-dev \
    postgresql-client \
    tcl-dev \
    tk-dev \
    zlib1g-dev
RUN pip install git-aggregator
COPY src /odoo
RUN git config --global --add user.name openupgrade &&\
    git config --global --add user.email openupgrade@oca &&\
    git config --global init.defaultBranch main
ENV PIP_CONSTRAINT=/odoo/pip.constraint
RUN cd /odoo && for yml_file in *.yml; do \
        gitaggregate -c $yml_file --no-color --jobs 4;\
    done &&\
    for requirement in */requirements.txt *.txt; do \
        if [ -f $requirement ]; then pip install -U -r $requirement; fi;\
    done &&\
    pip install ./odoo
USER openupgrade
CMD sleep infinity
"""
)
gitaggregate_template_pre14 = string.Template(
    """\
odoo:
    defaults:
        depth: 1
    remotes:
        oca: https://github.com/oca/openupgrade
    merges:
        - oca $version
"""
)
gitaggregate_template = string.Template(
    """\
odoo:
    defaults:
        depth: 1
    remotes:
        oca: https://github.com/oca/ocb
    merges:
        - oca $version
openupgrade:
    defaults:
        depth: 1
    remotes:
        oca: https://github.com/oca/openupgrade
    merges:
        - oca $version
"""
)
gitaggregate_oca_repo_template = string.Template(
    """\
$repo:
    defaults:
        depth: 1
    remotes:
        oca: https://github.com/oca/$repo
    merges:
        - oca $version
"""
)
odoo_service_template = string.Template(
    """\
'$version':
    build:
        context: ./$version
    depends_on:
        - db
    volumes:
        - type: bind
          source: ../source
          target: /home/openupgrade/.local/share/Odoo/filestore
    networks:
        - openupgrade
"""
)

templates = {
    "compose": {
        "base": string.Template(
            dedent(
                f"""\
            version: '3'
            networks:
                openupgrade:
                    driver: bridge
                    driver_opts:
                        com.docker.network.bridge.enable_ip_masquerade: 0
                    internal: true
            services:
                db:
                    image: postgres:15
                    environment:
                        POSTGRES_USER: {db_user}
                        POSTGRES_PASSWORD: {db_password}
                        POSTGRES_DB: $db
                    networks:
                        - openupgrade
            $odoo_versions"""
            )
        ),
        "odoo_versions": {
            "12.0": indent(odoo_service_template.substitute(version="12.0"), " " * 4),
            "13.0": indent(odoo_service_template.substitute(version="13.0"), " " * 4),
            "14.0": indent(odoo_service_template.substitute(version="14.0"), " " * 4),
            "15.0": indent(odoo_service_template.substitute(version="15.0"), " " * 4),
            "16.0": indent(odoo_service_template.substitute(version="16.0"), " " * 4),
            "17.0": indent(odoo_service_template.substitute(version="17.0"), " " * 4),
            "18.0": indent(odoo_service_template.substitute(version="18.0"), " " * 4),
            "19.0": indent(odoo_service_template.substitute(version="19.0"), " " * 4),
        },
    },
    "dockerfile": {
        "12.0": dockerfile_template.safe_substitute(python_version="3.7"),
        "13.0": dockerfile_template.safe_substitute(python_version="3.7"),
        "14.0": dockerfile_template.safe_substitute(python_version="3.8"),
        "15.0": dockerfile_template.safe_substitute(python_version="3.8"),
        "16.0": dockerfile_template.safe_substitute(python_version="3.11"),
        "17.0": dockerfile_template.safe_substitute(python_version="3.11"),
        "18.0": dockerfile_template.safe_substitute(python_version="3.12"),
        "19.0": dockerfile_template.safe_substitute(python_version="3.12"),
    },
    "gitaggregate": {
        "12.0": gitaggregate_template_pre14.substitute(version="12.0"),
        "13.0": gitaggregate_template_pre14.substitute(version="13.0"),
        "14.0": gitaggregate_template.substitute(version="14.0"),
        "15.0": gitaggregate_template.substitute(version="15.0"),
        "16.0": gitaggregate_template.substitute(version="16.0"),
        "17.0": gitaggregate_template.substitute(version="17.0"),
        "18.0": gitaggregate_template.substitute(version="18.0"),
        "19.0": gitaggregate_template.substitute(version="19.0"),
    },
    "constraints": {
        "13.0": (
            "Werkzeug<0.15",
            "pyOpenSSL<23",
            "cryptography<23.2.0",
            "pypdf2<2.0.0",
            "lxml<5.0",
        ),
        "14.0": (
            "Werkzeug<0.17",
            "pyOpenSSL<23",
            "cryptography<23.2.0",
            "pypdf<5.0",
            "lxml<5.0",
        ),
        "15.0": (
            "lxml<5.0",
            "pyOpenSSL<23",
            "cryptography<23.2.0",
        ),
        "16.0": (
            "lxml<5.0",
            "pyOpenSSL<23",
            "cryptography<23.2.0",
        ),
        "17.0": (
            "lxml<5.0",
            "pyOpenSSL<23",
            "cryptography<23.2.0",
        ),
    },
    "requirements": {
        experimental_version: (
            "git+https://github.com/oca/openupgradelib",
        ),
    }
}

supported_versions = sorted(
    version
    for version in templates["compose"]["odoo_versions"].keys()
    if version != experimental_version
)
latest_version = supported_versions[-1]

parser = argparse.ArgumentParser(
    prog="run-migration",
    description="Runs an Odoo database migration for you using OpenUpgrade",
)
parser.add_argument(
    "backup",
    help="Backup of your Odoo database from database manager or url to your Odoo "
    "instance if database manager is accessible",
    metavar="BACKUP.zip|http://yourodoo.com",
)
parser.add_argument(
    "--skip-container-build",
    action="store_true",
    help=argparse.SUPPRESS,
)
parser.add_argument(
    "--debug",
    action="store_true",
    help=argparse.SUPPRESS,
)
parser.add_argument(
    "--repos",
    action="extend",
    type=str,
    nargs="+",
    help="Pass OCA repository names your database uses",
    metavar="REPO",
    default=[],
)
parser.add_argument(
    "-t",
    "--target-version",
    help=f"The version you want to migrate to, default {latest_version}",
    default=latest_version,
)
parser.add_argument(
    "-E",
    "--experimental",
    action="store_true",
    help="Attempt to run a migration for the current experimental version "
    f"{experimental_version}. This probably fails and you should pass specific PRs to "
    "test with the --prs parameter",
)
parser.add_argument(
    "--prs",
    action="extend",
    type=int,
    nargs="+",
    help="Pass PR numbers to test for the experimental version",
    metavar="PRNUMBER",
)
args = parser.parse_args()

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO if not args.debug else logging.DEBUG,
    format="(%(levelname)s) [%(asctime)s] %(message)s",
)

if __name__ == "__main__":
    try:
        main(args)
    except Exception as e:
        for line in " ".join(map(str, e.args)).split("\n"):
            logging.error(line)
        if args.debug:
            raise
        else:
            logging.error("please consult the files in ./logs for error analysis")
        sys.exit(1)
