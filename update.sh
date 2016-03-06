#!/bin/bash

if [ "$LIVE" = "true" ]; then
    git fetch --all
    git reset --hard origin/master
    docker build -t hdb_scraper .
fi

rm -f data/bidadari.log

docker run --rm -v `pwd`/data:/app/data hdb_scraper

cat data/bidadari.log

# If data scrape is ok
if grep --quiet "^###OK###$" data/bidadari.log; then
    # If there is any changes to the data scraped
    if [[ $(git diff data/bidadari.csv) ]]; then
        git add data/
        git commit -m "Updated data on `date`"
        if [ "$LIVE" = "true" ]; then
            git push
        fi
    else
        echo "No change in data"
        git checkout -- data/
    fi
else
    echo "Data scrape failed"
    git checkout -- data/
fi
