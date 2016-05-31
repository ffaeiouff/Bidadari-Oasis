build:
	docker build -t Bidadari-Oasis .

run:
	docker run --rm -v `pwd`:/app Bidadari-Oasis
