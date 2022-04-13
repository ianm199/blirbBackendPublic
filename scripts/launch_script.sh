#!/bin/bash
cd $HOME/test/backend/movieWatchDjango
while true; do
        read -p "Pull latest code?" yn
        case $yn in
                [Yy]* ) git pull; break;;
                [Nn]* ) break;;
                * ) echo "Please answer yes or no.";;
        esac
done