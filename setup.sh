#!/bin/bash

export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64"
export ANDROID_HOME="/opt/android-sdk"
export PATH="${PATH}:${ANDROID_HOME}/emulator:${ANDROID_HOME}/tools:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/tools/bin"

sudo apt-get install -y --no-install-recommends openjdk-8-jdk unzip make gcc virtualenv python python-pip python-celery-common xvfb

sudo mkdir -p /opt/android-sdk && sudo chown ctf:ctf /opt/android-sdk && cd /opt/android-sdk && \
wget -q https://dl.google.com/android/repository/sdk-tools-linux-${ANDROID_SDK_VERSION}.zip && \
unzip *tools*linux*.zip && \
rm *tools*linux*.zip

sdkmanager "platform-tools" "emulator" "platforms;android-28" "system-images;android-28;default;x86_64"

setup_dependencies() {
    apt-get install -y --no-install-recommends openjdk-8-jdk

    mkdir -p /opt/android-sdk && cd /opt/android-sdk && \
    wget -q https://dl.google.com/android/repository/sdk-tools-linux-${ANDROID_SDK_VERSION}.zip && \
    unzip *tools*linux*.zip && \
    rm *tools*linux*.zip

    sdkmanager "platform-tools" "emulator" "platforms;android-P" "system-images;android-P;default;x86_64"
}

EMULATOR_COUNT=2
EMULATOR_BASE_NAME="pwnable-emulator"

# Create emulators
create_emulators() {
    EMULATOR_COUNT=$1
    for i in $(seq $EMULATOR_COUNT); do
        EMULATOR_NAME="$EMULATOR_BASE_NAME-$i"
        echo "no" | avdmanager create avd -n $EMULATOR_NAME -k "system-images;android-P;default;x86_64"
    done
}

start_emulator() {
    EMULATOR_ID=$1

    EMULATOR_NAME="$EMULATOR_BASE_NAME-$EMULATOR_ID"
    emulator -wipe-data -accel on -no-boot-anim -screen no-touch -no-audio -no-window -avd "$EMULATOR_NAME"
}

stop_emulator() {
    EMULATOR_ID=$1

    EMULATOR_NAME="$EMULATOR_BASE_NAME-$EMULATOR_ID"
    adb -s "$EMULATOR_NAME" emu kill
}

create_emulators $EMULATOR_COUNT
