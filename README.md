# APK Submission Server

## Run instructions

1) `python serve.py`
2) `./setup_redis.sh`
3) `celery worker -A celery_worker.celery --loglevel=info`

## TODO

* Dockerize this
* Look for performance optimizations with running problems in emulator
* Look for reliability gains with adb
    * Kill the adb server every so often?

### Installing Android SDK

```
wget https://dl.google.com/android/repository/sdk-tools-linux-3859397.zip
unzip sdk-tools-linux-3859397.zip
sudo mkdir /opt/android-sdk
sudo chown ubuntu:ubuntu /opt/android-sdk
mv tools/ /opt/android-sdk/
cd /opt/android-sdk/
tools/bin/sdkmanager --update
tools/bin/sdkmanager "platforms^Cndroid-23" "build-tools;23.0.2" "extras;google;m2repository" "extras;android;m2repository"
```
