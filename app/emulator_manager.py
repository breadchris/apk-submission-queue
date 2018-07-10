import os
import time
import Queue
import socket
import logging
import subprocess
import threading
from datetime import datetime

from . import models
from models import db_session

# from models import db_session

logger = logging.getLogger('root')

def cmd_with_timeout(cmd, cwd="/opt/android-sdk/emulator", timeout_sec=10):
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timer = threading.Timer(timeout_sec, proc.kill)

    stdout = ""
    stderr = ""
    rc = 0
    try:
        timer.start()
        stdout, stderr = proc.communicate()
        rc = proc.returncode
    except Exception, e:
        logger.error("Exception running cmd: {}".format(e))
        rc = 1
    finally:
        timer.cancel()

    return (stdout, stderr, rc)

def update_status(task, status):
    task.update_state(state='PROGRESS', \
        meta={'status': status, 'time': datetime.utcnow()})

class Challenge(object):
    def __init__(self, apk_file, flag, flag_path):
        self.apk_file = apk_file
        self.flag = flag
        self.flag_path = flag_path
        self.user = None

    def set_user(self, user):
        self.user = user

class Emulator(object):
    STATUS_ERROR = 1
    OFFLINE = 2
    ONLINE_NOT_BOOTED = 3
    ONLINE = 4

    def __init__(self, name, challenges=[]):
        self.name = name
        self.challenges = challenges

    def adb_cmd(self, cmd, timeout_sec=10):
        base_cmd = ['adb', '-s', self.serial]
        base_cmd.extend(cmd)

        (stdout, stderr, rc) = cmd_with_timeout(base_cmd, timeout_sec=timeout_sec)
        if rc != 0:
            logger.error("Error running cmd: {} = {}".format(cmd, rc))
            logger.error("STDOUT: {}".format(stdout))
            logger.error("STDERR: {}".format(stderr))
            return (stdout, False)
        return (stdout, True)

    def setup_and_run_apk(self, task, apk_file):
        logger.debug("Running apk in emulator: {}".format(apk_file))

        update_status(task, "Setting up emulator")

        if not self.start() or \
           not self.setup() or \
           not self.install_apk(apk_file):
            return False

        update_status(task, "Emulator started up successfully")

        update_status(task, "Running apk in emulator")
        if not self.run_apk(apk_file):
            return False

        # Wait a bit to let the apk run
        # Waiting three minutes for now
        logger.debug("Waiting for apk to run: {}".format(apk_file))
        time.sleep(60 * 3)

        update_status(task, "apk ran successfully!")

        logger.debug("Stopping emulator for submission: {}".format(apk_file))
        if not self.stop():
            return False

        return True

    def start(self):
        # Start emulator
        cmd = ["emulator", "-wipe-data", "-accel", "on", "-no-boot-anim", \
                "-no-audio", "-avd", self.name]

        subprocess.Popen(cmd, cwd="/opt/android-sdk/emulator", stdin=None, stdout=None, stderr=None, close_fds=True)

        """
        Android Console: Authentication required
        Android Console: type 'auth <auth_token>' to authenticate
        Android Console: you can find your <auth_token> in
        '/Users/cthompson/.emulator_console_auth_token'
        OK
        >>> avd name
        test
        OK
        """
        def get_device_name(serial):
            port = int(serial.split("-")[-1])

            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except socket.error as msg:
                logger.error("Unable to get device name: {}".format(msg))
                return False

            try:
                s.connect(('localhost', port))
            except socket.error as msg:
                s.close()
                logger.error("Unable to get device name: {}".format(msg))
                return False

            s.settimeout(2.0)

            # lol idk why, but it works
            s.recv(1024)
            s.settimeout(None)

            s.recv(1024)

            s.send('avd name\n')
            lines = s.recv(1024)

            if lines == "" or "/" in lines:
                return False

            lines = lines.strip().split("\n")
            logger.debug("Getting device name: {}".format(lines))

            if len(lines) == 2 and lines[1] == "OK":
                return lines[0].strip()
            else:
                return ""

        def adb_get_devices():
            # Get running devices
            devices_cmd = ["adb", "devices"]
            (stdout, stderr, rc) = cmd_with_timeout(devices_cmd)
            if rc != 0:
                logger.error("Error getting list of devices: {}({})".format(self.name, rc))
                logger.error("STDERR: {}".format(stderr))
                yield

            for line in stdout.split("\n")[1:]:
                if "emulator-" in line:
                    device_serial = line.split()[0]
                    yield device_serial

        """
        List of devices attached
        emulator-5554   device

        """
        time.sleep(5)
        done = False
        while not done:
            for device_serial in adb_get_devices():
                name = None
                try:
                    name = get_device_name(device_serial)
                    if name == False:
                        continue
                except:
                    continue

                if name == None:
                    logger.error("Unable to get device name for: {}".format(device_serial))
                    continue

                logger.debug("{} {} {}".format(device_serial, name, self.name))
                if self.name == name:
                    self.serial = device_serial
                    done = True
                    break
            time.sleep(3)

        while True:
            if self.status() == self.ONLINE:
                break
            time.sleep(1)

        logger.debug("Device started up: {}".format(self.name))
        return True

    def stop(self):
        _, success = self.adb_cmd(["emu", "kill"], 30)
        return success

    def status(self):
        stdout, success = self.adb_cmd(["shell", "getprop", "sys.boot_completed"])
        if not success:
            return self.STATUS_ERROR

        val = stdout.strip()
        if val == "error: device offline":
            return self.OFFLINE
        if val == "":
            return self.ONLINE_NOT_BOOTED
        if val == "1":
            return self.ONLINE

        return self.STATUS_ERROR

    def setup(self):
        time.sleep(5)
        for challenge in self.challenges:
            if not self.install_apk(challenge.apk_file, perm_apk=True) or \
               not self.run_apk(challenge.apk_file, challenge):
               return False

        return True

    def run_apk(self, apk_file, challenge=None):
        cmd = ["./aapt", "dump", "badging", apk_file]

        # TODO: Do something about this path :/

        (stdout, stderr, rc) = cmd_with_timeout(cmd, cwd="/opt/android-sdk/build-tools/28.0.0/")
        if rc != 0:
            logger.error("Error getting apk info: {}".format(rc))
            logger.error("STDERR: {}".format(stderr))
            return False

        # Get apk info
        package_name = ""
        activity_name = ""
        for line in stdout.split("\n"):
            if line.startswith("package: "):
                package_name = line.split(" ")[1].split("=")[1].replace("'", "")
            elif line.startswith("launchable-activity: "):
                activity_name = line.split(" ")[1].split("=")[1].replace("'", "")


        if package_name == "" or activity_name == "":
            logger.error("Unable to get package information from: ".format(apk_file))
            return False

        logger.debug("Running: {}/{}".format(package_name, activity_name))

        stdout, success = self.adb_cmd(
            ["shell", "am", "start", "-n", "{}/{}".format(package_name, activity_name)])
        if not success:
            return False

        if challenge is not None:
            # Wait for apk to start
            time.sleep(1)

            stdout, success = self.adb_cmd(["root"])
            if not success:
                return False

            stdout, success = self.adb_cmd(["shell", "ps", "-A"])
            if not success:
                return False

            user = None
            for line in stdout.split("\n"):
                parts = line.split()
                if len(parts) == 9 and parts[-1] == package_name:
                    user = parts[0]

            if user is None:
                logger.error("Unable to find user for apk: {}".format(apk_file))
                return False

            challenge.set_user(user)

            logger.debug("Creating secret challenge file: {}".format(challenge.flag_path))

            stdout, success = self.adb_cmd(["shell", "echo", challenge.flag, ">", challenge.flag_path])
            if not success:
                return False

            stdout, success = self.adb_cmd(["shell", "su", "root", "chown", "root:{}".format(user), "{}".format(challenge.flag_path)])
            if not success:
                return False

            stdout, success = self.adb_cmd(["shell", "su", "root", "chmod", "550", challenge.flag_path])
            if not success:
                return False

        return True

    def install_apk(self, apk_file, perm_apk=False):
        logger.debug("Installing apk {} on device {}".format(apk_file, self.name))

        """
        cmd = []
        if perm_apk:
            cmd = ["install", "-g", apk_file]
        else:
            cmd = ["install", apk_file]
        """
        cmd = ["install", "-g", apk_file]

        stdout, success = self.adb_cmd(cmd)
        if not success:
            return False

        logger.debug("Installed apk {} on device {}".format(apk_file, self.name))
        return True

class EmulatorManager(object):
    EMULATORS_BUSY = 1

    def __init__(self, emulators=[], challenges=[]):
        self.challenges = challenges
        self.emus = emulators

    def init_emulators(self):
        for emu_name in self.emus:
            db_emu = models.Emulator.query.filter(models.Emulator.name == emu_name).first()
            if db_emu is not None:
                continue

            e = models.Emulator(emu_name)
            db_session.add(e)
            db_session.commit()

    def get_emulator(self):
        db_emu = models.Emulator.query.filter(models.Emulator.busy == 0).first()
        if db_emu is None:
            return None

        # Set emulator as busy
        db_emu.busy = 1
        db_session.commit()
        return Emulator(db_emu.name, self.challenges)

    def release_emulator(self, emu):
        db_emu = models.Emulator.query.filter(models.Emulator.name == emu.name).first()

        # Set emulator as not busy
        db_emu.busy = 0
        db_session.commit()

    # TODO: Make this thread safe
    def run_submission(self, task, emu, apk_file):
        try:
            success = emu.setup_and_run_apk(task, apk_file)
        except Exception, e:
            success = False
            logger.exception("Error while running submission: {}".format(e))

        if not success:
            emu.stop()

        self.release_emulator(emu)
        return success
