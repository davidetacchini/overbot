#!/bin/bash
red=$(tput setaf 1)
green=$(tput setaf 2)
reset=$(tput sgr0)

bold=$(tput bold)
normal=$(tput sgr0)

for pack in isort black flake8
do
	if [ -x "$(command -v $pack)" ]; then
		echo "Checking for ${bold}$pack${normal}... ${green}OK${reset}"
		$pack .
	else
		echo "${red}$pack is not installed. Please install it via pip.${reset}"
		exit
	fi
done
