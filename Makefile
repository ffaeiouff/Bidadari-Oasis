build:
	docker build -t hdb_scraper .

run:
	docker run --rm -v `pwd`:/app hdb_scraper
