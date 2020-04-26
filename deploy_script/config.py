class Config:
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'MYSQL_ROOT_PASSWORD'
    WEB_FOLDER = '/var/www/catroweb/'
    NGINX_SITES_AVAILABLE = '/etc/nginx/sites-available/'
    NGINX_SITES_ENABLED = '/etc/nginx/sites-enabled/'
    GITHUB_REPO_OWNER = 'Catrobat'
    GITHUB_REPO_NAME = 'Catroweb-Symfony'
    LOG_FILE = '/var/log/catroweb_deployer.log'
    IGNORED_COMMITS = [
        '04aebd23f959aab4d7bf76609686f531cb3426b9',  # SHARE-000
    ]  # list of sha-1 commit hashes
    IGNORED_GITHUB_LABEL_IDS = [
        2014689048,  # no auto-deploy
    ]
