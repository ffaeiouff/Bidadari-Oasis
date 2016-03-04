#!/bin/bash

rm -f data/bidadari.log
docker run --rm -v `pwd`/data:/app/data hdb_scraper

# If data scrape is ok
if grep --quiet "^###OK###$" data/bidadari.log; then
    # If there is any changes to the data scraped
    if [[ $(git diff data/bidadari.csv data/bidadari.json) ]]; then
        git add data/
        git commit -m "Updated data on `date`"
    else
        echo "No change in data"
        git checkout -- data/
    fi
else
    echo "Data scrape failed"
    git checkout -- data/
fi
