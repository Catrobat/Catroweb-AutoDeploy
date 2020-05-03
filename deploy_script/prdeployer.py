#!/usr/bin/env python3
import json
import logging.handlers
import os
import re
import shutil
import subprocess
from enum import Enum
from string import Template
from typing import List, Dict

import pymysql
import requests

from config import Config
from logger import ColoredLogger

logging.setLoggerClass(ColoredLogger)
logger = logging.getLogger(__name__)


class DeploymentType(Enum):
    PULL_REQUEST = 'pr'
    BRANCH = 'branch'


class DeploymentData:
    label: str
    type: DeploymentType
    source_branch: str
    source_sha: str
    source_clone_url: str
    title: str
    url: str
    author: str

    def __init__(self, label: str, source_sha, source_branch, source_clone_url, title=None, url=None, author=None,
                 type=DeploymentType.PULL_REQUEST):
        self.label = label
        self.source_sha = source_sha
        self.source_branch = source_branch
        self.source_clone_url = source_clone_url
        self.title = title
        self.url = url
        self.author = author
        self.type = type

    def __repr__(self):
        return 'DeploymentData(' + repr(self.label) + ', ' + repr(self.source_sha) + ', ' + \
               repr(self.source_branch) + ', ' + repr(self.source_clone_url) + ', ' + repr(self.title) + ', ' + \
               repr(self.url) + ', ' + repr(self.author) + ', ' + repr(self.type) + ')'


class IgnoredPullRequestException(Exception):
    message = ""

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message


class Deployer:
    db_connection: pymysql.Connection
    _nginx_template: Template
    _available_php_versions: List[str]

    def __init__(self):
        # initialize variables
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nginx-server-block.template'), 'r') as f:
            self._nginx_template = Template(f.read())
        self._available_php_versions = self._detect_available_php_versions()

    def connect_db(self):
        logger.info("Connecting to MariaDB on localhost using user %s", Config.MYSQL_USER)
        self.db_connection = pymysql.connect(host='localhost', user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD,
                                             charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
        self.db_connection.autocommit(False)

    def close_db(self):
        logger.info("Close connection to MariaDB")
        self.db_connection.close()

    def run(self):
        logger.info('Deployer.run() started')
        pull_requests = self.get_pull_requests()
        self.connect_db()
        try:
            self.process_pull_requests(pull_requests)
            self.process_branches()
        finally:
            self.close_db()

        p = subprocess.Popen(['systemctl', 'reload', 'nginx'])
        if p.wait() != 0:
            logger.error("Failed to reload nginx")
        logger.info('Deployer.run() finished')

    def process_pull_requests(self, pull_requests):
        active_labels = []
        with self.db_connection.cursor() as cursor:
            sql_query = "SELECT * FROM deployment.deployment WHERE `type` = 'pr' AND label = %s;"
            for pr in pull_requests:
                logger.info('Process pull request %d', int(pr['number']))
                label = 'pr' + str(int(pr['number']))
                active_labels.append(label)
                data = DeploymentData(label, pr['head']['sha'], pr['head']['ref'], pr['head']['repo']['clone_url'],
                                      pr['title'], pr['html_url'], pr['user']['login'])
                logger.debug(str(data))

                try:
                    if data.source_sha in Config.IGNORED_COMMITS:
                        raise IgnoredPullRequestException(
                            f"Skip {label}, commit {data.source_sha} is in IGNORED_COMMITS")

                    for git_label in pr['labels']:
                        if git_label['id'] in Config.IGNORED_GITHUB_LABEL_IDS:
                            raise IgnoredPullRequestException(f"Skip {label}, GitHub label \"{git_label['name']}\" "
                                                              f"({git_label['id']}) in IGNORED_GITHUB_LABEL_IDS")
                except IgnoredPullRequestException as e:
                    logger.warning(e.message)
                    try:
                        self.delete_deployment(label)
                    except Exception as e:
                        logger.error(e)
                    continue

                cursor.execute(sql_query, (label,))
                entry = cursor.fetchone()
                fail_count = 0
                try:
                    if entry is None:
                        self.create_deployment(data)
                    elif entry['fail_count'] > 0:
                        if data.source_sha == entry['source_sha'] and entry['fail_count'] >= 3:
                            logger.warning(f"Skip {label}, deploy of {data.source_sha} failed 3 times.")
                        else:
                            fail_count = entry['fail_count']
                            self.create_deployment(data, db_entry_exists=True)
                    else:
                        if data.source_sha != entry['source_sha']:
                            self.update_deployment(data)
                except Exception as e:
                    logger.error(e)
                    logger.warning(f"Failed creating/updating {label}. Delete it.")
                    try:
                        self.delete_deployment(label, data, fail_count + 1)
                    except Exception as e:
                        logger.error(e)

            # delete closed pull requests
            cursor.execute(
                "SELECT `label` FROM deployment.deployment "
                f"WHERE `type` = 'pr' AND label NOT IN ({', '.join('%s' for _ in active_labels)})",
                active_labels)
            result = cursor.fetchall()
            logger.info("Delete not active pull requests: %s", ', '.join(list(map(lambda x: x['label'], result))))
            for row in result:
                try:
                    self.delete_deployment(row['label'])
                except Exception as e:
                    logger.error(e)

    def process_branches(self):
        with self.db_connection.cursor() as cursor:
            cursor.execute("SELECT * FROM deployment.deployment WHERE `type` = %s", (DeploymentType.BRANCH.value,))
            result = cursor.fetchall()
            for row in result:
                try:
                    self.update_github_branch(row)
                except Exception as e:
                    logger.error(e)

    def update_github_branch(self, row):
        branch = row['source_branch']
        logger.info(f"Check GitHub branch {branch} for updates")
        api_url = f'https://api.github.com/repos/{Config.GITHUB_REPO_OWNER}/{Config.GITHUB_REPO_NAME}/branches/{branch}'
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/vnd.github.v3+json'}
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            result = json.loads(response.content.decode('utf-8'))
            latest_sha = result['commit']['sha']
            if latest_sha in Config.IGNORED_COMMITS:
                logger.warning(f"Skip {row['label']}, commit {latest_sha} is in IGNORED_COMMITS")
                return

            if row['source_sha'] != latest_sha:
                clone_url = f'https://github.com/{Config.GITHUB_REPO_OWNER}/{Config.GITHUB_REPO_NAME}.git'
                title = result['commit']['commit']['message'].partition('\n')[0]
                author = result['commit']['commit']['author']['name']
                data = DeploymentData(row['label'], latest_sha, branch, clone_url, title, result['_links']['html'],
                                      author, DeploymentType.BRANCH)
                logger.debug(str(data))
                self.update_deployment(data)
        else:
            raise Exception(f"Failed to get GitHub data for branch {branch}: Error {response.status_code}")

    def update_deployment(self, data: DeploymentData):
        git_folder = os.path.join(Config.WEB_FOLDER, data.label)

        # git fetch, git reset
        logger.info(f"Git fetch + reset for {data.label}")
        self._run_subprocess("git fetch origin", data.label, "run git fetch", git_folder)
        self._run_subprocess(["git", "reset", "--hard", f"origin/{data.source_branch}"], data.label,
                             "run git reset", git_folder)

        self._copy_parameters_yml(git_folder, data.label)

        # Set ownership
        logger.info(f"Set file ownership for {data.label}")
        self._run_subprocess("chown -hR www-data:www-data .", data.label, "set file ownership", git_folder)
        self._run_subprocess("chown root:root .env.local", data.label, "set .env.local file ownership", git_folder)

        php_version = self._detect_required_php_version(data.label)
        logger.info(f"Detected PHP version for {data.label} is {php_version}")
        self._install_dependencies_and_reset(git_folder, data.label, php_version)
        self._write_nginx_site(data.label, php_version)

        # update database entry
        logger.info(f"Updating deployment of {data.label} finished, update database entry")
        with self.db_connection.cursor() as cursor:
            cursor.execute(
                "UPDATE deployment.deployment "
                "SET `source_branch` = %s, `source_sha` = %s, `deployed_at` = CURRENT_TIMESTAMP , `title` = %s, "
                "`fail_count` = 0 WHERE `label` = %s",
                (data.source_branch, data.source_sha, data.title, data.label,))
        self.db_connection.commit()

    def delete_deployment(self, label: str, data: DeploymentData = None, fail_count=0):
        # 1. delete nginx site
        logger.info(f"Delete nginx site for {label}")
        try:
            os.unlink(os.path.join(Config.NGINX_SITES_AVAILABLE, label))
        except Exception:
            pass
        try:
            os.unlink(os.path.join(Config.NGINX_SITES_ENABLED, label))
        except Exception:
            pass

        # 2. drop database
        logger.info(f"Drop database and user for {label}")
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE {label}")
                cursor.execute("DROP USER %s@'localhost'", (label,))
        except Exception:
            pass

        # 3. delete deployment web folder
        logger.info(f"Delete web folder for {label}")
        shutil.rmtree(os.path.join(Config.WEB_FOLDER, label), ignore_errors=True)

        # 4. delete database entry
        logger.info(f"Deleting {label} finished, delete/update database entry")
        try:
            with self.db_connection.cursor() as cursor:
                if fail_count == 0:
                    cursor.execute("DELETE FROM deployment.deployment WHERE label = %s", (label,))
                elif fail_count == 1:
                    cursor.execute(
                        "INSERT INTO deployment.deployment(`label`, `type`, `source_branch`, `source_sha`, "
                        "`deployed_at`, `title`, `url`, `author`, `fail_count`) "
                        "VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s)",
                        (data.label, data.type.value, data.source_branch, data.source_sha, data.title, data.url,
                         data.author, int(fail_count),))
                else:
                    cursor.execute(
                        "UPDATE deployment.deployment "
                        "SET `source_branch` = %s, `source_sha` = %s, `deployed_at` = CURRENT_TIMESTAMP, "
                        "`title` = %s, `fail_count` = %s "
                        "WHERE `label` = %s",
                        (data.source_branch, data.source_sha, data.title, int(fail_count), data.label,))

        except Exception as e:
            logger.warning(f"Failed deleting/updating database entry for {label} with fail count {fail_count}: {e}")
            pass

        self.db_connection.commit()

    def create_deployment(self, data: DeploymentData, db_entry_exists=False):
        git_folder = os.path.join(Config.WEB_FOLDER, data.label)

        # Clone Repository
        logger.info(f"Clone Repository for {data.label}")
        p = subprocess.Popen(
            ["git", "clone", data.source_clone_url, '--branch', data.source_branch, '--single-branch', data.label],
            cwd=Config.WEB_FOLDER, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with p.stdout:
            for line in iter(p.stdout.readline, b''):
                logger.debug(line.decode('utf-8').rstrip('\n'))
        if p.wait() != 0:
            raise Exception(f"Failed to clone repository {data.source_clone_url}/{data.source_branch} to {data.label}")

        # Create Database
        logger.info(f"Create database and user for {data.label}")
        db_password = self._generate_password()
        with self.db_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {data.label}")
            cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (data.label, db_password,))
            cursor.execute(f"GRANT ALL PRIVILEGES ON {data.label}.* TO '{data.label}'@'localhost';")
        self.db_connection.commit()

        self._copy_parameters_yml(git_folder, data.label)

        logger.info(f"Set ownership and create .env.local file for {data.label}")
        # Create .env.dev.local file
        with open(os.path.join(git_folder, '.env.dev.local'), 'w') as env_file:
            print('SECURE_SCHEME="https"', file=env_file)

        # Set ownership
        self._run_subprocess("chown -hR www-data:www-data .", data.label, "set file ownership", git_folder)

        # Create .env.local file
        with open(os.path.join(git_folder, '.env.local'), 'w') as env_file:
            print(f"DATABASE_URL=pdo-mysql://{data.label}:{db_password}@localhost/{data.label}",
                  file=env_file)
            print(f"DATABASE_NAME={data.label}", file=env_file)
            print(f"DATABASE_USER={data.label}", file=env_file)
            print(f"DATABASE_PASSWORD={db_password}", file=env_file)

        php_version = self._detect_required_php_version(data.label)
        logger.info(f"Detected PHP version for {data.label} is {php_version}")
        self._install_dependencies_and_reset(git_folder, data.label, php_version)
        self._write_nginx_site(data.label, php_version)

        # add database entry
        logger.info(f"Creating deployment of {data.label} finished, add database entry")
        with self.db_connection.cursor() as cursor:
            if db_entry_exists:
                cursor.execute(
                    "UPDATE deployment.deployment "
                    "SET `source_branch` = %s, `source_sha` = %s, `deployed_at` = CURRENT_TIMESTAMP , `title` = %s, "
                    "`fail_count` = 0 WHERE `label` = %s",
                    (data.source_branch, data.source_sha, data.title, data.label,))
            else:
                cursor.execute(
                    "INSERT INTO deployment.deployment(`label`, `type`, `source_branch`, `source_sha`, `deployed_at`, "
                    "`title`, `url`, `author`) VALUES(%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s)",
                    (data.label, data.type.value, data.source_branch, data.source_sha, data.title, data.url,
                     data.author,))
        self.db_connection.commit()

    def get_pull_requests(self) -> List[Dict[str, any]]:
        logger.info("Fetching pull requests from GitHub")
        pull_requests = []
        page = 1
        while True:
            added_prs = self._get_pull_requests_page(page)
            pull_requests += added_prs
            page += 1
            if len(added_prs) < 30:
                break
        logger.info("Found %d pull requests on GitHub", len(pull_requests))
        return pull_requests

    @staticmethod
    def _get_pull_requests_page(page: int = 1) -> List[Dict[str, any]]:
        api_url = 'https://api.github.com/repos/Catrobat/Catroweb-Symfony/pulls?state=open'
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/vnd.github.v3+json'}
        api_url += '&page=' + str(page)
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return json.loads(response.content.decode('utf-8'))
        else:
            raise Exception(f"Failed to get pull requests from GitHub API: Error {response.status_code}")

    @staticmethod
    def _generate_password(length: int = 30) -> str:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _install_dependencies_and_reset(self, git_folder: str, label: str, php_version: str):
        logger.info(f"Run composer install for {label}")
        self._run_subprocess(
            ["sudo", "-u", "www-data", "php" + php_version, "/usr/bin/composer", "install", "--no-interaction"],
            label, "run composer install", git_folder)
        logger.info(f"Run npm ci for {label}")
        self._run_subprocess("sudo -u www-data npm ci", label, "run npm ci", git_folder)
        logger.info(f"Run catro:reset for {label}")
        self._run_subprocess("sudo -u www-data php bin/console catro:reset --hard", label, "run catro:reset",
                             git_folder)
        logger.info(f"Run grunt for {label}")
        self._run_subprocess("sudo -u www-data grunt", label, "run grunt", git_folder)

    @staticmethod
    def _copy_parameters_yml(git_folder: str, label):
        logger.info(f"Copy parameters.yml for {label}")
        parameters_yml_dist_file = os.path.join(git_folder, 'config/packages/parameters.yml.dist')
        if os.path.isfile(parameters_yml_dist_file):
            shutil.copy(parameters_yml_dist_file, os.path.join(git_folder, 'config/packages/parameters.yml'))

    @staticmethod
    def _run_subprocess(command, label: str, desc: str, cwd=None):
        if isinstance(command, str):
            command = command.split(" ")
        if not isinstance(command, list):
            raise Exception(f"Invalid command for {label}: <{type(command)}> {str(command)}")

        p = subprocess.Popen(command, cwd=cwd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        with p.stdout:
            for line in iter(p.stdout.readline, b''):
                logger.debug(line.decode('utf-8').rstrip('\n'))
        if p.wait() != 0:
            raise Exception(f"Failed to {desc} for {label}")

    def _write_nginx_site(self, label: str, php_version: str):
        logger.info(f"Write nginx site file for {label} with PHP version {php_version}")
        available_path = os.path.join(Config.NGINX_SITES_AVAILABLE, label)
        with open(available_path, 'w') as f:
            f.write(self._nginx_template.substitute(label=label, phpversion=php_version))
        enabled_path = os.path.join(Config.NGINX_SITES_ENABLED, label)
        if not os.path.exists(enabled_path):
            logger.debug(f"Create nginx site-enabled symlink for {label}")
            os.symlink(available_path, enabled_path)

    def _detect_required_php_version(self, label):
        with open(os.path.join(Config.WEB_FOLDER, label, 'composer.json'), 'r') as f:
            data = json.load(f)

        required_version = data['require']['php']

        # since there can be problems with other dependencies
        # first look if specified version is available, and ignore operators (>=, ~, ...)
        matches = re.search(r"(\d\.\d)", required_version)
        if matches:
            selected_version = matches.group()
            if selected_version in self._available_php_versions:
                return selected_version

        matches = re.match(r"^\d.\d", required_version)
        if matches:
            selected_version = matches.group()
            if selected_version in self._available_php_versions:
                return selected_version
            else:
                raise Exception(f"Required PHP version {required_version} for {label} not available.")

        matches = re.match(r"^>=?(\d)\.(\d)", required_version)
        if matches:
            major = int(matches.group(1))
            minor = int(matches.group(2))
            for version in self._available_php_versions:
                version_no = list(map(lambda x: int(x), version.split(".")))
                if version_no[0] > major or (version_no[0] == major and version_no[1] >= minor):
                    return version
            raise Exception(f"Required PHP version {required_version} for {label} not available.")

        matches = re.match(r"^<(\d)\.(\d)", required_version)
        if matches:
            major = int(matches.group(1))
            minor = int(matches.group(2))
            for version in self._available_php_versions:
                version_no = list(map(lambda x: int(x), version.split(".")))
                if version_no[0] < major or (version_no[0] == major and version_no[1] < minor):
                    return version
            raise Exception(f"Required PHP version {required_version} for {label} not available.")

        matches = re.match(r"^<=(\d)\.(\d)", required_version)
        if matches:
            major = int(matches.group(1))
            minor = int(matches.group(2))
            for version in self._available_php_versions:
                version_no = list(map(lambda x: int(x), version.split(".")))
                if version_no[0] < major or (version_no[0] == major and version_no[1] <= minor):
                    return version
            raise Exception(f"Required PHP version {required_version} for {label} not available.")

        matches = re.match(r"^~(\d)\.(\d)", required_version)
        if matches:
            major = int(matches.group(1))
            minor = int(matches.group(2))
            for version in self._available_php_versions:
                version_no = list(map(lambda x: int(x), version.split(".")))
                if version_no[0] == major and version_no[1] >= minor:
                    return version
            raise Exception(f"Required PHP version {required_version} for {label} not available.")

        raise Exception(f"Failed parsing required PHP version {required_version} for {label}.")

    @staticmethod
    def _detect_available_php_versions() -> List[str]:
        p = subprocess.run(['update-alternatives', '--list', 'php'], stdout=subprocess.PIPE)
        versions = []
        for executable_path in p.stdout.decode('utf-8').splitlines():
            matches = re.search(r'/php(\d\.\d)$', executable_path)
            versions.append(matches.group(1))
        versions.sort(reverse=True)  # newest version should be preferred
        logger.info('PHP Versions installed on the system: %s', ', '.join(versions))
        return versions


if __name__ == '__main__':
    Deployer().run()
