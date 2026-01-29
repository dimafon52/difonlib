#!/usr/bin/env bash

# 14.07.25

echo " Start..."
docker container stop android-arm-emulator-container

sleep 2

# docker run --rm --privileged -d -p 6080:6080 -p 5554:5554 -p 5555:5555 -e EMULATOR_DEVICE="Samsung Galaxy S10" -e WEB_VNC=true --device /dev/kvm --name android-arm-emulator-container budtmo/docker-android:emulator_11.0
docker run --rm --privileged -d \
       -p 6080:6080 -p 5555:5555 \
       -e EMULATOR_DEVICE="Samsung Galaxy S10" \
       -e WEB_VNC=true \
       --device /dev/kvm \
       --name android-arm-emulator-container \
       budtmo/docker-android:emulator_11.0

sleep 15

adb kill-server
sleep 1
adb root
sleep 1
adb devices
# adb connect 127.0.0.1:5555
sleep 20
adb install -f ${PWD}/apk/com.tuya.smartlife_3.6.1.apk
sleep 3

echo "Run Tuya Smart Home application. To continue press ENTER"
read
firefox localhost:6080

echo "If Tuya Smart Live is runed - press ENTER"
read
adb root
sleep 1
adb pull /data/data/com.tuya.smartlife/shared_prefs .

ls -l shared_prefs/*
nemo ./shared_prefs/ &

# firefox ${PWD}/shared_prefs/preferences_global_keyeu1609443890901OWMrJ.xml
# google-chrome-stable ${PWD}/shared_prefs/preferences_global_keyeu1609443890901OWMrJ.xml &

read -p " >>> Stop 'Tuya Smart Live' docker container? (y/n) " RESP
if [ "$RESP" = "y" ]; then
    echo "Please wait..."
    docker container stop android-arm-emulator-container
fi


# ./check_tuya_devs.py


