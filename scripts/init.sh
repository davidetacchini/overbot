#!/bin/bash
red=$(tput setaf 1)
green=$(tput setaf 2)
reset=$(tput sgr0)

bold=$(tput bold)
normal=$(tput sgr0)

if [ "$EUID" -ne 0 ]; then 
	echo "${red}You must have root permission.${reset}"
  	exit 1
else
 	echo "[${green}OK${reset}] root permissions"
fi

printf "Welcome to the OverBot Setup!\n\n"
read -p "Enter the database name: " db_name
read -p "Enter the database user: " db_user

printf "Copying service file to /etc/systemd/system/overbot.service...\n\n"
sed -i "s:/path/to/overbot/:$(pwd)/:" overbot.service
sed -i "s:username:$(whoami):" overbot.service
cp overbot.service /etc/systemd/system/overbot.service

printf "Setting up the database...\n\n"
printf "Replacing schema user to ${bold}$db_user${normal}\n"

sed -i "s:davide:$db_user:" schema.sql

printf "Loading database schema...\n"
sudo -u $db_user psql $db_name < schema.sql

printf "Checking for pip to be at the latest version available...\n"
python3 -m pip install -U --upgrade pip

printf "Installing dependencies...\n"
python3 -m pip install -U -r ./requirements.txt

printf "Reloading the daemon...\n"
{
	systemctl daemon-reload
} || {
	echo "[${red}ERROR${reset}] an error occured while reloading the daemon."
}

printf "${green}${bold}Installation completed!${normal}${reset}\n"
printf "Run ${bold}systemctl start overbot${normal}\n"
