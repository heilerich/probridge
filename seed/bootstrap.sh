#!/bin/bash
export KEY_ID=`gpg --list-keys | awk '$1 == "pub" {getline;print $1}' | head -n 1`
if [ "${KEY_ID}" = "" ]; then
  gpg --batch --generate-key gpg.template
  export KEY_ID=`gpg --list-keys | awk '$1 == "pub" {getline;print $1}' | head -n 1`
fi

if [ ! -d "${HOME}/.password-store/" ]; then
  echo "SEED: Init password store"
  pass init "${KEY_ID}"
fi

export PREF_PATH="${HOME}/.config/protonmail/bridge"
if [ ! -f "${PREF_PATH}/prefs.json" ]; then
  echo "Install preferences template"
  mkdir -p "${PREF_PATH}"
  cp prefs.json "${PREF_PATH}/"
fi

exec socat TCP-LISTEN:${IMAP_PORT},fork,bind=$(hostname -I) TCP:127.0.0.1:${IMAP_PORT} &
exec socat TCP-LISTEN:${SMTP_PORT},fork,bind=$(hostname -I) TCP:127.0.0.1:${SMTP_PORT} &
exec proton-bridge "$@"
