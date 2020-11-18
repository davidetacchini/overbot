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

printf "\n\nInstalling the configuration file...\n"
curl https://raw.githubusercontent.com/davidetacchini/OverBot/master/config.example.py -o ./config.py
printf "[${green}OK${reset}] configuration file successfully installed!\n"

if [ -f "./config.example.py" ]; then
	echo "Removing config.example.py..."
	rm -f ./config.example.py
fi

printf "Copying service file to /etc/systemd/system/overbot.service...\n\n"
sed -i "s:/path/to/OverBot/:$(pwd)/:" overbot.service
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
	echo "[${red}ERROR${reset}] an error occured while reloading the deamon."
}

printf "${green}${bold}Installation completed!${normal}${reset}\n"
printf "${red}Before running the bot you must configure the config.py file!${reset}\n"
printf "Once you've edited the config.py file, run ${bold}systemctl start overbot${normal}\n"
