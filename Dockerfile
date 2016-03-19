FROM alpine:3.3

RUN apk add --update python3 tzdata && \
	cp /usr/share/zoneinfo/Asia/Singapore /etc/localtime && \
	echo "Asia/Singapore" > /etc/timezone && \
    python3 -m ensurepip && \
    pip3 install beautifulsoup4 requests && \
    rm -rf /var/cache/apk/* && \
    mkdir hdb_scraper

WORKDIR /app
ADD scraper.py /app

CMD ["python3", "-u", "scraper.py"]
