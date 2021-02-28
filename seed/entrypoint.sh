#!/bin/bash
USER_ID=${PID:-9001}
GROUP_ID=${GID:-$USER_ID}

echo "Starting with UID : $USER_ID, GID: $GROUP_ID"
groupadd -g $GROUP_ID bridge
useradd --shell /bin/bash -u $USER_ID -g bridge -o -c "" -m bridge
export HOME=/home/bridge

chown bridge:bridge -R /home/bridge
chmod og= -R /home/bridge

exec gosu bridge:bridge ./bootstrap.sh "$@"