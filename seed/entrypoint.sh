#!/bin/bash

export KEY_ID=`gpg --list-keys | awk '$1 == "pub" {getline;print $1}' | head -n 1`
if [ "${KEY_ID}" = "" ]; then
  gpg --batch --generate-key gpg.template
  export KEY_ID=`gpg --list-keys | awk '$1 == "pub" {getline;print $1}' | head -n 1`
fi

if [ ! -f "${HOME}/.password-store/" ]; then
  echo "SEED: Init password store"
  pass init "${KEY_ID}"
fi

export PREF_PATH="${HOME}/.config/protonmail/bridge"
if [ ! -f "${PREF_PATH}/prefs.json" ]; then
  echo "Install preferences template"
  cp prefs.json "${PREF_PATH}"
fi

proton-bridge "$@"
