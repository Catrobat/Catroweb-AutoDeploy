# Catroweb Auto-Deploy Server Installation
Do the following steps as root user:
1. Run puppet agent (maybe multiple times)
1. Disable nginx default site: `rm /etc/nginx/sites-enabled/default`
1. Create folder for Python script and upload the files of *deploy_script* `mkdir /opt/prdeployer`
1. Install Python requirements: `cd /opt/prdeployer` and `pip3 install -r requirements.txt`
1. Update Node/NPM: `npm install -g n && n stable && npm install npm@latest -g`
1. Install Sass (use new command in future): `npm install -g sass`
1. Secure MariaDB server: `mysql_secure_installation`  
	Current root password (None, Enter)  
	Set new root password [Y] (Choose a random password)  
	Remove anonymous users [Y]  
	Disallow root login remotely [Y]  
	Remove test database [Y]  
	Reload privilege tables now [Y]
1. Allow TCP root login (disable socket): 
`mysql mysql -e "UPDATE user SET plugin = '' WHERE user = 'root' AND host = 'localhost';`  
`mysql -e "FLUSH PRIVILEGES;"`
1. To allow mysql login as root without a password, create the file */root/.my.cnf* with the following content  
    ```
    [client]
    user=root
    password=MYSQL_PASSWORD_DEFINED_ABOVE
    ```
1. Also set the password in */opt/prdeployer/config.py* file
1. Create web directories: `mkdir /var/www/catroweb && mkdir -p /var/www/index/logs`
1. Create cache directories for composer and npm: 
   ```bash
   mkdir /var/www/.composer && chown www-data:www-data /var/www/.composer
   mkdir /var/www/.npm && chown www-data:www-data /var/www/.npm
   mkdir /var/www/.config && chown www-data:www-data /var/www/.config
   ```
1. Upload files of *index_page* to */var/www/index/*
1. Create database for deployment: `mysql -e "CREATE DATABASE deployment;"`
1. Initialize the database with the *create_deployment_table.sql* file: `mysql deployment < create_deployment_table.sql`
1. Create MySQL user for index page: `mysql -Be "CREATE USER 'index'@'localhost' IDENTIFIED BY 'YOUR_RANDOM_INDEX_PASSWORD'; GRANT SELECT ON deployment.* TO 'index'@'localhost';"`
1. Set MySQL password for index in */var/www/index/config.php*, and check *url_template* there, too.
1. Add branches using the following Python3 script, executed in */opt/prdeployer/*:  
   ```python
   import prdeployer
   prdeployer.Deployer.add_github_branch('master')
   prdeployer.Deployer.add_github_branch('develop')
   ```

The server should run using HTTPS, otherwise, errors or warnings may occur in the browser.

### The following things are under puppet control
* nginx site config for index
* nginx server block template used by deployer
* php sury apt list config
* installed apt packages
* cron command

## Installation without Puppet
1. Add Sury PHP as package source: See https://deb.sury.org/
1. Install needed packages (use PHP version needed, multiple versions possible)
   ```bash
   apt-get install nginx mariadb-server ssl-cert npm curl python3 git
   apt-get install php7.4-common php7.4-cli php7.4-fpm php7.4-curl php7.4-intl php7.4-gd php7.4-zip php7.4-mysql php7.4-xml php7.4-mbstring
   apt-get install php-apcu php-imagick php-gettext composer
   ```
1. Copy the file *nginx_index_site* to */etc/nginx/sites-available/index*
1. Create a symlink from */etc/nginx/sites-enabled/000-index* to */etc/nginx/sites-available/index*
1. Do the steps from above, except the first one
1. Restart nginx: `systemctl restart nginx`
1. Add the following line as cronjob for root using `crontab -e`:
   ```
   /15 * * * * /usr/bin/flock -w 300 /opt/prdeployer/prdeployer.lock /usr/bin/python3 /opt/prdeployer/prdeployer.py >/dev/null 2>&1
   ```

## Update the Autodeployer system after changes

For changes in the python & php scripts just run: 
```
/opt/update-prdeployer-git.sh 
```
However, all other file changes should be done manually since they could contain production secrets. (Etc. `overwrite`folder)
