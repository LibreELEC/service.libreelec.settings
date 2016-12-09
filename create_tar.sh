#!/bin/sh

# to use you need to set the xz command to use
# git config --global tar.tar.xz.command "xz -c"

if [ -z "$1" ]; then
  echo "Usage: $0 <tag|commit-sha|HEAD>"
  exit 0
fi

git archive --format=tar.xz --prefix=LibreELEC-settings-$1/ $1 -o LibreELEC-settings-$1.tar.xz
