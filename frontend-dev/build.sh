#!/bin/bash


if [ -d dist/ ]; then
    echo "/dist exists. removing it."
    rm -rf dist/
    
    if [ -d ../api/dist/ ]; then
        echo "../api/dist/ exists. removing before building and copying from frontend-dev\..."
        rm -rf ../api/dist/
        echo "../api/dist/ removed."

    else
        echo "../api/dist/ does not exist"
    fi
    
else
    echo "/dist does not exist"
fi

sed -i 's#let apiAddress = "http://localhost:8000/";#let apiAddress = "/";#g' src/main.js
echo "building new /dist..."
npm run build
sed -i 's#let apiAddress = "/";#let apiAddress = "http://localhost:8000/";#g' src/main.js
echo "copying dist/ from frontend-dev to ../api/dist.."
cp -r dist/ ../api/dist/
echo "done!"

echo "find and replace all instances of /assets/ to /dist/assets/"
sed -i 's#/assets/#/dist/assets/#g' ../api/dist/index.html
sed -i 's#http://localhost:8000/#/#g' ../api/dist/index.html
sed -i 's#/assets/#/dist/assets/#g' ../api/dist/register.html
sed -i 's#/assets/#/dist/assets/#g' ../api/dist/login.html


echo "Do you wish to start syslog server? (yes/no)"
read yn

case $yn in
    yes|y|Y ) cd .. && ./start.sh;;
    no|n|N ) exit;;
    * ) echo "Invalid input. Please type 'yes' or 'no'.";;
esac