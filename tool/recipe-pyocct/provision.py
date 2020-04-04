#!/usr/bin/env python

#
# provision library from azure cloud
#

import os


def invoke(command:str) -> None:
    print(f"### command: {command}")
    result = os.system(command)
    assert result == 0, f"result: {result}"


print(f"### review enviro")
for key, value in sorted(os.environ.items()):
    print(f"# {key}={value}")

library_file = "OCP.cpython-36m-x86_64-linux-gnu.so"
library_version = "7.4-alpha"

library_source = f"https://github.com/CadQuery/OCP/releases/download/{library_version}/{library_file}"
library_target = f"/tmp/{library_file}"

library_fetch_cmd = f"curl -L -k -o {library_target} {library_source}"

if os.path.exists(library_target):
    print(f"### library present")
else:
    print(f"### library missing")
    invoke(library_fetch_cmd)


print(f"### install library")
invoke(f"mkdir -p $SP_DIR")
invoke(f"cp -f {library_target} $SP_DIR/{library_file}")
