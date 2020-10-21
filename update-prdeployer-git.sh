#!/bin/sh
# This file needs to be moved to /opt for execution if anything changes

if [ "$(whoami)" != 'root' ]; then
        echo "Please run $0 as root."
        exit 1;
fi

cd /opt/Catroweb-AutoDeploy
git fetch
git reset --hard origin/master
cat deploy_script/prdeployer.py > /opt/prdeployer/prdeployer.py
cat index_page/index.php > /var/www/index/index.php
cat index_page/config.inc.php > /var/www/index/config.inc.php
echo "Only prdeployer.py and index.php are updated automatically."
echo "Please update overwrite folder etc. manually!"
