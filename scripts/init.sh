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

printf "\n\nInstalling the configuration file...\n"
curl https://raw.githubusercontent.com/davidetacchini/OverBot/master/config.example.py -o ./config.py
printf "[${green}OK${reset}] configuration file successfully installed.\n"

if [ ! -f "./config.example.py" ]; then
	printf "\n\nInstalling the configuration file...\n"
	curl https://raw.githubusercontent.com/davidetacchini/OverBot/master/config.example.py
	printf "[${green}OK${reset}] configuration file successfully installed.\n"
fi

printf "\n\Moving config.example.py to config.py...\n"
mv config.example.py config.py

printf "Copying service file to /etc/systemd/system/overbot.service...\n\n"
sed -i "s:/path/to/overbot/:$(pwd)/:" overbot.service
sed -i "s:username:$(whoami):" overbot.service
cp overbot.service /etc/systemd/system/overbot.service

printf "Loading database schema...\n"
sudo -u davide psql overbot < schema.sql

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
printf "${red}Checkout the README file to complete the installation.${reset}\n"
