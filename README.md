### Build
```
docker build -t quonkbot:0.1.0 .
```

### Run
```
docker run -v /$(pwd)/db:/home/appuser/db --env-file .env quonkbot:0.1.0
```