#!/bin/sh

set -eu

db=""

for v in "$@"
do
    if [ "$v" == "--db" ]
    then
        db="next"
    elif [ "$db" == "next" ]
    then
        db="$v"
    elif [[ "$v" == "--db="* ]]
    then
        db="${v#--db=}"
    fi
done

if ! [ "$db" == 'next' ] && ! [ -z "$db" ]
then
    .venv/bin/alembic -x db="${db//+*:\/\//://}" upgrade head
fi

exec .venv/bin/python3 -mtour_guide_bot.cli "$@"
